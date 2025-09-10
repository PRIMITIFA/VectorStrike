import time
import random
import keyboard
import pymem
import pymem.process
from pynput.mouse import Controller, Button
from win32gui import GetWindowText, GetForegroundWindow
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
from Process.offsets import Offsets
from Process.process_handler import CS2Process
from Features.key_mapping import key_mapper

class SetTriggerKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Trigger Key")
        self.setModal(True)
        self.selected_key = None
        
        # UI Setup
        self.layout = QVBoxLayout()
        self.key_label = QLabel("Press any key...")
        self.key_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.key_label)
        self.setLayout(self.layout)

    def keyPressEvent(self, event):
        """Handle key press events directly within the dialog."""
        key = event.key()

        # Ignore modifier keys
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return

        # Comprehensive key mapping
        key_map = {
            Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3", Qt.Key_F4: "f4",
            Qt.Key_F5: "f5", Qt.Key_F6: "f6", Qt.Key_F7: "f7", Qt.Key_F8: "f8",
            Qt.Key_F9: "f9", Qt.Key_F10: "f10", Qt.Key_F11: "f11", Qt.Key_F12: "f12",
            Qt.Key_Insert: "insert", Qt.Key_Delete: "delete", Qt.Key_Home: "home",
            Qt.Key_End: "end", Qt.Key_PageUp: "page up", Qt.Key_PageDown: "page down",
            Qt.Key_Left: "left", Qt.Key_Right: "right", Qt.Key_Up: "up", Qt.Key_Down: "down",
            Qt.Key_A: "a", Qt.Key_B: "b", Qt.Key_C: "c", Qt.Key_D: "d", Qt.Key_E: "e",
            Qt.Key_F: "f", Qt.Key_G: "g", Qt.Key_H: "h", Qt.Key_I: "i", Qt.Key_J: "j",
            Qt.Key_K: "k", Qt.Key_L: "l", Qt.Key_M: "m", Qt.Key_N: "n", Qt.Key_O: "o",
            Qt.Key_P: "p", Qt.Key_Q: "q", Qt.Key_R: "r", Qt.Key_S: "s", Qt.Key_T: "t",
            Qt.Key_U: "u", Qt.Key_V: "v", Qt.Key_W: "w", Qt.Key_X: "x", Qt.Key_Y: "y",
            Qt.Key_Z: "z",
            Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3", Qt.Key_4: "4",
            Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7", Qt.Key_8: "8", Qt.Key_9: "9",
            Qt.Key_Space: "space", Qt.Key_Tab: "tab", Qt.Key_CapsLock: "caps lock",
            Qt.Key_NumLock: "num lock", Qt.Key_ScrollLock: "scroll lock",
            Qt.Key_Backspace: "backspace", Qt.Key_Enter: "enter", Qt.Key_Return: "enter",
            Qt.Key_Escape: "esc", Qt.Key_Print: "print screen",
            Qt.Key_Minus: "-", Qt.Key_Plus: "+", Qt.Key_Equal: "=",
            Qt.Key_BracketLeft: "[", Qt.Key_BracketRight: "]",
            Qt.Key_Backslash: "\\", Qt.Key_Semicolon: ";", Qt.Key_Apostrophe: "'",
            Qt.Key_Comma: ",", Qt.Key_Period: ".", Qt.Key_Slash: "/",
            Qt.Key_QuoteLeft: "`"
        }
        
        self.selected_key = key_map.get(key)

        if self.selected_key:
            self.key_label.setText(f"Selected: {self.selected_key.upper()}")
            # Close the dialog after a short delay
            QTimer.singleShot(100, self.accept)
        
        event.accept()

    def get_selected_key(self):
        """Return the captured key."""
        return self.selected_key
        
