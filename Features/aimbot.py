import pymem, time, math, random, json, threading
from pynput import mouse
from Process.offsets import Offsets
from Process.process_handler import CS2Process
import requests
from requests import get
import ctypes
import time
import pyMeow as pw_module
from ctypes import windll, wintypes
import threading
import time
import math
import random
import json
from collections import deque
from pynput import mouse
import pymem
import os

# === SendInput setup for external mouse movement ===
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [("type", ctypes.c_ulong), ("ii", _INPUT)]

SendInput = ctypes.windll.user32.SendInput

def move_mouse(dx, dy):
    mi = MOUSEINPUT(dx=dx, dy=dy, mouseData=0, dwFlags=MOUSEEVENTF_MOVE, time=0, dwExtraInfo=None)
    inp = INPUT(type=INPUT_MOUSE, ii=INPUT._INPUT(mi=mi))
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

class CS2WeaponTracker:
    VALID_WEAPON_IDS = {
        41, 42, 59, 80, 500, 505, 506, 507, 508, 509, 512, 514, 515, 516, 519, 520, 522, 523,
        44, 43, 45, 46, 47, 48, 49
    }

    def __init__(self):
        self.pm = None
        self.client = None
        self.attach_to_process()

    def attach_to_process(self):
        while True:
            try:
                self.pm = pymem.Pymem("cs2.exe")
                self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
                break
            except Exception as e:
                time.sleep(1)

    def get_current_weapon_id(self):
        try:
            local_player = self.pm.read_longlong(self.client + Offsets.dwLocalPlayerPawn)
            if not local_player:
                return None

            weapon_ptr = self.pm.read_longlong(local_player + Offsets.m_pClippingWeapon)
            if not weapon_ptr:
                return None

            weapon_id = self.pm.read_int(
                weapon_ptr + Offsets.m_AttributeManager + Offsets.m_Item + Offsets.m_iItemDefinitionIndex
            )
            return weapon_id
        except Exception as e:
            return None

    def is_weapon_valid_for_aim(self):
        weapon_id = self.get_current_weapon_id()
        if weapon_id is None:
            return True
        valid = weapon_id not in self.VALID_WEAPON_IDS
        return valid

