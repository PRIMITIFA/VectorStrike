import ctypes
import ctypes.wintypes as wintypes
import struct
import time
import random
from Process.offsets import Offsets

class CS2GlowManager:
    PROCESSENTRY32 = ctypes.Structure
    MODULEENTRY32 = ctypes.Structure

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * wintypes.MAX_PATH)
        ]

    class MODULEENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
            ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
            ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
            ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * wintypes.MAX_PATH)
        ]

    PROCESS_ALL = 0x0010 | 0x0020 | 0x0008 | 0x0400
    TH32CS_SNAPPROCESS = 0x00000002
    TH32CS_SNAPMODULE = 0x00000008

    def __init__(self, shared_config, proc=b"cs2.exe", mod=b"client.dll"):
        self.shared_config = shared_config
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k32 = k32
        self.proc_name, self.mod_name = proc, mod
        self.pid = self._get_pid()
        self.handle = k32.OpenProcess(self.PROCESS_ALL, False, self.pid)
        if not self.handle:
            raise Exception("Failed to open process")
        self.client = self._get_module_base()
        if not self.client:
            raise Exception("Module base not found")

    def _get_pid(self):
        snap = self.k32.CreateToolhelp32Snapshot(self.TH32CS_SNAPPROCESS, 0)
        if snap == -1:
            raise Exception("Snapshot failed")
        entry = self.PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(entry)
        success = self.k32.Process32First(snap, ctypes.byref(entry))
        while success:
            if entry.szExeFile[:len(self.proc_name)].lower() == self.proc_name.lower():
                self.k32.CloseHandle(snap)
                return entry.th32ProcessID
            success = self.k32.Process32Next(snap, ctypes.byref(entry))
        self.k32.CloseHandle(snap)
        raise Exception("Process not found")

    def _get_module_base(self):
        snap = self.k32.CreateToolhelp32Snapshot(self.TH32CS_SNAPMODULE, self.pid)
        if snap == -1:
            return None
        module = self.MODULEENTRY32()
        module.dwSize = ctypes.sizeof(module)
        success = self.k32.Module32First(snap, ctypes.byref(module))
        while success:
            if module.szModule[:len(self.mod_name)].lower() == self.mod_name.lower():
                self.k32.CloseHandle(snap)
                return ctypes.cast(module.modBaseAddr, ctypes.c_void_p).value
            success = self.k32.Module32Next(snap, ctypes.byref(module))
        self.k32.CloseHandle(snap)
        return None

    def _rw(self, addr, size=None, data=None):
        buf = ctypes.create_string_buffer(size) if size else ctypes.create_string_buffer(data)
        bytes_rw = ctypes.c_size_t()
        func = self.k32.ReadProcessMemory if size else self.k32.WriteProcessMemory
        success = func(self.handle, ctypes.c_void_p(addr), buf, size or len(data), ctypes.byref(bytes_rw))
        if not success or (size and bytes_rw.value != size) or (data and bytes_rw.value != len(data)):
            return None if size else False
        return buf.raw if size else True

    def _read_i(self, addr): return struct.unpack("i", self._rw(addr, 4) or b"\0\0\0\0")[0]
    def _read_u(self, addr): return struct.unpack("I", self._rw(addr, 4) or b"\0\0\0\0")[0]
    def _read_ull(self, addr): return struct.unpack("Q", self._rw(addr, 8) or b"\0"*8)[0]
    def _write_u(self, addr, val): return self._rw(addr, data=struct.pack("I", val))

    def _to_argb(self, r, g, b, a):
        clamp = lambda x: max(0, min(1, x))
        r, g, b, a = [int(clamp(c) * 255) for c in (r, g, b, a)]
        return (a << 24) | (r << 16) | (g << 8) | b

    def _get_local_team(self):
        local = self._read_ull(self.client + Offsets.dwLocalPlayerPawn)
        return self._read_i(local + Offsets.m_iTeamNum) if local else None

    def update_glow(self):
        # Check glow toggle in shared config dynamically
        if not getattr(self.shared_config, "glow", True):
            return  # Glow disabled, skip

        local = self._read_ull(self.client + Offsets.dwLocalPlayerPawn)
        entities = self._read_ull(self.client + Offsets.dwEntityList)
        team = self._get_local_team()
        if not (local and entities and team is not None):
            return

        for i in range(64):
            entry = self._read_ull(entities + 0x10)
            if not entry:
                continue
            ctrl = self._read_ull(entry + i * 0x78)
            if not ctrl:
                continue
            pawn_handle = self._read_i(ctrl + Offsets.m_hPlayerPawn)
            if not pawn_handle:
                continue

            ent2 = self._read_ull(entities + 0x8 * ((pawn_handle & 0x7FFF) >> 9) + 0x10)
            pawn = self._read_ull(ent2 + 0x78 * (pawn_handle & 0x1FF)) if ent2 else 0
            if not pawn or pawn == local:
                continue
            if self._read_u(pawn + Offsets.m_lifeState) != 256:
                continue

            is_team = self._read_i(pawn + Offsets.m_iTeamNum) == team
            color = (1, 0, 0, 1) if is_team else (0, 0, 1, 1)

            glow = pawn + Offsets.m_Glow
            self._write_u(glow + Offsets.m_glowColorOverride, self._to_argb(*color))
            self._write_u(glow + Offsets.m_bGlowing, 1)
            self._write_u(glow + Offsets.m_iGlowType, 3)

    def run(self):
        try:
            while True:
                self.update_glow()
                time.sleep(0.01 + random.uniform(0, 0.005))
        except KeyboardInterrupt:
            pass
        finally:
            self.k32.CloseHandle(self.handle)