class TriggerBot:
    def __init__(self, triggerKey="shift", shootTeammates=False, shared_config=None):
        self.triggerKey = triggerKey
        print(f"[DEBUG] TriggerBot initialized with key: {self.triggerKey}")
        self.shootTeammates = shootTeammates

        self.cs2 = CS2Process()
        self.cs2.initialize()

        self.pm = pymem.Pymem("cs2.exe")
        self.client = self.cs2.module_base

        self.offsets_manager = Offsets()
        self.mouse = Controller()
        self.last_shot_time = 0

        # Shared configuration object from GUI
        if shared_config:
            self.shared_config = shared_config
        else:
            class DummyConfig:
                stop = False
                triggerbot_cooldown = 0.8
                triggerbot_enabled = True
                shoot_teammates = False
            self.shared_config = DummyConfig()

    def shoot(self):
        self.mouse.press(Button.left)
        time.sleep(0.005)  # very short tap
        self.mouse.release(Button.left)

    def enable(self):
        try:
            if GetWindowText(GetForegroundWindow()) != "Counter-Strike 2":
                return

            # Skip key check if triggerbot is set to always on
            if hasattr(self.shared_config, 'triggerbot_always_on') and self.shared_config.triggerbot_always_on:
                pass  # Continue execution without key check
            else:
                # Check if trigger key is pressed using the KeyMapper utility
                try:
                    key_pressed = key_mapper.is_key_pressed(self.triggerKey)
                    if not key_pressed:
                        return
                except Exception as e:
                    print(f"[TriggerBot] Error checking key press for '{self.triggerKey}': {e}")
                    return

            # Read local player pawn pointer safely
            player = 0
            try:
                player = self.pm.read_longlong(self.client + self.offsets_manager.dwLocalPlayerPawn)
            except Exception:
                return  # Invalid pointer, likely in menu

            if not player or player == 0:
                return  # Not in game

            entityId = 0
            try:
                entityId = self.pm.read_int(player + self.offsets_manager.m_iIDEntIndex)
            except Exception:
                return

            if entityId <= 0:
                return

            entList = 0
            try:
                entList = self.pm.read_longlong(self.client + self.offsets_manager.dwEntityList)
            except Exception:
                return

            if not entList or entList == 0:
                return

            # Safe read entity pointer
            entEntry = 0
            try:
                entEntry = self.pm.read_longlong(entList + 0x8 * (entityId >> 9) + 0x10)
                entity = self.pm.read_longlong(entEntry + 120 * (entityId & 0x1FF))
            except Exception:
                return

            if not entity or entity == 0:
                return

            # Now safe to read other entity data
            entityTeam = self.pm.read_int(entity + self.offsets_manager.m_iTeamNum)
            entityHp = self.pm.read_int(entity + self.offsets_manager.m_iHealth)
            playerTeam = self.pm.read_int(player + self.offsets_manager.m_iTeamNum)

            cooldown = getattr(self.shared_config, "triggerbot_cooldown", 0.8)
            allow_team = getattr(self.shared_config, "shoot_teammates", False)

            if entityTeam != 0 and entityHp > 0:
                if allow_team or (entityTeam != playerTeam):
                    current_time = time.time()
                    if current_time - self.last_shot_time >= cooldown:
                        self.shoot()
                        self.last_shot_time = current_time

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"[TriggerBot] Exception: {e}")

        def toggle_shoot_teammates(self, state):
            self.shootTeammates = state == Qt.Checked
            self.shared_config.shoot_teammates = self.shootTeammates

        def run(self):
            print("[*] TriggerBot started.")
            try:
                while not getattr(self.shared_config, "stop", False):
                    if getattr(self.shared_config, "triggerbot_enabled", True):
                        self.enable()
                    time.sleep(0.005)  # Fast polling
            except KeyboardInterrupt:
                print("[*] TriggerBot interrupted by user.")
            finally:
                print("[TriggerBot] Stopped.")

# Standalone test run
if __name__ == "__main__":
    class DummySharedConfig:
        stop = False
        triggerbot_enabled = True
        shoot_teammates = False
        triggerbot_cooldown = 0.2

    bot = TriggerBot(triggerKey="shift", shared_config=DummySharedConfig())
    bot.run()