class AimbotRCS:
    MAX_DELTA_ANGLE = 60
    LEARN_FILE = "aimbot.json"
    SENSITIVITY = 0.022
    INVERT_Y = -1
    LEARN_DIR = "aimbot_data"

    def __init__(self, cfg):
        self.cfg = cfg
        self.pm = pymem.Pymem("cs2.exe")
        self.o = Offsets()
        self.cs2 = CS2Process()
        self.cs2.initialize()
        self.base = self.cs2.module_base
        self.local_player_controller = self.base + self.o.dwLocalPlayerController  # cache once

        # Cache read functions
        self.read_funcs = {
            "int": self.pm.read_int,
            "long": self.pm.read_longlong,
            "float": self.pm.read_float,
            "ushort": self.pm.read_ushort,
        }

        self.bone_indices = {"head": 6, "chest": 18}
        self.left_down = False
        self.shots_fired = 0
        self.last_punch = (0.0, 0.0)
        self.target_id = None
        self.last_target_lost_time = 0
        self.aim_start_time = None
        self.last_aim_angle = None
        self.lock = threading.Lock()

        self.weapon_tracker = CS2WeaponTracker()

        self.learning_data = {}
        self.load_learning()
        self.learning_dirty = False

        mouse.Listener(on_click=self.on_click, daemon=True).start()
        threading.Thread(target=self.periodic_save, daemon=True).start()

        # Local math functions
        self._isnan = math.isnan
        self._hypot = math.hypot
        self._atan2 = math.atan2
        self._degrees = math.degrees

    def is_cs2_focused(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return False

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        PROCESS_VM_READ = 0x0010
        PROCESS_QUERY_INFORMATION = 0x0400

        hProcess = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid.value)
        if not hProcess:
            return False

        try:
            buffer_len = wintypes.DWORD(260)
            exe_path_buffer = ctypes.create_unicode_buffer(buffer_len.value)
            # Query full process image name
            QueryFullProcessImageName = kernel32.QueryFullProcessImageNameW
            if not QueryFullProcessImageName(hProcess, 0, exe_path_buffer, ctypes.byref(buffer_len)):
                return False

            exe_name = exe_path_buffer.value.split("\\")[-1].lower()
            return exe_name == "cs2.exe"
        finally:
            kernel32.CloseHandle(hProcess)
            
    def periodic_save(self):
        while not self.cfg.stop:
            time.sleep(30)
            if self.cfg.enable_learning and self.learning_dirty:
                self.save_learning()
                self.learning_dirty = False

    def load_learning(self):
        self.learning_data = {}
        if not os.path.exists(self.LEARN_DIR):
            os.makedirs(self.LEARN_DIR)

        weapon_id = self.weapon_tracker.get_current_weapon_id()
        if not weapon_id:
            return

        filepath = os.path.join(self.LEARN_DIR, f"{weapon_id}.json")
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            self.learning_data = {
                tuple(map(float, k.split(','))): deque([tuple(x) for x in v], maxlen=50)
                for k, v in data.items()
            }
        except (FileNotFoundError, json.JSONDecodeError):
            self.learning_data = {}

    def save_learning(self):
        if not self.cfg.enable_learning:
            return

        weapon_id = self.weapon_tracker.get_current_weapon_id()
        if not weapon_id:
            return

        filepath = os.path.join(self.LEARN_DIR, f"{weapon_id}.json")
        try:
            with self.lock, open(filepath, "w") as f:
                data = {f"{k[0]},{k[1]}": list(v) for k, v in self.learning_data.items()}
                json.dump(data, f)
        except Exception as e:
            print(f"[!] Failed saving learning data for weapon {weapon_id}: {e}")


    def read(self, addr, t="int"):
        if not addr:
            return 0.0 if t == "float" else 0
        try:
            return self.read_funcs[t](addr)
        except Exception:
            return 0.0 if t == "float" else 0

    def get_entity(self, base, idx):
        array_idx = (idx & 0x7FFF) >> 9
        entity_addr = self.read(base + 8 * array_idx + 16, "long")
        if not entity_addr:
            return 0
        ctrl = self.read(entity_addr + 0x78 * (idx & 0x1FF), "long")
        local_ctrl = self.read(self.local_player_controller, "long")  # cached addr
        return ctrl if ctrl and ctrl != local_ctrl else 0

    def read_vec3(self, addr):
        r = self.read
        return [r(addr + i * 4, "float") for i in range(3)]

    def read_weapon_id(self, pawn):
        w = self.read(pawn + self.o.m_pClippingWeapon, "long")
        if not w:
            return 0
        item_idx_addr = w + self.o.m_AttributeManager + self.o.m_Item + self.o.m_iItemDefinitionIndex
        return self.read(item_idx_addr, "ushort")

    def read_bone_pos(self, pawn, idx):
        scene = self.read(pawn + self.o.m_pGameSceneNode, "long")
        if not scene:
            return None
        bones = self.read(scene + self.o.m_pBoneArray, "long")
        if not bones:
            return None
        return self.read_vec3(bones + idx * 32)

    def calc_angle(self, src, dst):
        dx = dst[0] - src[0]
        dy = dst[1] - src[1]
        dz = dst[2] - src[2]
        hyp = self._hypot(dx, dy)
        pitch = -self._degrees(self._atan2(dz, hyp))
        yaw = self._degrees(self._atan2(dy, dx))
        return pitch, yaw

    def normalize(self, pitch, yaw):
        if self._isnan(pitch) or self._isnan(yaw):
            return 0.0, 0.0
        pitch = max(min(pitch, 89.0), -89.0)
        yaw = (yaw + 180.0) % 360.0 - 180.0
        return pitch, yaw

    def angle_diff(self, a, b):
        d = (a - b + 180) % 360 - 180
        return d

    def in_fov(self, pitch1, yaw1, pitch2, yaw2):
        dp = self.angle_diff(pitch2, pitch1)
        dy = self.angle_diff(yaw2, yaw1)
        # squared distance (optional optimization)
        return (dp * dp + dy * dy) <= (self.cfg.FOV * self.cfg.FOV)

    @staticmethod
    def lerp(a, b, t):
        return a + (b - a) * t

    @staticmethod
    def add_noise(value, max_noise=0.03):
        return value + random.uniform(-max_noise, max_noise)

    def clamp_angle_diff(self, current, target, max_delta=MAX_DELTA_ANGLE):
        d = self.angle_diff(target, current)
        if abs(d) > max_delta:
            d = max_delta if d > 0 else -max_delta
        return current + d

    def on_click(self, x, y, btn, pressed):
        if btn == mouse.Button.left:
            self.left_down = pressed
            self.aim_start_time = time.perf_counter() if pressed else None
            if not pressed:
                self.shots_fired = 0
                self.last_punch = (0.0, 0.0)
                self.last_aim_angle = None

    def update_learning(self, key, dp, dy, alpha=0.15):
        with self.lock:
            if key not in self.learning_data:
                self.learning_data[key] = deque(maxlen=50)
            if self.learning_data[key]:
                last_dp, last_dy = self.learning_data[key][-1]
                dp = (1 - alpha) * last_dp + alpha * dp
                dy = (1 - alpha) * last_dy + alpha * dy
            self.learning_data[key].append((dp, dy))
            self.learning_dirty = True

    def get_learned_correction(self, key):
        if not self.cfg.enable_learning:
            return 0.0, 0.0
        corrections = self.learning_data.get(key)
        if not corrections:
            return 0.0, 0.0
        dp_avg = sum(x[0] for x in corrections) / len(corrections)
        dy_avg = sum(x[1] for x in corrections) / len(corrections)
        return dp_avg, dy_avg

    def quantize_angle(self, pitch, yaw, shots_fired, step=1.0):
        pitch_q = round(pitch / step) * step
        yaw_q = round(yaw / step) * step
        sf_bin = min(shots_fired, 10)  # binning: 1–10+
        return (pitch_q, yaw_q, sf_bin)

    def get_current_bone_index(self, pawn=None, my_pos=None, pitch=None, yaw=None):
        if not self.cfg.closest_to_crosshair:
            return self.bone_indices.get(self.cfg.target_bone_name, 6)

        if not pawn or not my_pos:
            return self.bone_indices.get("head", 6)

        read = self.read
        bone_pos_fn = self.read_bone_pos
        angle_diff = self.angle_diff
        isnan = self._isnan

        best_index = None
        best_distance = float('inf')

        cfg_bones = self.cfg.bone_indices_to_try
        enable_velocity_prediction = self.cfg.enable_velocity_prediction
        downward_offset = self.cfg.downward_offset
        smoothing = getattr(self.cfg, 'velocity_prediction_factor', 0.1)

        vel = None
        if enable_velocity_prediction:
            vel = read_vec = read(pawn + self.o.m_vecVelocity, "float")  # This needs 3 floats: fix below

        # Read velocity vector fully once outside loop if enabled
        if enable_velocity_prediction:
            vel = self.read_vec3(pawn + self.o.m_vecVelocity)

        for idx in cfg_bones:
            pos = bone_pos_fn(pawn, idx)
            if not pos:
                continue

            if enable_velocity_prediction and vel:
                pos = [pos[i] + vel[i] * smoothing for i in range(3)]

            pos[2] -= downward_offset

            p, y = self.calc_angle(my_pos, pos)
            if isnan(p) or isnan(y):
                continue

            dist = math.hypot(angle_diff(p, pitch), angle_diff(y, yaw))
            if dist < best_distance:
                best_distance = dist
                best_index = idx

        return best_index if best_index is not None else self.bone_indices.get("head", 6)
        
    def run(self):
        prev_weapon_id = None

        def normalize_angle_delta(delta):
            while delta > 180:
                delta -= 360
            while delta < -180:
                delta += 360
            return delta

        def squared_distance(a, b):
            return (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2

        def is_valid_target(pawn, my_team):
            if not pawn:
                return False
            health = self.read(pawn + self.o.m_iHealth)
            if health <= 0:
                return False
            life_state = self.read(pawn + self.o.m_lifeState)
            dormant = self.read(pawn + self.o.m_bDormant, "int")
            team = self.read(pawn + self.o.m_iTeamNum)
            return life_state == 256 and not dormant and (self.cfg.DeathMatch or team != my_team)

        sleep_base = 0.005
        sleep_no_target = 0.02  # more sleep when no target

        while not self.cfg.stop:
            try:
                # Check focus first
                if not self.is_cs2_focused():
                    time.sleep(0.1)
                    continue
                
                if not self.cfg.enabled:
                    time.sleep(sleep_base)
                    continue

                base = self.base
                o = self.o

                pawn = self.read(base + o.dwLocalPlayerPawn, "long")
                if not pawn:
                    time.sleep(sleep_base)
                    continue

                weapon_id = self.weapon_tracker.get_current_weapon_id()
                if weapon_id != prev_weapon_id:
                    self.load_learning()
                    prev_weapon_id = weapon_id

                health = self.read(pawn + o.m_iHealth)
                if health <= 0:
                    time.sleep(sleep_base)
                    continue

                ctrl = self.read(base + o.dwLocalPlayerController, "long")

                if not self.weapon_tracker.is_weapon_valid_for_aim():
                    self.shots_fired = 0
                    self.last_punch = (0.0, 0.0)
                    time.sleep(sleep_base)
                    continue

                my_team = self.read(pawn + o.m_iTeamNum)
                my_pos = self.read_vec3(pawn + o.m_vOldOrigin)
                pitch = self.read(base + o.dwViewAngles, "float")
                yaw = self.read(base + o.dwViewAngles + 4, "float")

                recoil_pitch = self.read(pawn + o.m_aimPunchAngle, "float")
                recoil_yaw = self.read(pawn + o.m_aimPunchAngle + 4, "float")

                entity_list = self.read(base + o.dwEntityList, "long")
                if not entity_list:
                    time.sleep(sleep_base)
                    continue

                target = None
                target_pos = None

                if self.target_id is not None:
                    # Try to validate current target first to avoid scanning entire list
                    t_ctrl = self.get_entity(entity_list, self.target_id)
                    t_pawn = self.get_entity(entity_list, self.read(t_ctrl + o.m_hPlayerPawn) & 0x7FFF) if t_ctrl else 0

                    if is_valid_target(t_pawn, my_team):
                        bone_index = self.get_current_bone_index(t_pawn, my_pos, pitch, yaw)
                        pos = self.read_bone_pos(t_pawn, bone_index) or self.read_vec3(t_pawn + o.m_vOldOrigin)

                        if self.cfg.enable_velocity_prediction:
                            vel = self.read_vec3(t_pawn + o.m_vecVelocity)
                        else:
                            vel = [0, 0, 0]

                        predicted = [pos[i] + vel[i] * 0.1 for i in range(3)]
                        predicted[2] -= self.cfg.downward_offset

                        tp, ty = self.calc_angle(my_pos, predicted)

                        if any(map(math.isnan, (tp, ty))) or not self.in_fov(pitch, yaw, tp, ty):
                            self.target_id = None
                            self.last_target_lost_time = time.time()
                        else:
                            target, target_pos = t_pawn, predicted
                    else:
                        self.target_id = None
                        self.last_target_lost_time = time.time()

                if target is None:
                    if self.last_target_lost_time and (time.time() - self.last_target_lost_time) < self.cfg.target_switch_delay:
                        time.sleep(sleep_no_target)
                        continue

                    min_dist_sq = float("inf")
                    max_entities = self.cfg.max_entities

                    for i in range(max_entities):
                        ctrl_ent = self.get_entity(entity_list, i)
                        if not ctrl_ent or ctrl_ent == ctrl:
                            continue

                        pawn_ent = self.get_entity(entity_list, self.read(ctrl_ent + o.m_hPlayerPawn) & 0x7FFF)
                        if not is_valid_target(pawn_ent, my_team):
                            continue

                        bone_index = self.get_current_bone_index(pawn_ent, my_pos, pitch, yaw)
                        pos = self.read_bone_pos(pawn_ent, bone_index) or self.read_vec3(pawn_ent + o.m_vOldOrigin)

                        if self.cfg.enable_velocity_prediction:
                            vel = self.read_vec3(pawn_ent + o.m_vecVelocity)
                        else:
                            vel = [0, 0, 0]

                        predicted = [pos[i] + vel[i] * 0.1 for i in range(3)]
                        predicted[2] -= self.cfg.downward_offset

                        tp, ty = self.calc_angle(my_pos, predicted)
                        if any(map(math.isnan, (tp, ty))) or not self.in_fov(pitch, yaw, tp, ty):
                            continue

                        dist_sq = squared_distance(my_pos, predicted)
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq
                            target, target_pos, self.target_id = pawn_ent, predicted, i

                if self.left_down:
                    if self.aim_start_time and time.time() - self.aim_start_time < self.cfg.aim_start_delay:
                        continue

                    self.shots_fired += 1

                    if target and target_pos:
                        tp, ty = self.calc_angle(my_pos, target_pos)

                        if abs(self.angle_diff(ty, yaw)) > 90:
                            continue

                        # Recoil compensation with dynamic scaling
                        dynamic_rcs_scale = self.cfg.rcs_scale * min(self.shots_fired / 2, 1.0)

                        compensated_pitch = tp - recoil_pitch * dynamic_rcs_scale
                        compensated_yaw = ty - recoil_yaw * dynamic_rcs_scale

                        compensated_pitch = self.clamp_angle_diff(pitch, compensated_pitch)
                        compensated_yaw = self.clamp_angle_diff(yaw, compensated_yaw)

                        # Smoothing with jitter
                        base_smooth = self.cfg.smooth_base
                        smooth_var = self.cfg.smooth_var
                        smoothing = max(0.05, min(base_smooth + random.uniform(-smooth_var, smooth_var), 0.25))

                        # Learning correction
                        key = self.quantize_angle(compensated_pitch, compensated_yaw, self.shots_fired)
                        dp, dy = self.get_learned_correction(key)
                        compensated_pitch += dp
                        compensated_yaw += dy

                        interp_pitch = pitch + (compensated_pitch - pitch) * smoothing
                        interp_yaw = yaw + (compensated_yaw - yaw) * smoothing

                        sp = self.add_noise(interp_pitch, 0.03)
                        sy = self.add_noise(interp_yaw, 0.03)
                        sp, sy = self.normalize(sp, sy)

                        delta_pitch = normalize_angle_delta(sp - pitch)
                        delta_yaw = normalize_angle_delta(sy - yaw)

                        delta_pitch = max(min(delta_pitch, self.MAX_DELTA_ANGLE), -self.MAX_DELTA_ANGLE)
                        delta_yaw = max(min(delta_yaw, self.MAX_DELTA_ANGLE), -self.MAX_DELTA_ANGLE)

                        mouse_dx = int(-delta_yaw / self.SENSITIVITY)
                        mouse_dy = int(-delta_pitch / self.SENSITIVITY) * self.INVERT_Y

                        max_mouse_move = 15
                        mouse_dx = max(min(mouse_dx, max_mouse_move), -max_mouse_move)
                        mouse_dy = max(min(mouse_dy, max_mouse_move), -max_mouse_move)

                        move_mouse(mouse_dx, mouse_dy)

                        if self.last_aim_angle:
                            lp, ly = self.last_aim_angle
                            if abs(self.angle_diff(sp, lp)) > 0.002 or abs(self.angle_diff(sy, ly)) > 0.002:
                                dp_learn = max(min(sp - pitch, 1.0), -1.0)
                                dy_learn = max(min(sy - yaw, 1.0), -1.0)
                                if abs(dp_learn) > 0.05 or abs(dy_learn) > 0.05:
                                    self.update_learning(key, dp_learn, dy_learn)

                        self.last_aim_angle = (sp, sy)
                    else:
                        self.last_aim_angle = None

                else:
                    # Reset shots when not firing
                    self.shots_fired = 0
                    self.last_aim_angle = None

                time.sleep(sleep_base + random.uniform(0, 0.003))

            except (EOFError, BrokenPipeError):
                break
            except Exception as e:
                print(f"[!] Exception in AimbotRCS: {e}")
                time.sleep(0.3)

        if self.cfg.enable_learning:
            self.save_learning()

        print("[AimbotRCS] Stopped.")
    
def start_aim_rcs(cfg):
    print("[*] Starting AimRCS...")
    AimbotRCS(cfg).run()
