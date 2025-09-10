import ctypes
import time
import win32gui
import win32process
import psutil
import pymem
import pymem.process
import keyboard

from Process.offsets import Offsets
from Process.process_handler import CS2Process

class BHopProcess:
    KEYEVENTF_KEYDOWN = 0x0000
    KEYEVENTF_KEYUP = 0x0002
    VK_SPACE = 0x20

    def __init__(self, shared_config, process_name="cs2.exe", module_name="client.dll", jump_cooldown=0.1, foreground_check_interval=10):
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.shared_config = shared_config
        self.process_name = process_name.lower()
        self.module_name = module_name
        self.jump_cooldown = jump_cooldown
        self.foreground_check_interval = foreground_check_interval

        # Initialize CS2Process to handle process and module base
        self.cs2 = CS2Process(process_name=self.process_name, module_name=self.module_name)
        self.cs2.initialize()

        # Assign pymem.Pymem instance
        import pymem
        self.pm = pymem.Pymem(self.process_name)

        # Use module base from CS2Process
        self.base_addr = self.cs2.module_base

        self.cached_exe = None
        self.last_jump_time = 0
        self.iteration = 0

    def press_spacebar(self):
        press_duration = 0.001  # Fixed press duration (between previous 0.004 and 0.008)
        self.user32.keybd_event(self.VK_SPACE, 0, self.KEYEVENTF_KEYDOWN, 0)
        time.sleep(press_duration)
        self.user32.keybd_event(self.VK_SPACE, 0, self.KEYEVENTF_KEYUP, 0)

    def get_foreground_exe(self):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc_name = psutil.Process(pid).name()
            return proc_name.lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def initialize(self):
        try:
            self.pm = pymem.Pymem(self.process_name)
            client_module = pymem.process.module_from_name(self.pm.process_handle, self.module_name)
            self.base_addr = client_module.lpBaseOfDll
        except Exception as e:
            print(f"[BHop ERROR] Could not open process or module: {e}")
            return False
        return True

    def run(self):
        print("[*] Starting BHop process. Hold SPACE to bunny hop. Press Ctrl+C to exit.")

        if not self.initialize():
            return

        while True:
            try:
                if getattr(self.shared_config, "stop", False):
                    break

                if self.iteration % self.foreground_check_interval == 0:
                    self.cached_exe = self.get_foreground_exe()
                self.iteration += 1

                if not getattr(self.shared_config, "bhop_enabled", False):
                    time.sleep(0.01)
                    continue

                if self.cached_exe != self.process_name:
                    time.sleep(0.01)
                    continue

                if keyboard.is_pressed('space'):
                    pawn = self.pm.read_longlong(self.base_addr + Offsets.dwLocalPlayerPawn)
                    if pawn == 0:
                        time.sleep(0.01)
                        continue

                    flags = self.pm.read_int(pawn + Offsets.m_fFlags)
                    on_ground = (flags & 1) == 1

                    now = time.time()
                    if on_ground and now - self.last_jump_time > self.jump_cooldown:
                        self.press_spacebar()
                        self.last_jump_time = now

                time.sleep(0.0015)

            except (EOFError, BrokenPipeError):
                break
            except (pymem.exception.MemoryReadError, pymem.exception.ProcessError):
                time.sleep(0.01)
            except Exception as e:
                print(f"[BHop ERROR] Exception in main loop: {e}")
                time.sleep(0.01)

        print("[BHop] Stopped.")
