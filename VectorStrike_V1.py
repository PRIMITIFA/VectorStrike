import sys
import os

# The launcher is run from the project root, so the current working directory should be the project root.
project_root = os.getcwd()
venv_site_packages = os.path.join(project_root, 'vxo19ciu', 'Lib', 'site-packages')

if venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

import os
import sys
import time
import string
import ctypes
from random import uniform
from datetime import datetime
import threading
import math
import shutil

import keyboard
import winsound
import requests
from requests import get
import pymem
import pymem.process
import pyMeow as pw_module
from pynput.mouse import Controller, Button
from win32gui import GetWindowText, GetForegroundWindow

from PyQt5.QtCore import Qt, QEvent, QTimer, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import QPixmap, QColor, QPainter, QPen, QBrush
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QGraphicsDropShadowEffect

import multiprocessing
import time
import signal
import json

from Process.offsets import Offsets
from Process.entity import Entity
from Process.process_handler import CS2Process

from process_starters import aim_process, bhop_process, glow_process

from Features.triggerbot import TriggerBot, SetTriggerKeyDialog
from Features.key_mapping import key_mapper
from Features.glow import CS2GlowManager 
from Features.Wallhack import WallHack

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
def read_json(path):
    with open(path, "r") as f:
        return json.load(f)

def get_primary_monitor_refresh_rate():
    try:
        user32 = ctypes.windll.user32
        desktop_dc = user32.GetDC(0)
        refresh_rate = ctypes.windll.gdi32.GetDeviceCaps(desktop_dc, 116)
        user32.ReleaseDC(0, desktop_dc)
        return refresh_rate if refresh_rate > 0 else 60
    except Exception as e:
        print(f"Failed to get refresh rate: {e}")
        return 60

def get_all_monitor_refresh_rates():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration")
        refresh_rates = []
        primary_rate = get_primary_monitor_refresh_rate()
        refresh_rates.append(primary_rate)
        winreg.CloseKey(key)
        return max(refresh_rates) if refresh_rates else 60
    except Exception as e:
        # Ignore "Access is denied" errors silently, print others
        if "Access is denied" not in str(e):
            print(f"Failed to get monitor refresh rates: {e}")
        return get_primary_monitor_refresh_rate()

def main():
    multiprocessing.freeze_support()
    manager = multiprocessing.Manager()
    shared_config = manager.Namespace()

    shared_config.enabled = True
    shared_config.stop = False
    shared_config.bhop_enabled = True
    shared_config.glow = False

    shared_config.FOV = 2.0
    shared_config.smooth_base = 0.12
    shared_config.smooth_var = 0.00
    shared_config.rcs_smooth_base = 0.44
    shared_config.rcs_smooth_var = 0.01
    shared_config.rcs_scale = 2.6
    shared_config.rcs_enabled = True
    shared_config.stabilize_shots = 4
    shared_config.max_entities = 64
    shared_config.target_switch_delay = 0.2
    shared_config.aim_start_delay = 0.05
    shared_config.downward_offset = 62
    shared_config.target_bone_name = "head"
    shared_config.closest_to_crosshair = False
    shared_config.DeathMatch = False
    shared_config.bone_indices_to_try = [6, 18]
    shared_config.sensitivity_scale = 0.5
    
    shared_config.sensitivity_scale = 1.74
    shared_config.mouse_scale = 1.0
    
    shared_config.enable_learning = True
    shared_config.enable_velocity_prediction = False
    shared_config.monitor_sync_enabled = True

    shared_config.triggerbot_enabled = False
    shared_config.triggerbot_cooldown = 0.8
    shared_config.shoot_teammates = False
    shared_config.triggerbot_always_on = False

    shared_config.game_fov = 90

    aim_p = multiprocessing.Process(target=aim_process, args=(shared_config,), name="AimProcess")
    bhop_p = multiprocessing.Process(target=bhop_process, args=(shared_config,), name="BHopProcess")
    glow_p = multiprocessing.Process(target=glow_process, args=(shared_config,), name="GlowProcess")

    aim_p.start()
    bhop_p.start()
    glow_p.start()

    app = QApplication([])

    # Check if CS2 is running before starting processes
    try:
        import psutil
        cs2_running = any("cs2.exe" in p.name().lower() for p in psutil.process_iter(['name']))
        if not cs2_running:
            print("\n"+"="*60)
            print("[!] CS2 IS NOT RUNNING")
            print("[!] Please start Counter-Strike 2 first")
            print("[!] Make sure to run this cheat as Administrator for proper permissions")
            print("="*60)
            input("Press Enter to exit...")
            shared_config.stop = True
            shared_config.bhop_enabled = False
            shared_config.glow = False
            aim_p.terminate()
            bhop_p.terminate()
            glow_p.terminate()
            manager.shutdown()
            return
    except ImportError:
        print("[!] Warning: psutil not installed, skipping CS2 process check")
    except Exception as e:
        print(f"[!] Warning: Could not check if CS2 is running: {e}")

    cs2_process = CS2Process()
    print("[*] Waiting for CS2 process...")
    try:
        cs2_process.initialize()
        print("[*] Successfully connected to CS2 process")
    except RuntimeError as e:
        print("\n"+"="*60)
        print("[!] CS2 IS NOT RUNNING")
        print("[!] Please start Counter-Strike 2 first")
        print("[!] Make sure to run this cheat as Administrator for proper permissions")
        print("="*60)
        input("Press Enter to exit...")
        shared_config.stop = True
        shared_config.bhop_enabled = False
        shared_config.glow = False
        aim_p.terminate()
        bhop_p.terminate()
        glow_p.terminate()
        manager.shutdown()
        return

    program = Program(shared_config, cs2_process=cs2_process)

    def signal_handler(sig, frame):
        print("[*] Signal received, stopping...")
        shared_config.stop = True
        shared_config.bhop_enabled = False
        shared_config.glow = False

    signal.signal(signal.SIGINT, signal_handler)

    try:
        program.Run()
        app.exec_()
    except Exception as e:
        print(f"[!] Exception in main: {e}")
    finally:
        shared_config.stop = True
        shared_config.bhop_enabled = False
        shared_config.glow = False

        for p in (aim_p, bhop_p, glow_p):
            if p.is_alive():
                p.join(timeout=3)
                if p.is_alive():
                    print(f"[!] Force terminating process: {p.name}")
                    p.terminate()

        manager.shutdown()

        print("[*] Shutdown complete.")

        
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class NoWheelSlider(QSlider):
    def wheelEvent(self, event):
        event.ignore()

class ColorPickerWidget(QWidget):
    _instance = None

    def __init__(self, callback, initial_color="#FF0000"):
        super().__init__()
        self.callback = callback
        self.current_color = QColor(initial_color)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setObjectName("ColorPickerWidget")
        self.setFixedSize(350, 320)

        self._init_ui()
        self._apply_styles()
        self._set_shadow()

        ColorPickerWidget._instance = self

    # ─────────────── UI SETUP ─────────────── #
    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)

        self._add_preset_colors()
        self._add_rgb_sliders()
        self._add_hex_input()
        self._add_action_buttons()

    def _set_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setXOffset(2)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    # ─────────────── COLOR PRESETS ─────────────── #
    def _add_preset_colors(self):
        presets = [
            "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF",
            "#FFFFFF", "#FFA500", "#800080", "#FFC0CB", "#00FF80", "#000080",
            "#808080", "#000000", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"
        ]
        row_layout = QHBoxLayout()
        for i, color in enumerate(presets):
            btn = QPushButton()
            btn.setFixedSize(16, 16)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(255, 255, 255, 0.8);
                }}
            """)
            btn.clicked.connect(lambda _, c=color: self.set_color_from_hex(c))
            row_layout.addWidget(btn)

            if (i + 1) % 12 == 0:
                self.layout.addLayout(row_layout)
                row_layout = QHBoxLayout()

        if row_layout.count() > 0:
            self.layout.addLayout(row_layout)

    # ─────────────── SLIDERS ─────────────── #
    def _add_rgb_sliders(self):
        self.red_slider, self.red_label = self._create_slider("R", self.current_color.red())
        self.green_slider, self.green_label = self._create_slider("G", self.current_color.green())
        self.blue_slider, self.blue_label = self._create_slider("B", self.current_color.blue())

    def _create_slider(self, name, value):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(f"{name}:"))

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(value)
        slider.valueChanged.connect(self.update_color_from_sliders)
        layout.addWidget(slider)

        label = QLabel(str(value))
        label.setFixedWidth(30)
        layout.addWidget(label)

        self.layout.addLayout(layout)
        return slider, label

    # ─────────────── HEX + PREVIEW ─────────────── #
    def _add_hex_input(self):
        layout = QHBoxLayout()

        layout.addWidget(QLabel("Hex:"))

        self.hex_input = QLineEdit(self.current_color.name())
        self.hex_input.textChanged.connect(self.update_color_from_hex)
        layout.addWidget(self.hex_input)

        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 20)
        self.update_color_preview()
        layout.addWidget(self.color_preview)

        self.layout.addLayout(layout)

    # ─────────────── APPLY / CANCEL BUTTONS ─────────────── #
    def _add_action_buttons(self):
        layout = QHBoxLayout()

        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")

        apply_btn.clicked.connect(self.apply_color)
        cancel_btn.clicked.connect(self.close_picker)

        layout.addWidget(apply_btn)
        layout.addWidget(cancel_btn)
        self.layout.addLayout(layout)

    # ─────────────── STYLESHEET ─────────────── #
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 15, 20, 220);
                border: 2px solid rgba(50, 50, 70, 180);
                border-radius: 12px;
            }

            QPushButton {
                background-color: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid rgba(100, 100, 130, 160);
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(60, 60, 90, 220);
                border: 1px solid rgba(130, 130, 180, 180);
            }
            QPushButton:pressed {
                background-color: rgba(30, 30, 50, 200);
                border: 1px solid rgba(170, 170, 220, 200);
            }

            QLineEdit {
                background-color: rgba(30, 30, 45, 230);
                border: 2px solid rgba(80, 80, 110, 160);
                border-radius: 6px;
                color: white;
                padding: 5px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid rgba(140, 140, 200, 200);
            }

            QLabel {
                color: rgba(230, 230, 240, 240);
                font-size: 12px;
                font-weight: bold;
            }

            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
                background-color: rgba(60, 60, 90, 180);
            }
            QSlider::handle:horizontal {
                background-color: rgba(180, 180, 230, 200);
                border: 2px solid rgba(220, 220, 255, 200);
                border-radius: 6px;
                width: 14px;
                height: 14px;
                margin: -4px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: rgba(200, 200, 255, 220);
                border: 2px solid rgba(240, 240, 255, 255);
            }
        """)

    # ─────────────── UPDATE METHODS ─────────────── #
    def update_color_from_sliders(self):
        r, g, b = self.red_slider.value(), self.green_slider.value(), self.blue_slider.value()
        self.red_label.setText(str(r))
        self.green_label.setText(str(g))
        self.blue_label.setText(str(b))
        self.current_color = QColor(r, g, b)
        self.update_hex_input()
        self.update_color_preview()

    def update_color_from_hex(self):
        hex_text = self.hex_input.text()
        if QColor(hex_text).isValid():
            self.current_color = QColor(hex_text)
            self.update_sliders()
            self.update_color_preview()

    def update_sliders(self):
        self.red_slider.setValue(self.current_color.red())
        self.green_slider.setValue(self.current_color.green())
        self.blue_slider.setValue(self.current_color.blue())

    def update_hex_input(self):
        self.hex_input.setText(self.current_color.name())

    def update_color_preview(self):
        self.color_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {self.current_color.name()};
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 4px;
            }}
        """)

    # ─────────────── COLOR SELECTION ─────────────── #
    def set_color_from_hex(self, hex_color):
        self.current_color = QColor(hex_color)

        for widget in (self.red_slider, self.green_slider, self.blue_slider, self.hex_input):
            widget.blockSignals(True)

        self.update_sliders()
        self.update_hex_input()
        self.update_color_preview()

        for widget in (self.red_slider, self.green_slider, self.blue_slider, self.hex_input):
            widget.blockSignals(False)

    def apply_color(self):
        color_map = {
            "#ff0000": "red", "#00ff00": "green", "#0000ff": "blue",
            "#ffff00": "yellow", "#00ffff": "cyan", "#ff00ff": "magenta",
            "#ffffff": "white", "#ffa500": "orange", "#800080": "purple",
            "#ffc0cb": "pink", "#00ff80": "lime", "#000080": "navy",
            "#808080": "gray", "#000000": "black"
        }
        hex_color = self.current_color.name().lower()
        self.callback(color_map.get(hex_color, hex_color))
        self.close_picker()

    # ─────────────── WINDOW CONTROL ─────────────── #
    def show_picker(self, position: QPoint):
        if ColorPickerWidget._instance and ColorPickerWidget._instance != self:
            ColorPickerWidget._instance.close_picker()

        screen = QApplication.primaryScreen().geometry()
        x = min(position.x(), screen.width() - self.width() - 10)
        y = min(position.y(), screen.height() - self.height() - 10)

        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def close_picker(self):
        self.hide()
        if ColorPickerWidget._instance == self:
            ColorPickerWidget._instance = None

    def closeEvent(self, event):
        self.close_picker()
        super().closeEvent(event)

class ColorButton(QPushButton):
    COLOR_MAP = {
        "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
        "yellow": "#FFFF00", "cyan": "#00FFFF", "magenta": "#FF00FF",
        "white": "#FFFFFF", "orange": "#FFA500", "purple": "#800080",
        "pink": "#FFC0CB", "lime": "#00FF80", "navy": "#000080",
        "gray": "#808080", "black": "#000000"
    }

    def __init__(self, color_name: str, text: str, callback):
        super().__init__("")
        self.callback = callback
        self.current_color = color_name
        self.color_picker = None

        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.show_color_picker)
        self.update_button_style()

    def set_color(self, color_name: str):
        """Update internal color and restyle button."""
        self.current_color = color_name
        self.update_button_style()

    def get_hex_color(self, color_name: str) -> str:
        """Return hex code from color name or fallback."""
        name = color_name.lower()
        if name.startswith('#') and QColor(name).isValid():
            return name
        return self.COLOR_MAP.get(name, "#FF0000")

    def show_color_picker(self):
        """Display color picker widget."""
        if ColorPickerWidget._instance:
            ColorPickerWidget._instance.close_picker()

        hex_color = self.get_hex_color(self.current_color)
        self.color_picker = ColorPickerWidget(self.on_color_selected, hex_color)
        self.color_picker.set_color_from_hex(hex_color)

        position = self.mapToGlobal(self.rect().bottomLeft()) + QPoint(0, 5)
        self.color_picker.show_picker(position)

    def on_color_selected(self, color_name: str):
        """Handle color picker selection."""
        self.set_color(color_name)
        self.callback(color_name)

    def update_button_style(self):
        """Set button style with appropriate text contrast."""
        hex_color = self.get_hex_color(self.current_color)
        qcolor = QColor(hex_color)

        # Compute luminance for contrast
        luminance = (0.299 * qcolor.red() + 0.587 * qcolor.green() + 0.114 * qcolor.blue()) / 255
        text_color = "#000000" if luminance > 0.55 else "#FFFFFF"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_color};
                color: {text_color};
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid rgba(255, 255, 255, 0.7);
            }}
            QPushButton:pressed {{
                border: 2px solid rgba(255, 255, 255, 1.0);
            }}
        """)

        
class WindowToggleSignal(QObject):
    toggle_requested = pyqtSignal()

class Program:
    def __init__(self, shared_config, cs2_process=None):
        self.shared_config = shared_config
        self._drag_pos = None

        try:

            self.detected_refresh_rate = get_all_monitor_refresh_rates()
            self.monitor_sync_enabled = getattr(shared_config, 'monitor_sync_enabled', True)
            self.fps = self.detected_refresh_rate if self.monitor_sync_enabled else 144

            print(f"[*] Detected monitor refresh rate: {self.detected_refresh_rate} Hz")
            print(f"[*] ESP FPS: {self.fps}")

            self.cs2 = cs2_process or CS2Process()
            if cs2_process is None:
                self.cs2.initialize()

            self.process = self.cs2.process
            self.module = self.cs2.module_base

            self.wall = WallHack(self.process, self.module, shared_config=self.shared_config)

            self.triggerbot = None
            self.trigger_key = None  # Will be set when triggerbot is enabled
            self.trigger_team = False
            self.fov_overlay = None
            self.fov_overlay_enabled = False
            self.fov_overlay_color = "green"
            self.bomb_esp_enabled = False

            self.window_visible = True
            self.keyboard_listener = None
            self.menu_toggle_key = "insert"  # Default menu toggle key
            self.last_key_press_time = 0  # For improved debouncing
            self.key_press_cooldown = 0.2  # 200ms cooldown for better responsiveness
            self._key_states = {}  # Track key states for better debouncing
            
            self.toggle_signal = WindowToggleSignal()

            self.gui_elements = {}

            self.create_gui()
            
            self.toggle_signal.toggle_requested.connect(self.toggle_window_visibility)
            
            self.start_menu_key_listener()

        except Exception as e:
            exit(f"Error: Enable only after opening Counter Strike 2\nDetails: {e}")

    def toggle_window_visibility(self):
        try:
            if self.window_visible:
                self.window.hide()
                self.window_visible = False
            else:
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()
                self.window.setFocus()
                self.window_visible = True
        except Exception as e:
            print(f"[!] Error toggling window: {e}")
            self.window_visible = True

    def is_key_press_allowed(self, key_name):
        """Optimized debouncing with per-key state tracking"""
        # Process UI events to prevent freezing
        QApplication.processEvents()
        
        current_time = time.time()
        
        if key_name in self._key_states:
            if current_time - self._key_states[key_name] < self.key_press_cooldown:
                return False
        
        self._key_states[key_name] = current_time
        
        # Process UI events again after updating state
        QApplication.processEvents()
        
        return True

    def start_menu_key_listener(self):
        """Optimized keyboard listener with better error handling"""
        print(f"[*] Starting {self.menu_toggle_key} key listener...")
        
        # Process UI events to prevent freezing
        QApplication.processEvents()
        
        # Clean up existing listener
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
                self.keyboard_listener.join(timeout=0.3)
            except:
                pass
            self.keyboard_listener = None
        
        try:
            from pynput import keyboard as pynput_keyboard
            
            # Use KeyMapper to get the pynput key object
            target_key = key_mapper.get_pynput_key(self.menu_toggle_key)
            print(f"[*] Using key: {self.menu_toggle_key} (mapped to: {target_key})")
            
            # Process UI events to prevent freezing
            QApplication.processEvents()
            
            def on_press(key):
                # Use KeyMapper to check if the pressed key matches the target key
                key_match = key_mapper.is_key_match(key, target_key)
                
                if key_match and self.is_key_press_allowed(self.menu_toggle_key):
                    try:
                        # Process UI events before emitting signal
                        QApplication.processEvents()
                        self.toggle_signal.toggle_requested.emit()
                    except Exception as e:
                        print(f"[!] Toggle error: {e}")
            
            self.keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
            self.keyboard_listener.start()
            print(f"[*] Keyboard listener active for {self.menu_toggle_key}")
            
            # Process UI events after starting listener
            QApplication.processEvents()
            
        except ImportError:
            print("[!] pynput not available, using fallback...")
            self._start_fallback_listener()
        except Exception as e:
            print(f"[!] Failed to start listener: {e}")
            
        # Final UI event processing
        QApplication.processEvents()

    def _start_fallback_listener(self):
        """Optimized fallback keyboard detection"""
        # Process UI events before starting the thread
        QApplication.processEvents()
        
        def fallback_thread():
            last_state = False
            while True:
                try:
                    current_state = keyboard.is_pressed(self.menu_toggle_key)
                    if current_state and not last_state and self.is_key_press_allowed(self.menu_toggle_key):
                        # Use a signal-slot connection to safely update UI from another thread
                        # This avoids direct UI manipulation from a non-UI thread
                        self.toggle_signal.toggle_requested.emit()
                    last_state = current_state
                    time.sleep(0.05)
                except Exception as e:
                    print(f"[!] Fallback error: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=fallback_thread, daemon=True)
        thread.start()
        
        # Process UI events after starting the thread
        QApplication.processEvents()

    def mk_cb(self, name, conf_key, conn=None, gui_key=None, target=None, initial_state=None):
        target_obj = target if target is not None else self.wall
        
        # Determine the initial checked state
        if initial_state is not None:
            checked = initial_state
        else:
            checked = getattr(target_obj, conf_key, False)

        cb = QCheckBox(name)
        cb.setChecked(checked)

        # Connect the stateChanged signal
        if conn:
            # For custom connection functions, we might need to pass the state explicitly
            if callable(conn):
                cb.stateChanged.connect(conn)
        else:
            # Default behavior: set attribute on target object
            cb.stateChanged.connect(lambda state, key=conf_key: setattr(target_obj, key, state == Qt.Checked))

        # Store the checkbox in gui_elements if a key is provided
        if gui_key:
            self.gui_elements[gui_key] = cb
        
        return cb

    def create_gui(self):
        self.window = QWidget()
        self.window.setWindowTitle(f"GameBarOverlay ")
        self.window.setFixedSize(1100, 700)
        
        self.window.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool |
            Qt.WindowSystemMenuHint
        )
        
        self.window.setWindowOpacity(1.0)
        self.window.setMouseTracking(True)
        
        self.window.raise_()
        self.window.activateWindow()

        self.window.mousePressEvent = self.mousePressEvent
        self.window.mouseMoveEvent = self.mouseMoveEvent
        self.window.mouseReleaseEvent = self.mouseReleaseEvent

        self.window.setStyleSheet("""
        QWidget {
            background-color: #000000;
            color: #e4e6eb;
            font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
            font-size: 14px;
        }

        QTabWidget::pane {
            background-color: #1a1d24;
            border-radius: 12px;
            padding: 8px;
            border-left: 1px solid #2a2e3b;
            border-right: 1px solid #2a2e3b;
            border-bottom: 1px solid #2a2e3b;
            border-top: none;  /* Remove top border */
            margin-top: -1px;  /* Pull pane up */
        }

        QTabBar {
            background-color: #1a1d24;
            margin: 0;
            padding: 0;
            border: none;
        }

        QTabBar::tab {
            background-color: #1a1d24;
            color: #9fa6bd;
            padding: 10px 20px;
            margin: 0 6px 0 6px;  /* no top margin */
            border-bottom: 2px solid transparent;
            font-weight: 500;
        }

        QTabBar::tab:selected {
            color: #ffffff;
            border-bottom: 2px solid #4e8cff;
            background-color: #1f232b;
        }

        QTabBar::tab:hover {
            color: #ffffff;
            background-color: #1d2128;
        }

        /* BUTTONS */
        QPushButton {
            background-color: #2e3547;
            color: #e6e8ef;
            padding: 15px 30px;
            border-radius: 8px;
            font-weight: 500;
            font-size: 16px;
            border: none;
        }

        QPushButton:hover {
            background-color: #3b445c;
        }

        QPushButton:pressed {
            background-color: #526080;
        }

        /* CHECKBOXES */
        QCheckBox {
            spacing: 16px;
            font-weight: 500;
            color: #c2c6d6;
            padding: 4px 0;
        }

        QCheckBox::indicator {
            width: 24px;
            height: 24px;
            border: 2px solid #4e8cff;
            border-radius: 5px;
            background: transparent;
        }

        QCheckBox::indicator:checked {
            background-color: #4e8cff;
            image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'><path fill='white' d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z'/></svg>");
        }

        /* LABELS */
        QLabel {
            font-size: 13px;
            color: #ced2e3;
            padding: 4px 0;
        }

        /* SLIDERS */
        QSlider::groove:horizontal {
            height: 6px;
            background: #2b2f3b;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background: #4e8cff;
            border-radius: 8px;
            width: 16px;
            height: 16px;
            margin: -5px 0;
        }

        QSlider::handle:horizontal:hover {
            background: #6b9eff;
        }

        QSlider::handle:horizontal:pressed {
            background: #8ab5ff;
        }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        top_info = QWidget()
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Logo section
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(40, 40)
        self.logo_label.setStyleSheet("background-color: rgba(30, 30, 45, 150); border-radius: 5px;")
        
        # Set default logo text
        self.logo_label.setText("VS")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("color: #7a8cc7; font-weight: 800; font-size: 18px; background-color: rgba(30, 30, 45, 150); border-radius: 5px;")
        
        # Make logo clickable for upload
        self.logo_label.setToolTip("Click to upload custom logo")
        self.logo_label.setCursor(Qt.PointingHandCursor)
        self.logo_label.mousePressEvent = self.upload_logo
        
        logo_layout.addWidget(self.logo_label)
        top_layout.addWidget(logo_container)
        
        # Title and toggle key info
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        ghax_label = QLabel("VectorStrike CS2 Cheat")
        ghax_label.setStyleSheet("color: #7a8cc7; font-weight: 600; font-size: 11px;")
        ghax_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_layout.addWidget(ghax_label)

        self.toggle_key_label = QLabel(f"Press {self.menu_toggle_key.upper()} to Toggle Menu")
        self.toggle_key_label.setStyleSheet("color: #90EE90; font-weight: 500; font-size: 10px;")
        self.toggle_key_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_layout.addWidget(self.toggle_key_label)
        
        top_layout.addWidget(title_container)
        
        # Spacer
        top_layout.addSpacerItem(QSpacerItem(100, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Exit button (smaller)
        quit_button = QPushButton("Exit")
        quit_button.setFixedSize(60, 30)
        quit_button.setStyleSheet("padding: 5px; font-size: 12px;")
        quit_button.clicked.connect(self.quit_vectorstrike)
        top_layout.addWidget(quit_button)

        top_info.setLayout(top_layout)
        main_layout.addWidget(top_info)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)
        tabs.setDocumentMode(True)

        def tab_widget(widgets, two_columns=False):
            container = QWidget()
            if two_columns:
                layout = QHBoxLayout()
                layout.setContentsMargins(15, 10, 15, 10)
                layout.setSpacing(15)
                
                left_col = QVBoxLayout()
                left_col.setSpacing(10)
                
                right_col = QVBoxLayout()
                right_col.setSpacing(10)
                
                half = (len(widgets) + 1) // 2
                for w in widgets[:half]:
                    left_col.addWidget(w)
                for w in widgets[half:]:
                    right_col.addWidget(w)
                    
                left_col.addStretch()
                right_col.addStretch()
                layout.addLayout(left_col)
                layout.addLayout(right_col)
                container.setLayout(layout)
            else:
                layout = QVBoxLayout()
                layout.setContentsMargins(15, 10, 15, 10)
                layout.setSpacing(10)
                for w in widgets:
                    layout.addWidget(w)
                layout.addStretch()
                container.setLayout(layout)
            return container

        esp_features = [
            ("Watermark", self.toggle_watermark, getattr(self.wall, 'watermark_enabled', False)),
            ("Box ESP", self.toggle_box_esp, False),
            ("Line ESP", self.toggle_line_esp, False),
            ("Skeleton ESP", self.toggle_skeleton_esp, False),
            ("Bone ESP", self.toggle_bone_esp, getattr(self.wall, 'bone_esp_enabled', False)),
            ("Head ESP", self.toggle_head_esp, False),
            ("Name ESP", self.toggle_name_esp, False),
            ("Health ESP", self.toggle_health_esp, False),
            ("Health Bar", self.toggle_healthbar, False),
            ("Armor Bar", self.toggle_armorbar, getattr(self.wall, 'armorbar_enabled', False)),
            ("Armor ESP", self.toggle_armoresp, getattr(self.wall, 'armor_esp_enabled', False)),
            ("Distance ESP", self.toggle_distance_esp, False),
            ("Weapon ESP", self.toggle_weapon_esp, getattr(self.wall, 'weapon_esp_enabled', False)),
            ("Enemy Only", self.toggle_enemy_only, getattr(self.wall, 'enemy_only_enabled', False)),
            ("Team Only", self.toggle_team_only, getattr(self.wall, 'team_only_enabled', False)),
            ("Bomb ESP", self.toggle_bomb_esp, getattr(self.wall, 'bomb_esp_enabled', True)),
            ("Spectator List", self.toggle_spectator_list, getattr(self.wall, 'spectator_list_enabled', False)),
            ("Flash ESP", self.toggle_flash_esp, getattr(self.wall, 'flash_esp_enabled', False)),
            ("Scoped ESP", self.toggle_scope_esp, getattr(self.wall, 'scope_esp_enabled', False)),
            ("Radar Overlay", self.toggle_radar_overlay, getattr(self.wall, 'radar_overlay_enabled', True)),            
        ]

        def create_checkbox_container(cb_widget, extra_widgets=[]):
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 5, 0, 5)
            layout.setSpacing(8)
            layout.addWidget(cb_widget)
            for w in extra_widgets:
                layout.addWidget(w)
            layout.addStretch()
            container.setMaximumWidth(350)
            return container

        esp_widgets = []

        for label, func, state in esp_features:
            esp_key = label.lower().replace(" ", "_")
            cb = self.mk_cb(label, esp_key, conn=func, gui_key=f"esp_{esp_key}", initial_state=state)

            if label == "Bone ESP":
                size_label = QLabel("Size:")
                size_slider = QSlider(Qt.Horizontal)
                size_slider.setMinimum(1)
                size_slider.setMaximum(10)
                current_bone_size = getattr(self.wall, 'bone_esp_size', 3)
                size_slider.setValue(current_bone_size)
                size_slider.setFixedWidth(100)
                size_slider.valueChanged.connect(self.wall.SetBoneESPSize)

                shape_label = QLabel("Shape:")
                bone_shapes = ["Square", "Circle"]
                shape_combo = QComboBox()
                shape_combo.addItems(bone_shapes)
                current_bone_shape = getattr(self.wall, 'bone_esp_shape', "Square").capitalize()
                shape_combo.setCurrentIndex(bone_shapes.index(current_bone_shape) if current_bone_shape in bone_shapes else 0)
                shape_combo.currentTextChanged.connect(self.wall.SetBoneESPShape)

                self.gui_elements["bone_esp_size_slider"] = size_slider
                self.gui_elements["bone_esp_shape_combo"] = shape_combo

                container = create_checkbox_container(cb, [size_label, size_slider, shape_label, shape_combo])
                esp_widgets.append(container)

            elif label == "Head ESP":
                size_label = QLabel("Size:")
                size_slider = QSlider(Qt.Horizontal)
                size_slider.setMinimum(1)
                size_slider.setMaximum(10)
                current_head_size = getattr(self.wall, 'head_esp_size', 5)
                size_slider.setValue(current_head_size)
                size_slider.setFixedWidth(100)
                size_slider.valueChanged.connect(self.wall.SetHeadESPSize)

                shape_label = QLabel("Shape:")
                head_shapes = ["Square", "Circle"]
                shape_combo = QComboBox()
                shape_combo.addItems(head_shapes)
                current_head_shape = getattr(self.wall, 'head_esp_shape', "Square").capitalize()
                shape_combo.setCurrentIndex(head_shapes.index(current_head_shape) if current_head_shape in head_shapes else 0)
                shape_combo.currentTextChanged.connect(self.wall.SetHeadESPShape)

                self.gui_elements["head_esp_size_slider"] = size_slider
                self.gui_elements["head_esp_shape_combo"] = shape_combo

                container = create_checkbox_container(cb, [size_label, size_slider, shape_label, shape_combo])
                esp_widgets.append(container)

            else:
                container = create_checkbox_container(cb)
                esp_widgets.append(container)

        tabs.addTab(tab_widget(esp_widgets, two_columns=True), "ESP")

        trigger_widgets = [
            self.mk_cb("Triggerbot", "triggerbot_enabled", self.toggle_triggerbot, "triggerbot", target=self.shared_config),
            self.mk_cb("Shoot Teammates", "shoot_teammates", self.toggle_shoot_teammates, "shoot_teammates", target=self.shared_config),
            self.mk_cb("Always On (No Key Press)", "triggerbot_always_on", self.toggle_triggerbot_always_on, "triggerbot_always_on", target=self.shared_config),
        ]
        btn_set_key = QPushButton("Set Trigger Key")
        btn_set_key.clicked.connect(self.set_trigger_key)
        trigger_widgets.append(btn_set_key)

        cooldown_val = getattr(self.shared_config, 'triggerbot_cooldown', 0.8)
        cooldown_label = QLabel(f"Cooldown (s): {cooldown_val:.1f}")
        cooldown_slider = NoWheelSlider(Qt.Horizontal)
        cooldown_slider.setMinimum(1)
        cooldown_slider.setMaximum(50)
        cooldown_slider.setValue(int(cooldown_val * 10))

        self.gui_elements["cooldown_label"] = cooldown_label
        self.gui_elements["cooldown_slider"] = cooldown_slider

        def on_cooldown(val):
            secs = val / 10
            cooldown_label.setText(f"Cooldown (s): {secs:.1f}")
            self.shared_config.triggerbot_cooldown = secs
        cooldown_slider.valueChanged.connect(on_cooldown)
        trigger_widgets.extend([cooldown_label, cooldown_slider])
        tabs.addTab(tab_widget(trigger_widgets), "Triggerbot")

        # Combined setter for both font and weapon ESP colors
        def set_font_and_weapon_color(color):
            self.wall.SetESPFontColor(color)
            self.wall.SetWeaponESPColor(color)

        # Combined getter — choose one or fallback (e.g., font color or weapon color)
        def get_font_and_weapon_color():
            # Prefer font color if exists, otherwise weapon color, or fallback default
            return self.wall.esp_font_settings.get('color', getattr(self.wall, 'weapon_esp_color', '#0ff'))

        # Define color button config: label, setter, getter attribute
        color_buttons = [
            ("Box Background", self.wall.SetBoxBackgroundColor, lambda: getattr(self.wall, 'box_background_color', '#000')),
            ("Box Enemy", self.wall.SetBoxESPColor, lambda: getattr(self.wall, 'box_esp_color', '#f00')),
            ("Box Team", self.wall.SetTeamESPColor, lambda: getattr(self.wall, 'team_esp_color', '#00f')),
            ("Skeleton ESP", self.wall.SetSkeletonESPColor, lambda: getattr(self.wall, 'skeleton_esp_color', '#ffa500')),
            ("Bone ESP", self.wall.SetBoneESPColor, lambda: getattr(self.wall, 'bone_esp_color', '#ff0')),
            ("Line ESP", self.wall.SetLineESPColor, lambda: getattr(self.wall, 'line_color', '#fff')),
            ("Head ESP", self.wall.SetHeadESPColor, lambda: getattr(self.wall, 'head_esp_color', '#ff0')),
            ("Crosshair", self.wall.SetCrosshairColor, lambda: getattr(self.wall, 'crosshair_color', '#fff')),
            ("FOV Overlay", self.wall.SetFOVOverlayColor, lambda: getattr(self.shared_config, 'fov_overlay_color', 'green')),
            ("Font Colors", set_font_and_weapon_color, get_font_and_weapon_color),
        ]

        # Build buttons and store in gui_elements (unchanged)
        color_widgets = []
        for name, setter, get_color in color_buttons:
            color = get_color()
            btn = ColorButton(color, name, setter)
            btn.set_color(color)
            btn.setFixedSize(40, 20)
            color_widgets.append((name + " Color", btn))
            self.gui_elements[f"color_{name.lower().replace(' ', '_')}"] = btn

        # Layout and tabs unchanged
        color_layout = QGridLayout()
        color_layout.setHorizontalSpacing(50)
        for index, (label, widget) in enumerate(color_widgets):
            row = index // 2
            col = (index % 2) * 2
            label_widget = QLabel(label + ":")
            label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            color_layout.addWidget(label_widget, row, col)
            color_layout.addWidget(widget, row, col + 1, alignment=Qt.AlignLeft)

        color_tab = QWidget()
        color_tab.setLayout(color_layout)
        tabs.addTab(color_tab, "Colors")

        warn_style = "color: #e06666; font-weight: bold;"
        info_style = "color: #90EE90; font-size: 11px;"

        warn1 = QLabel("⚠️ Warning: Changing FOV writes directly to game memory.")
        warn2 = QLabel("⚠️ Warning: Enabling Glow writes directly to game memory.")
        warn3 = QLabel("⚠️ Warning: No Flash writes directly to game memory.")
        warn1.setStyleSheet(warn_style)
        warn2.setStyleSheet(warn_style)
        warn3.setStyleSheet(warn_style)

        fov_val = getattr(self.shared_config, 'game_fov', 90)
        lbl_fov = QLabel(f"FOV: {fov_val}")
        lbl_fov.setAlignment(Qt.AlignCenter)

        fov_slider = NoWheelSlider(Qt.Horizontal)
        fov_slider.setRange(50, 179)
        fov_slider.setValue(fov_val)

        self.gui_elements["fov_label"] = lbl_fov
        self.gui_elements["fov_slider"] = fov_slider

        def on_fov_change(value):
            lbl_fov.setText(f"FOV: {value}")
            try:
                ctrl = pw_module.r_int64(self.process, self.module + Offsets.dwLocalPlayerController)
                if ctrl:
                    pw_module.w_int(self.process, ctrl + Offsets.m_iDesiredFOV, value)
                self.shared_config.game_fov = value
            except Exception as e:
                print(f"Error setting FOV: {e}")

        fov_slider.valueChanged.connect(on_fov_change)

        monitor_sync_cb = self.mk_cb("ESP Monitor Sync", "monitor_sync_enabled", self.toggle_monitor_sync, "monitor_sync")
        monitor_sync_info = QLabel(f"📺 Detected refresh rate: {self.detected_refresh_rate} Hz")
        monitor_sync_info.setStyleSheet(info_style)

        # --- New Misc Tab Layout ---
        # Define checkboxes that will be used in the grid
        bhop_cb = self.mk_cb("Enable Bhop", "bhop_enabled", self.on_bhop_toggle, "bhop", target=self.shared_config)
        glow_cb = self.mk_cb("Enable Glow", "glow", None, "glow", target=self.shared_config)
        crosshair_cb = self.mk_cb("Crosshair", "crosshair_enabled", self.toggle_crosshair, "crosshair")
        noflash_cb = self.mk_cb("No Flash", 'noflash_enabled', self.toggle_noflash, "noflash")
        monitor_sync_cb = self.mk_cb("ESP Monitor Sync", "monitor_sync_enabled", self.toggle_monitor_sync, "monitor_sync")

        # Use a grid for checkboxes for a cleaner layout
        checkbox_layout = QGridLayout()
        checkbox_layout.setContentsMargins(0, 10, 0, 10)
        checkbox_layout.setSpacing(10)
        checkbox_layout.addWidget(bhop_cb, 0, 0)
        checkbox_layout.addWidget(glow_cb, 0, 1)
        checkbox_layout.addWidget(crosshair_cb, 1, 0)
        checkbox_layout.addWidget(noflash_cb, 1, 1)
        
        checkbox_container = QWidget()
        checkbox_container.setLayout(checkbox_layout)

        # Menu keybind setting widget
        menu_key_layout = QHBoxLayout()
        menu_key_layout.setContentsMargins(0, 0, 0, 0)
        menu_key_layout.setSpacing(10)
        menu_key_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        menu_key_label = QLabel("Menu Toggle Key:")
        menu_key_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        menu_key_layout.addWidget(menu_key_label)
        
        self.menu_key_display = QLabel(self.menu_toggle_key.upper())
        self.menu_key_display.setStyleSheet("color: #90EE90; font-size: 11px; font-weight: bold;")
        self.menu_key_display.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.menu_key_display.setMinimumWidth(20)
        menu_key_layout.addWidget(self.menu_key_display)
        
        btn_set_menu_key = QPushButton("Change Key")
        btn_set_menu_key.setFixedWidth(150)
        btn_set_menu_key.clicked.connect(self.set_menu_key)
        menu_key_layout.addWidget(btn_set_menu_key)
        
        menu_key_widget = QWidget()
        menu_key_widget.setLayout(menu_key_layout)
        menu_key_widget.setMinimumHeight(btn_set_menu_key.sizeHint().height() + 10)

        # Assemble the final list of widgets for the Misc tab
        misc_widgets = [
            warn1,
            warn2,
            warn3,
            lbl_fov,
            fov_slider,
            checkbox_container, # Grid of checkboxes
            monitor_sync_cb,      # Monitor sync checkbox
            monitor_sync_info,    # Monitor sync info label
            menu_key_widget       # Menu key settings
        ]

        tabs.addTab(tab_widget(misc_widgets, two_columns=True), "Misc")

        def slider_row(name, val, minv, maxv, setter, key=None):
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)

            lbl = QLabel(f"{name}: {val}")
            slider = NoWheelSlider(Qt.Horizontal)
            slider.setMinimum(minv)
            slider.setMaximum(maxv)
            slider.setValue(int(val))

            slider.valueChanged.connect(lambda v: (setter(v), lbl.setText(f"{name}: {v}")))
            lbl.setFixedWidth(150)
            layout.addWidget(lbl)
            layout.addWidget(slider)

            if key:
                self.gui_elements[f"{key}_slider"] = slider
                self.gui_elements[f"{key}_label"] = lbl

            return container

        # Existing checkboxes
        aimbot_enabled_cb = QCheckBox("Enable Aimbot")
        deathmatch_cb = QCheckBox("DeathMatch (shoot teammates)")
        fov_overlay_cb = QCheckBox("Show FOV Overlay")

        aimbot_widgets = [aimbot_enabled_cb, deathmatch_cb, fov_overlay_cb]

        aimbot_enabled_cb.setChecked(self.shared_config.enabled)
        aimbot_enabled_cb.stateChanged.connect(lambda s: setattr(self.shared_config, 'enabled', s == Qt.Checked))

        deathmatch_cb.setChecked(self.shared_config.DeathMatch)
        deathmatch_cb.stateChanged.connect(lambda s: setattr(self.shared_config, 'DeathMatch', s == Qt.Checked))

        self.gui_elements["aimbot_enabled"] = aimbot_enabled_cb
        self.gui_elements["deathmatch"] = deathmatch_cb
        self.gui_elements["fov_overlay"] = fov_overlay_cb

        def on_fov_overlay_toggle(state):
            if state == Qt.Checked:
                if not getattr(self, 'fov_overlay', None):
                    self.fov_overlay = WallHack.FOVOverlay(self.shared_config)
                self.fov_overlay.show()
                self.fov_overlay_enabled = True
            else:
                if getattr(self, 'fov_overlay', None):
                    self.fov_overlay.hide()
                    self.fov_overlay_enabled = False

        fov_overlay_cb.setChecked(self.fov_overlay_enabled)
        fov_overlay_cb.stateChanged.connect(on_fov_overlay_toggle)

        # Moved nearest bone checkbox here with the other checkboxes
        nearest_bone_cb = QCheckBox("Aim at Nearest Bone (Head/Chest)")
        nearest_bone_cb.setChecked(self.shared_config.closest_to_crosshair)
        nearest_bone_cb.stateChanged.connect(lambda s: setattr(self.shared_config, 'closest_to_crosshair', s == Qt.Checked))
        aimbot_widgets.append(nearest_bone_cb)
        self.gui_elements["closest_to_crosshair"] = nearest_bone_cb

        # Other feature checkboxes
        learning_checkbox = QCheckBox("Enable Aimbot Learning")
        learning_checkbox.setChecked(getattr(self.shared_config, 'enable_learning', True))
        learning_checkbox.stateChanged.connect(lambda s: setattr(self.shared_config, 'enable_learning', s == Qt.Checked))
        aimbot_widgets.append(learning_checkbox)
        self.gui_elements["learning"] = learning_checkbox

        velocity_checkbox = QCheckBox("Enable Velocity Prediction")
        velocity_checkbox.setChecked(getattr(self.shared_config, 'enable_velocity_prediction', True))
        velocity_checkbox.stateChanged.connect(lambda s: setattr(self.shared_config, 'enable_velocity_prediction', s == Qt.Checked))
        aimbot_widgets.append(velocity_checkbox)
        self.gui_elements["velocity_prediction"] = velocity_checkbox

        rcs_enabled_cb = QCheckBox("Enable RCS (Recoil Control System)")
        rcs_enabled_cb.setChecked(getattr(self.shared_config, 'rcs_enabled', True))
        rcs_enabled_cb.stateChanged.connect(lambda s: setattr(self.shared_config, 'rcs_enabled', s == Qt.Checked))
        aimbot_widgets.append(rcs_enabled_cb)
        self.gui_elements["rcs_enabled"] = rcs_enabled_cb

        # Sliders
        sliders = [
            ("Aimbot FOV", self.shared_config.FOV, 1, 30, lambda v: setattr(self.shared_config, 'FOV', float(v)), "aimbot_fov"),
            ("Aimbot Smooth Base", int(self.shared_config.smooth_base * 100), 5, 100, lambda v: setattr(self.shared_config, 'smooth_base', v / 100), "smooth_base"),
            ("Aimbot Smooth Var", int(self.shared_config.smooth_var * 100), 1, 50, lambda v: setattr(self.shared_config, 'smooth_var', v / 100), "smooth_var"),
            ("RCS Smooth Base", int(self.shared_config.rcs_smooth_base * 100), 5, 100, lambda v: setattr(self.shared_config, 'rcs_smooth_base', v / 100), "rcs_smooth_base"),
            ("RCS Smooth Var", int(self.shared_config.rcs_smooth_var * 100), 1, 50, lambda v: setattr(self.shared_config, 'rcs_smooth_var', v / 100), "rcs_smooth_var"),
            ("RCS Scale", int(self.shared_config.rcs_scale * 10), 10, 50, lambda v: setattr(self.shared_config, 'rcs_scale', v / 10), "rcs_scale"),
            ("Stabilize Shots", self.shared_config.stabilize_shots, 1, 10, lambda v: setattr(self.shared_config, 'stabilize_shots', v), "stabilize_shots"),
            ("Target Switch Delay", int(self.shared_config.target_switch_delay * 100), 0, 200, lambda v: setattr(self.shared_config, 'target_switch_delay', v / 100), "target_switch_delay"),
            ("Aim Start Delay", int(self.shared_config.aim_start_delay * 100), 0, 100, lambda v: setattr(self.shared_config, 'aim_start_delay', v / 100), "aim_start_delay"),
            ("Downward Offset", self.shared_config.downward_offset, 0, 200, lambda v: setattr(self.shared_config, 'downward_offset', v), "downward_offset"),
        ]

        
        aimbot_widgets.extend(slider_row(*s) for s in sliders)

        # Bone selection dropdown (after all checkboxes)
        bone_container = QWidget()
        bone_layout = QHBoxLayout(bone_container)
        bone_layout.setContentsMargins(0, 0, 0, 0)
        bone_layout.setSpacing(10)
        bone_label = QLabel("Target Bone:")
        bone_label.setFixedWidth(150)
        bone_combo = QComboBox()
        bones = ["head", "chest"]
        bone_combo.addItems(bones)
        current_bone = getattr(self.shared_config, 'target_bone_name', 'head')
        bone_combo.setCurrentIndex(bones.index(current_bone) if current_bone in bones else 0)

        def on_bone_change(idx):
            bone = bones[idx]
            self.shared_config.target_bone_name = bone
            self.shared_config.target_bone_index = 6 if bone == "head" else 18

        bone_combo.currentIndexChanged.connect(on_bone_change)
        bone_layout.addWidget(bone_label)
        bone_layout.addWidget(bone_combo)
        aimbot_widgets.append(bone_container)
        self.gui_elements["bone_combo"] = bone_combo

        tabs.addTab(tab_widget(aimbot_widgets, two_columns=True), "Aimbot")

        config_widgets = []
        config_dropdown = QComboBox()
        config_name_input = QLineEdit()
        config_name_input.setPlaceholderText("Enter new config name")
        status_label = QLabel("")
        btn_save = QPushButton("💾 Save")
        btn_load = QPushButton("📂 Load")
        btn_delete = QPushButton("🗑️ Delete")
        btn_auto_save = QPushButton("💾 Save to General")
        btn_set_autoload = QPushButton("⚡ Set as General")
        btn_reset_defaults = QPushButton("🔄 Reset to Defaults")
        btn_reset_defaults.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 5px;")
        btn_reset_defaults.setToolTip("Reset all settings to default values")
        def ensure_config_dir():
            path = "configs"
            os.makedirs(path, exist_ok=True)
            return path
        def config_path(name):
            return os.path.join(ensure_config_dir(), f"{name}.json")
        def refresh_config_list():
            config_dropdown.clear()
            try:
                files = [f[:-5] for f in os.listdir(ensure_config_dir()) if f.endswith(".json")]
                config_dropdown.addItems(files if files else ["No configs available"])
                if "general" in files:
                    config_dropdown.setCurrentText("general")
            except Exception as e:
                config_dropdown.addItems(["No configs available"])
                print("Error refreshing configs:", e)
        def auto_save_config():
            try:
                write_json(config_path("general"), self.get_current_config_data())
                status_label.setText("🔄 Saved to general config")
                refresh_config_list()
            except Exception as e:
                status_label.setText(f"❌ Auto-save failed: {e}")
                print("Auto-save error:", e)
        def set_autoload():
            name = config_dropdown.currentText()
            if not name or name == "No configs available":
                return status_label.setText("❌ No config selected.")
            try:
                shutil.copy2(config_path(name), config_path("general"))
                status_label.setText(f"⚡ Set '{name}' as general auto-load config")
                refresh_config_list()
            except Exception as e:
                status_label.setText(f"❌ Set autoload failed: {e}")
                print("Set autoload error:", e)
        def reset_defaults():
            try:
                print("[*] Resetting all settings to defaults...")
                default_settings = {
                    "aimbot": {
                        "enabled": False,
                        "FOV": 4.0,
                        "smooth_base": 0.12,
                        "smooth_var": 0.0,
                        "rcs_smooth_base": 0.12,
                        "rcs_smooth_var": 0.03,
                        "rcs_scale": 2.6,
                        "stabilize_shots": 3,
                        "target_switch_delay": 0.2,
                        "aim_start_delay": 0.06,
                        "downward_offset": 62,
                        "target_bone_name": 'head',
                        "target_bone_index": 6,
                        "enable_learning": True,
                        "enable_velocity_prediction": False,
                        "DeathMatch": False,
                        "triggerbot_enabled": False,
                        "triggerbot_cooldown": 0.8,
                        "shoot_teammates": False,
                    },
                    "esp": {
                        "enabled": True,
                        "watermark_enabled": True,
                        "crosshair_enabled": False,
                        "enemy_only_enabled": False,
                        "team_only_enabled": False,
                        "distance_esp_enabled": False,
                        "box_esp_enabled": False,
                        "healthbar_enabled": False,
                        "health_esp_enabled": False,
                        "name_esp_enabled": False,
                        "line_esp_enabled": False,
                        "head_esp_enabled": False,
                        "skeletonesp": False,
                        "bone_esp_enabled": False,
                        "head_esp_shape": 'square',
                        "head_esp_size": 10,
                        "bone_esp_shape": 'square',
                        "bone_esp_size": 5,
                        "esp_font_settings": {"size": 10, "color": "cyan"},
                        "team_esp_color": 'blue',
                        "box_esp_color": 'red',
                        "head_esp_color": 'yellow',
                        "line_color": 'white',
                        "skeleton_esp_color": 'orange',
                        "bone_esp_color": 'yellow',
                        "box_background_color": 'black',
                        "crosshair_color": 'white',
                    },
                    "misc": {
                        "bhop_enabled": False,
                        "glow": False,
                        "game_fov": 90,
                        "monitor_sync_enabled": True,
                    },
                    "overlay": {
                        "fov_overlay_enabled": False,
                    }
                }

                for k, v in default_settings["aimbot"].items():
                    setattr(self.shared_config, k, v)
                for k, v in default_settings["misc"].items():
                    setattr(self.shared_config, k, v)

                for k, v in default_settings["esp"].items():
                    setattr(self.wall, k, v)
                self.monitor_sync_enabled = True
                self.fps = self.detected_refresh_rate
                self.triggerbot = None
                if getattr(self, 'fov_overlay', None):
                    self.fov_overlay.hide()
                self.fov_overlay_enabled = False
                self.update_gui_from_config()

                gui = self.gui_elements
                if "fov_slider" in gui: gui["fov_slider"].setValue(90)
                if "fov_label" in gui: gui["fov_label"].setText("FOV: 90")
                if "cooldown_slider" in gui: gui["cooldown_slider"].setValue(8)
                if "cooldown_label" in gui: gui["cooldown_label"].setText("Cooldown (s): 0.8")
                if "bone_combo" in gui: gui["bone_combo"].setCurrentIndex(0)
                QApplication.processEvents()
                status_label.setText("🔄 All settings reset to defaults")
                print("[*] Reset complete")
            except Exception as e:
                status_label.setText(f"❌ Reset failed: {e}")
                print("Reset error:", e)
        def save_config():
            name = config_name_input.text().strip()
            if not name:
                return status_label.setText("❌ Please enter a config name.")
            try:
                write_json(config_path(name), self.get_current_config_data())
                config_name_input.clear()
                refresh_config_list()
                status_label.setText(f"✅ Saved: {name}")
            except Exception as e:
                status_label.setText(f"❌ Save failed: {e}")
                print("Save error:", e)
        def load_config():
            name = config_dropdown.currentText()
            if not name or name == "No configs available":
                return status_label.setText(" No config selected.")
            try:
                data = read_json(config_path(name))
                aim_data = data.get("aimbot", {})
                esp_data = data.get("esp", {})

                # Load aimbot settings
                for key, val in aim_data.items():
                    if hasattr(self.shared_config, key):
                        setattr(self.shared_config, key, val)
                    elif key == "bone": setattr(self.shared_config, "target_bone_name", val)
                    elif key == "learning": setattr(self.shared_config, "enable_learning", val)
                    elif key == "velocity_prediction": setattr(self.shared_config, "enable_velocity_prediction", val)
                    elif key == "deathmatch": setattr(self.shared_config, "DeathMatch", val)
                    elif hasattr(self, key):
                        setattr(self, key, val)

                # Load ESP settings
                for key, val in esp_data.items():
                    if hasattr(self.wall, key):
                        setattr(self.wall, key, val)
                    elif hasattr(self, key):
                        setattr(self, key, val)

                # Handle menu toggle key
                if "menu_toggle_key" in aim_data:
                    self.menu_toggle_key = aim_data["menu_toggle_key"]

                # Handle FOV overlay
                self.fov_overlay_enabled = esp_data.get("fov_overlay_enabled", False)
                if self.fov_overlay_enabled:
                    if not getattr(self, 'fov_overlay', None):
                        self.fov_overlay = WallHack.FOVOverlay(self.shared_config)
                    self.fov_overlay.show()
                elif getattr(self, 'fov_overlay', None):
                    self.fov_overlay.hide()

                # Handle TriggerBot
                if aim_data.get("triggerbot_enabled", False):
                    # Get trigger key from config, ensure it's not the same as menu toggle key
                    trigger_key = aim_data.get("trigger_key", "shift")
                    if trigger_key == self.menu_toggle_key:
                        # Use an alternative key
                        trigger_key = "ctrl" if self.menu_toggle_key != "ctrl" else "shift"
                        print(f"[!] Warning: Trigger key was same as menu key. Changed to {trigger_key}")
                    
                    self.trigger_key = trigger_key
                    self.triggerbot = TriggerBot(
                        triggerKey=self.trigger_key,
                        shootTeammates=self.shared_config.shoot_teammates,
                        shared_config=self.shared_config
                    )
                else:
                    self.triggerbot = None

                self.update_gui_from_config()
                status_label.setText(f" Loaded: {name}")
            except Exception as e:
                status_label.setText(f" Load failed: {e}")
                print("Load error:", e)
        def delete_config():
            name = config_dropdown.currentText()
            if not name or name == "No configs available":
                status_label.setText("❌ No config selected.")
                return
            filepath = os.path.join(ensure_config_dir(), f"{name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                status_label.setText(f"🗑️ Deleted: {name}")
                refresh_config_list()
            else:
                status_label.setText("❌ Config not found.")

        btn_save.clicked.connect(save_config)
        btn_load.clicked.connect(load_config)
        btn_delete.clicked.connect(delete_config)
        btn_auto_save.clicked.connect(auto_save_config)
        btn_set_autoload.clicked.connect(set_autoload)
        btn_reset_defaults.clicked.connect(reset_defaults)

        form_group = QGroupBox("🎛️ Config Management")
        form_layout = QFormLayout()
        form_layout.addRow("📁 Available Configs:", config_dropdown)
        form_layout.addRow("✏️ New Config Name:", config_name_input)

        button_row1 = QWidget()
        button_layout1 = QHBoxLayout(button_row1)
        button_layout1.addWidget(btn_save)
        button_layout1.addWidget(btn_load)
        button_layout1.addWidget(btn_delete)
        button_layout1.setContentsMargins(0, 0, 0, 0)

        button_row2 = QWidget()
        button_layout2 = QHBoxLayout(button_row2)
        button_layout2.addWidget(btn_auto_save)
        button_layout2.addWidget(btn_set_autoload)
        button_layout2.addWidget(btn_reset_defaults)
        button_layout2.setContentsMargins(0, 0, 0, 0)
        form_layout.addRow(button_row1)
        form_layout.addRow(button_row2)
        form_layout.addRow("Status:", status_label)
        form_group.setLayout(form_layout)
        config_widgets.append(form_group)

        refresh_config_list()
        tabs.addTab(tab_widget(config_widgets), "Configs")
        
        # Create Account tab
        account_widgets = []
        
        # Account information group
        account_group = QGroupBox("👤 Account Information")
        account_layout = QFormLayout()
        
        # Email/Username field
        email_label = QLabel("Email/Username:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email or username")
        self.email_input.setText("user@example.com")  # Default value
        account_layout.addRow(email_label, self.email_input)
        
        # Premium status indicator
        premium_label = QLabel("Premium Status:")
        self.premium_status = QLabel("✅ Premium")
        self.premium_status.setStyleSheet("color: #90EE90; font-weight: bold;")
        account_layout.addRow(premium_label, self.premium_status)
        
        # Subscription expiry
        expiry_label = QLabel("Subscription Expires:")
        self.expiry_date = QLabel("December 31, 2023")
        account_layout.addRow(expiry_label, self.expiry_date)
        
        # Load account info if available
        self.load_account_info()
        
        # Hardware ID
        hwid_label = QLabel("Hardware ID:")
        self.hwid_value = QLabel("XXXX-XXXX-XXXX-XXXX")
        self.hwid_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.hwid_value.setStyleSheet("font-family: monospace; background-color: rgba(30, 30, 45, 230); padding: 3px; border-radius: 3px;")
        account_layout.addRow(hwid_label, self.hwid_value)
        
        # Save button
        save_btn = QPushButton("Save Account Info")
        save_btn.clicked.connect(self.save_account_info)
        account_layout.addRow("", save_btn)
        
        account_group.setLayout(account_layout)
        account_widgets.append(account_group)
        
        # Support/Contact group
        support_group = QGroupBox("🔧 Support")
        support_layout = QVBoxLayout()
        
        support_info = QLabel("Need help? Contact our support team:")
        support_email = QLabel("support@vectorstrike.com")
        support_email.setStyleSheet("color: #7a8cc7; font-weight: bold;")
        support_discord = QLabel("Join our Discord: discord.gg/vectorstrike")
        
        support_layout.addWidget(support_info)
        support_layout.addWidget(support_email)
        support_layout.addWidget(support_discord)
        support_group.setLayout(support_layout)
        account_widgets.append(support_group)
        
        tabs.addTab(tab_widget(account_widgets), "Account")
        main_layout.addWidget(tabs)
        self.window.setLayout(main_layout)
        self.window.show()

        self.load_autoconfig()
        self.load_saved_logo()

    def get_current_config_data(self):
        """Generate current config data structure"""
        return {
            "aimbot": {
                "enabled": getattr(self.shared_config, 'enabled', False),
                "FOV": getattr(self.shared_config, 'FOV', 4.0),
                "smooth_base": getattr(self.shared_config, 'smooth_base', 0.12),
                "smooth_var": getattr(self.shared_config, 'smooth_var', 0.0),
                "rcs_enabled": getattr(self.shared_config, 'rcs_enabled', True),
                "rcs_smooth_base": getattr(self.shared_config, 'rcs_smooth_base', 0.12),
                "rcs_smooth_var": getattr(self.shared_config, 'rcs_smooth_var', 0.03),
                "rcs_scale": getattr(self.shared_config, 'rcs_scale', 2.6),
                "stabilize_shots": getattr(self.shared_config, 'stabilize_shots', 3),
                "target_switch_delay": getattr(self.shared_config, 'target_switch_delay', 0.2),
                "aim_start_delay": getattr(self.shared_config, 'aim_start_delay', 0.06),
                "downward_offset": getattr(self.shared_config, 'downward_offset', 62),
                "target_bone_name": getattr(self.shared_config, 'target_bone_name', 'head'),
                "enable_learning": getattr(self.shared_config, 'enable_learning', True),
                "enable_velocity_prediction": getattr(self.shared_config, 'enable_velocity_prediction', False),
                "DeathMatch": getattr(self.shared_config, 'DeathMatch', False),
                "triggerbot_enabled": getattr(self.shared_config, 'triggerbot_enabled', False),
                "triggerbot_cooldown": getattr(self.shared_config, 'triggerbot_cooldown', 0.8),
                "trigger_key": getattr(self, 'trigger_key', None),
                "shoot_teammates": getattr(self.shared_config, 'shoot_teammates', False),
                "bhop_enabled": getattr(self.shared_config, 'bhop_enabled', False),
                "glow": getattr(self.shared_config, 'glow', False),
                "game_fov": getattr(self.shared_config, 'game_fov', 90),
                "monitor_sync_enabled": getattr(self.shared_config, 'monitor_sync_enabled', True),
                "menu_toggle_key": getattr(self, 'menu_toggle_key', 'insert'),
                "noflash_enabled": getattr(self.shared_config, 'noflash_enabled', False),
                "triggerbot_always_on": getattr(self.shared_config, 'triggerbot_always_on', False),
            },
            "esp": {
                "enabled": getattr(self.wall, 'enabled', False),
                "watermark_enabled": getattr(self.wall, 'watermark_enabled', False),
                "crosshair_enabled": getattr(self.wall, 'crosshair_enabled', False),
                "enemy_only_enabled": getattr(self.wall, 'enemy_only_enabled', False),
                "team_only_enabled": getattr(self.wall, 'team_only_enabled', False),
                "distance_esp_enabled": getattr(self.wall, 'distance_esp_enabled', False),
                "box_esp_enabled": getattr(self.wall, 'box_esp_enabled', False),
                "healthbar_enabled": getattr(self.wall, 'healthbar_enabled', False),
                "health_esp_enabled": getattr(self.wall, 'health_esp_enabled', False),
                "name_esp_enabled": getattr(self.wall, 'name_esp_enabled', False),
                "line_esp_enabled": getattr(self.wall, 'line_esp_enabled', False),
                "head_esp_enabled": getattr(self.wall, 'head_esp_enabled', False),
                "skeletonesp": getattr(self.wall, 'skeletonesp', False),
                "bone_esp_enabled": getattr(self.wall, 'bone_esp_enabled', False),
                "armoresp_enabled": getattr(self.wall, 'armoresp_enabled', False),
                "armorbar_enabled": getattr(self.wall, 'armorbar_enabled', False),
                "spectator_list_enabled": getattr(self.wall, 'spectator_list_enabled', False),
                "flash_esp_enabled": getattr(self.wall, 'flash_esp_enabled', False),
                "scoped_esp_enabled": getattr(self.wall, 'scoped_esp_enabled', False),
                "head_esp_shape": getattr(self.wall, 'head_esp_shape', 'Square'),
                "head_esp_size": getattr(self.wall, 'head_esp_size', 5),
                "bone_esp_shape": getattr(self.wall, 'bone_esp_shape', 'Square'),
                "bone_esp_size": getattr(self.wall, 'bone_esp_size', 3),
                "esp_font_settings": getattr(self.wall, 'esp_font_settings', {}),
                "team_esp_color": getattr(self.wall, 'team_esp_color', 'green'),
                "box_esp_color": getattr(self.wall, 'box_esp_color', 'red'),
                "head_esp_color": getattr(self.wall, 'head_esp_color', 'red'),
                "line_color": getattr(self.wall, 'line_color', 'red'),
                "skeleton_esp_color": getattr(self.wall, 'skeleton_esp_color', 'white'),
                "bone_esp_color": getattr(self.wall, 'bone_esp_color', 'red'),
                "box_background_color": getattr(self.wall, 'box_background_color', 'black'),
                "crosshair_color": getattr(self.wall, 'crosshair_color', 'red'),
                "weapon_esp_enabled": getattr(self.wall, 'weapon_esp_enabled', False),
                "weapon_esp_color": getattr(self.wall, 'weapon_esp_color', 'cyan'),
                "bomb_esp_enabled": getattr(self.wall, 'bomb_esp_enabled', False),
                "fov_overlay_enabled": getattr(self, 'fov_overlay_enabled', False),
                "fov_overlay_color": getattr(self, 'fov_overlay_color', 'green'),
            },
        }
    def load_autoconfig(self):
        """Load the general.json config if it exists"""
        autoconfig_path = os.path.join("configs", "general.json")
        if os.path.exists(autoconfig_path):
            try:
                data = read_json(autoconfig_path)
                aim_data = data.get("aimbot", {})
                esp_data = data.get("esp", {})

                # Load aimbot settings
                for key, val in aim_data.items():
                    if hasattr(self.shared_config, key):
                        setattr(self.shared_config, key, val)
                    elif key == "bone": setattr(self.shared_config, "target_bone_name", val)
                    elif key == "learning": setattr(self.shared_config, "enable_learning", val)
                    elif key == "velocity_prediction": setattr(self.shared_config, "enable_velocity_prediction", val)
                    elif key == "deathmatch": setattr(self.shared_config, "DeathMatch", val)
                    elif hasattr(self, key):
                        setattr(self, key, val)

                # Load ESP settings
                for key, val in esp_data.items():
                    if hasattr(self.wall, key):
                        setattr(self.wall, key, val)
                    elif hasattr(self, key):
                        setattr(self, key, val)

                # Handle menu toggle key
                if "menu_toggle_key" in aim_data:
                    self.menu_toggle_key = aim_data["menu_toggle_key"]

                # Handle FOV overlay
                self.fov_overlay_enabled = esp_data.get("fov_overlay_enabled", False)
                if self.fov_overlay_enabled:
                    if not getattr(self, 'fov_overlay', None):
                        self.fov_overlay = WallHack.FOVOverlay(self.shared_config)
                    self.fov_overlay.show()
                elif getattr(self, 'fov_overlay', None):
                    self.fov_overlay.hide()

                # Handle TriggerBot
                if aim_data.get("triggerbot_enabled", False):
                    # Get trigger key from config, ensure it's not the same as menu toggle key
                    trigger_key = aim_data.get("trigger_key", "shift")
                    if trigger_key == self.menu_toggle_key:
                        # Use an alternative key
                        trigger_key = "ctrl" if self.menu_toggle_key != "ctrl" else "shift"
                        print(f"[!] Warning: Trigger key was same as menu key. Changed to {trigger_key}")
                    
                    self.trigger_key = trigger_key
                    self.triggerbot = TriggerBot(
                        triggerKey=self.trigger_key,
                        shootTeammates=self.shared_config.shoot_teammates,
                        shared_config=self.shared_config
                    )
                else:
                    self.triggerbot = None

                self.update_gui_from_config()
                print("[*] Auto-loaded general.json config")
            except Exception as e:
                print(f"Failed to auto-load config: {e}")
    def update_gui_from_config(self):
        """Simple function to update GUI elements from current config"""

        updates = {
            "triggerbot": getattr(self.shared_config, 'triggerbot_enabled', False),
            "shoot_teammates": getattr(self.shared_config, 'shoot_teammates', False),
            "bhop": getattr(self.shared_config, 'bhop_enabled', False),
            "glow": getattr(self.shared_config, 'glow', False),
            "crosshair": getattr(self.wall, 'crosshair_enabled', False),
            "aimbot_enabled": getattr(self.shared_config, 'enabled', False),
            "deathmatch": getattr(self.shared_config, 'DeathMatch', False),
            "learning": getattr(self.shared_config, 'enable_learning', True),
            "velocity_prediction": getattr(self.shared_config, 'enable_velocity_prediction', False),
            "fov_overlay": getattr(self, 'fov_overlay_enabled', False),
            "monitor_sync": getattr(self.shared_config, 'monitor_sync_enabled', True)
        }
        for key, value in updates.items():
            if key in self.gui_elements:
                self.gui_elements[key].setChecked(value)

        esp_updates = {
            "esp_watermark": getattr(self.wall, 'watermark_enabled', False),
            "esp_box_esp": getattr(self.wall, 'box_esp_enabled', False),
            "esp_line_esp": getattr(self.wall, 'line_esp_enabled', False),
            "esp_skeleton_esp": getattr(self.wall, 'skeletonesp', False),
            "esp_bone_esp": getattr(self.wall, 'bone_esp_enabled', False),
            "esp_head_esp": getattr(self.wall, 'head_esp_enabled', False),
            "esp_name_esp": getattr(self.wall, 'name_esp_enabled', False),
            "esp_health_esp": getattr(self.wall, 'health_esp_enabled', False),
            "esp_health_bar": getattr(self.wall, 'healthbar_enabled', False),
            "esp_distance_esp": getattr(self.wall, 'distance_esp_enabled', False),
            "esp_enemy_only": getattr(self.wall, 'enemy_only_enabled', False),
            "esp_team_only": getattr(self.wall, 'team_only_enabled', False)
        }
        for key, value in esp_updates.items():
            if key in self.gui_elements:
                self.gui_elements[key].setChecked(value)

        aimbot_slider_updates = {
            "aimbot_fov": (getattr(self.shared_config, 'FOV', 4.0), "Aimbot FOV"),
            "smooth_base": (int(getattr(self.shared_config, 'smooth_base', 0.12) * 100), "Aimbot Smooth Base"),
            "smooth_var": (int(getattr(self.shared_config, 'smooth_var', 0.0) * 100), "Aimbot Smooth Var"),
            "rcs_smooth_base": (int(getattr(self.shared_config, 'rcs_smooth_base', 0.12) * 100), "RCS Smooth Base"),
            "rcs_smooth_var": (int(getattr(self.shared_config, 'rcs_smooth_var', 0.03) * 100), "RCS Smooth Var"),
            "rcs_scale": (int(getattr(self.shared_config, 'rcs_scale', 2.6) * 10), "RCS Scale"),
            "stabilize_shots": (getattr(self.shared_config, 'stabilize_shots', 3), "Stabilize Shots"),
            "target_switch_delay": (int(getattr(self.shared_config, 'target_switch_delay', 0.2) * 100), "Target Switch Delay"),
            "aim_start_delay": (int(getattr(self.shared_config, 'aim_start_delay', 0.06) * 100), "Aim Start Delay"),
            "downward_offset": (getattr(self.shared_config, 'downward_offset', 62), "Downward Offset")
        }
        for key, (value, label) in aimbot_slider_updates.items():
            if f"{key}_slider" in self.gui_elements:
                self.gui_elements[f"{key}_slider"].setValue(int(value))
            if f"{key}_label" in self.gui_elements:
                self.gui_elements[f"{key}_label"].setText(f"{label}: {int(value)}")

        if "cooldown_slider" in self.gui_elements:
            cooldown_val = getattr(self.shared_config, 'triggerbot_cooldown', 0.8)
            self.gui_elements["cooldown_slider"].setValue(int(cooldown_val * 10))
            if "cooldown_label" in self.gui_elements:
                self.gui_elements["cooldown_label"].setText(f"Cooldown (s): {cooldown_val:.1f}")
        if "fov_slider" in self.gui_elements:
            fov_val = getattr(self.shared_config, 'game_fov', 90)
            self.gui_elements["fov_slider"].setValue(fov_val)
            if "fov_label" in self.gui_elements:
                self.gui_elements["fov_label"].setText(f"FOV: {fov_val}")

        if "bone_combo" in self.gui_elements:
            bone_name = getattr(self.shared_config, 'target_bone_name', 'head')
            bones = ["head", "chest"]
            if bone_name in bones:
                self.gui_elements["bone_combo"].setCurrentIndex(bones.index(bone_name))

        if "bone_esp_size_slider" in self.gui_elements:
            bone_size = getattr(self.wall, 'bone_esp_size', 5)
            self.gui_elements["bone_esp_size_slider"].setValue(bone_size)
        if "bone_esp_shape_combo" in self.gui_elements:
            bone_shape = getattr(self.wall, 'bone_esp_shape', 'square').capitalize()
            bone_shapes = ["Square", "Circle"]
            if bone_shape in bone_shapes:
                self.gui_elements["bone_esp_shape_combo"].setCurrentIndex(bone_shapes.index(bone_shape))
        if "head_esp_size_slider" in self.gui_elements:
            head_size = getattr(self.wall, 'head_esp_size', 10)
            self.gui_elements["head_esp_size_slider"].setValue(head_size)
        if "head_esp_shape_combo" in self.gui_elements:
            head_shape = getattr(self.wall, 'head_esp_shape', 'square').capitalize()
            head_shapes = ["Square", "Circle"]
            if head_shape in head_shapes:
                self.gui_elements["head_esp_shape_combo"].setCurrentIndex(head_shapes.index(head_shape))
        
        # Update color buttons
        color_mappings = {
            "color_box_background": getattr(self.wall, 'box_background_color', 'black'),
            "color_box_enemy": getattr(self.wall, 'box_esp_color', 'red'),
            "color_box_team": getattr(self.wall, 'team_esp_color', 'blue'),
            "color_skeleton_esp": getattr(self.wall, 'skeleton_esp_color', 'orange'),
            "color_font_color": getattr(self.wall, 'esp_font_settings', {}).get('color', 'cyan'),
            "color_bone_esp": getattr(self.wall, 'bone_esp_color', 'yellow'),
            "color_line_esp": getattr(self.wall, 'line_color', 'white'),
            "color_head_esp": getattr(self.wall, 'head_esp_color', 'yellow'),
            "color_crosshair": getattr(self.wall, 'crosshair_color', 'white')
        }
        
        for key, color in color_mappings.items():
            if key in self.gui_elements:
                self.gui_elements[key].set_color(color)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.window.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def upload_logo(self, event):
        """Handle logo image upload when logo is clicked"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.window,
                "Select Logo Image",
                "",
                "Image Files (*.png *.jpg *.jpeg *.bmp *.svg)"
            )
            
            if file_path:
                # Load the image
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # Scale the image to fit the label while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.logo_label.setPixmap(scaled_pixmap)
                    self.logo_label.setText("")  # Clear text when image is set
                    
                    # Save the logo path to config
                    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
                    os.makedirs(config_dir, exist_ok=True)
                    
                    # Save logo path to a separate config file
                    logo_config = os.path.join(config_dir, "logo_config.json")
                    with open(logo_config, "w") as f:
                        json.dump({"logo_path": file_path}, f, indent=4)
                    
                    print(f"[*] Logo updated and path saved to config")
                else:
                    print(f"[!] Failed to load image: {file_path}")
        except Exception as e:
            print(f"[!] Error uploading logo: {e}")
            
    def load_saved_logo(self):
        """Load the logo from /photos/logo.png or from config if it exists"""
        try:
            # First try to load from the default photos directory
            photos_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")
            default_logo_path = os.path.join(photos_dir, "logo.png")
            
            # Create photos directory if it doesn't exist
            if not os.path.exists(photos_dir):
                os.makedirs(photos_dir, exist_ok=True)
                print(f"[*] Created photos directory: {photos_dir}")
            
            # Create default logo file if it doesn't exist
            if not os.path.exists(default_logo_path):
                self.create_default_logo(default_logo_path)
                print(f"[*] Created default logo at: {default_logo_path}")
            
            # If default logo exists, use it
            if os.path.exists(default_logo_path):
                pixmap = QPixmap(default_logo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.logo_label.setPixmap(scaled_pixmap)
                    self.logo_label.setText("")  # Clear text when image is set
                    print(f"[*] Loaded logo from: {default_logo_path}")
                    return
            
            # If default logo doesn't exist or couldn't be loaded, try from config
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
            logo_config = os.path.join(config_dir, "logo_config.json")
            
            if os.path.exists(logo_config):
                with open(logo_config, "r") as f:
                    config = json.load(f)
                    
                logo_path = config.get("logo_path")
                if logo_path and os.path.exists(logo_path):
                    pixmap = QPixmap(logo_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.logo_label.setPixmap(scaled_pixmap)
                        self.logo_label.setText("")  # Clear text when image is set
                        print(f"[*] Loaded logo from config: {logo_path}")
        except Exception as e:
            print(f"[!] Error loading logo: {e}")
    
    def create_default_logo(self, logo_path):
        """Create a default SVG logo file"""
        try:
            # Create a simple SVG logo with VS text
            svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
  <rect width="40" height="40" rx="5" fill="#1e1e2d"/>
  <text x="20" y="25" font-family="Arial" font-size="18" font-weight="bold" fill="#7a8cc7" text-anchor="middle">VS</text>
  <path d="M5,35 L35,5" stroke="#4e8cff" stroke-width="1.5" opacity="0.3"/>
  <path d="M5,5 L35,35" stroke="#4e8cff" stroke-width="1.5" opacity="0.3"/>
</svg>'''
            
            # Write the SVG content to the file
            with open(logo_path, 'w') as f:
                f.write(svg_content)
                
            return True
        except Exception as e:
            print(f"[!] Error creating default logo: {e}")
            return False
    
    def quit_vectorstrike(self):
        print("[*] Quit button pressed. Terminating...")

        # Save config
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.argv[0])))
        config_dir = os.path.join(base_dir, "configs")
        filepath = os.path.join(config_dir, "general.json")

        try:
            os.makedirs(config_dir, exist_ok=True)
            config_data = self.get_current_config_data()
            with open(filepath, "w") as f:
                json.dump(config_data, f, indent=4)
            print(f"[*] Saved config to: {filepath}")
        except Exception as e:
            print(f"[!] Failed to save config: {e}")

        # Stop keyboard listener
        try:
            if getattr(self, 'keyboard_listener', None):
                self.keyboard_listener.stop()
                print("[*] Keyboard listener stopped")
        except Exception as e:
            print(f"[!] Failed to stop keyboard listener: {e}")

        # Show window if hidden
        try:
            if not self.window_visible:
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()
        except Exception as e:
            print(f"[!] Failed to show window: {e}")

        # Close overlay
        try:
            if getattr(self, 'fov_overlay', None):
                self.fov_overlay.close()
        except Exception as e:
            print(f"[!] Failed to close overlay: {e}")

        # Close main window
        try:
            self.window.close()
            print("[*] VectorStrike closed successfully")
        except Exception as e:
            print(f"[!] Failed to close window: {e}")

        # Stop background shared config flags
        try:
            self.shared_config.stop = True
            self.shared_config.bhop_enabled = False
            self.shared_config.glow = False
        except Exception as e:
            print(f"[!] Failed to stop shared config: {e}")

        # Terminate multiprocessing children (safe shutdown)
        try:
            for p in multiprocessing.active_children():
                print(f"[*] Terminating: {p.name}")
                p.terminate()
                p.join(timeout=2)
        except Exception as e:
            print(f"[!] Error terminating processes: {e}")

        # Final hard exit to ensure complete shutdown (important for Nuitka)
        os._exit(0)

    def toggle_radar_overlay(self, state):
        self.wall.toggle_radar_overlay(state == Qt.Checked)

    def toggle_spectator_list(self, state):
        if self.wall:
            self.wall.ToggleSpectatorList(state == Qt.Checked)

    def toggle_flash_esp(self, state):
        self.wall.flash_esp_enabled = state == Qt.Checked

    def toggle_scope_esp(self, state):
        self.wall.scope_esp_enabled = state == Qt.Checked


    def toggle_armorbar(self, state):
        self.wall.ToggleArmorBar(state == Qt.Checked)

    def toggle_armoresp(self, state):
        self.wall.ToggleArmorESP(state == Qt.Checked)


    def toggle_noflash(self, state):
        self.wall.ToggleNoFlash(state == Qt.Checked)


    def toggle_bomb_esp(self, state):
        self.wall.ToggleBombESP(state == Qt.Checked)

    def toggle_weapon_esp(self, state):
        self.wall.ToggleWeaponESP(bool(state))

    def on_bhop_toggle(self, state):
        self.shared_config.bhop_enabled = (state == Qt.Checked)

    def toggle_distance_esp(self, state):
        self.wall.ToggleDistanceESP(state == Qt.Checked)

    def toggle_shoot_teammates(self, state):
        self.shared_config.shoot_teammates = state == Qt.Checked

    def toggle_box_esp(self, state):
        self.wall.ToggleBoxESP(state == Qt.Checked)

    def toggle_healthbar(self, state):
        self.wall.ToggleHealthBar(state == Qt.Checked)

    def toggle_health_esp(self, state):
        self.wall.ToggleHealthESP(state == Qt.Checked)

    def toggle_enemy_only(self, state):
        self.wall.ToggleEnemyOnly(state == Qt.Checked)

    def toggle_team_only(self, state):
        self.wall.ToggleTeamOnly(state == Qt.Checked)

    def toggle_name_esp(self, state):
        self.wall.ToggleNameESP(state == Qt.Checked)

    def toggle_line_esp(self, state):
        self.wall.ToggleLineESP(state == Qt.Checked)

    def toggle_head_esp(self, state):
        self.wall.ToggleHeadESP(state == Qt.Checked)

    def toggle_bone_esp(self, state):
        self.wall.ToggleBoneESP(state == Qt.Checked)

    def toggle_skeleton_esp(self, state):
        self.wall.ToggleSkeletonESP(state == Qt.Checked)

    def toggle_watermark(self, state):
        self.wall.ToggleWatermark(state == Qt.Checked)

    def toggle_crosshair(self, state):
        self.wall.ToggleCrosshair(state == Qt.Checked)



    def toggle_monitor_sync(self, state):
        """Toggle ESP monitor sync and update FPS accordingly"""
        self.monitor_sync_enabled = state == Qt.Checked
        self.shared_config.monitor_sync_enabled = self.monitor_sync_enabled

        if self.monitor_sync_enabled:
            self.fps = self.detected_refresh_rate
        else:
            self.fps = 144

        print(f"[*] Monitor sync {'ENABLED' if self.monitor_sync_enabled else 'DISABLED'}")
        print(f"[*] ESP FPS updated to: {self.fps} Hz")

    def toggle_triggerbot_always_on(self, state):
        self.shared_config.triggerbot_always_on = (state == Qt.Checked)

    def toggle_triggerbot(self, state):
        self.shared_config.triggerbot_enabled = (state == Qt.Checked)
        if state == Qt.Checked:
            always_on = getattr(self.shared_config, "triggerbot_always_on", False)
            if not always_on and not self.trigger_key:
                # Set a default trigger key that's different from menu toggle key
                self.initialize_trigger_key()
                
    def save_account_info(self):
        """
        Save account information to a JSON file in the configs directory.
        """
        try:
            email = self.email_input.text().strip()
            
            # Create configs directory if it doesn't exist
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
            os.makedirs(config_dir, exist_ok=True)
            
            # Save account info to a JSON file
            account_file = os.path.join(config_dir, "account.json")
            account_data = {
                "email": email,
                "premium": True,  # Hardcoded for now
                "expiry": "December 31, 2023",  # Hardcoded for now
                "hwid": "XXXX-XXXX-XXXX-XXXX"  # Hardcoded for now
            }
            
            with open(account_file, "w") as f:
                json.dump(account_data, f, indent=4)
                
            # Show success message
            QMessageBox.information(self.window, "Success", "Account information saved successfully!")
        except Exception as e:
            QMessageBox.warning(self.window, "Error", f"Failed to save account information: {e}")
            
    def load_account_info(self):
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
            account_file = os.path.join(config_dir, "account.json")
            
            if os.path.exists(account_file):
                with open(account_file, "r") as f:
                    account_data = json.load(f)
                    
                    # Update UI with loaded data
                    if "email" in account_data:
                        self.email_input.setText(account_data["email"])
                    
                    if "premium" in account_data:
                        premium = account_data["premium"]
                        if premium:
                            self.premium_status.setText("✅ Premium")
                            self.premium_status.setStyleSheet("color: #90EE90; font-weight: bold;")
                        else:
                            self.premium_status.setText("❌ Free")
                            self.premium_status.setStyleSheet("color: #e06666; font-weight: bold;")
                    
                    if "expiry" in account_data:
                        self.expiry_date.setText(account_data["expiry"])
                        
                    if "hwid" in account_data:
                        self.hwid_value.setText(account_data["hwid"])
        except Exception as e:
            print(f"Error loading account info: {e}")
            
    def initialize_trigger_key(self):
        if not self.trigger_key:
            # Set a default trigger key that's different from menu toggle key
            default_key = "shift"
            if default_key == self.menu_toggle_key:
                default_key = "ctrl"  # Use ctrl as alternative
            
            self.trigger_key = default_key
            
            if not self.trigger_key:
                self.shared_config.triggerbot_enabled = False
                if "triggerbot" in self.gui_elements:
                    self.gui_elements["triggerbot"].setChecked(False)
                return
            
            # Ensure we don't use menu_toggle_key as fallback
            if self.trigger_key == self.menu_toggle_key:
                from PyQt5.QtWidgets import QMessageBox
                msg = QMessageBox(self.window)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Key Conflict")
                msg.setText(f"The trigger key cannot be the same as the menu toggle key ({self.menu_toggle_key.upper()})!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                
                # Set a different default key
                self.trigger_key = "ctrl" if self.menu_toggle_key != "ctrl" else "shift"
                
                # Save the config to ensure the trigger key is persisted
                try:
                    config_path = os.path.join("configs", "general.json")
                    write_json(config_path, self.get_current_config_data())
                    print(f"[*] Saved trigger key '{self.trigger_key}' to config")
                except Exception as e:
                    print(f"[!] Failed to save trigger key to config: {e}")
                
            self.triggerbot = TriggerBot(
                triggerKey=self.trigger_key,
                shootTeammates=self.shared_config.shoot_teammates,
                shared_config=self.shared_config
            )
            print(f"[*] Triggerbot ENABLED {'(Always On)' if always_on else f'with key: {self.trigger_key}'}")
        else:
            self.triggerbot = None
            print("[*] Triggerbot DISABLED")

    def toggle_shoot_teammates(self, state):
        self.shared_config.shoot_teammates = state == Qt.Checked
        if self.triggerbot:
            self.triggerbot.shootTeammates = self.shared_config.shoot_teammates
            
    def set_trigger_key(self):
        """Set the trigger key using a non-blocking dialog."""
        dialog = SetTriggerKeyDialog(self.window)
        if dialog.exec_():
            new_key = dialog.get_selected_key()
            if new_key:
                # Check for conflict with menu toggle key
                if new_key == self.menu_toggle_key:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self.window, "Key Conflict", 
                                      f"The trigger key cannot be the same as the menu toggle key ({self.menu_toggle_key.upper()})!")
                    return

                self.trigger_key = new_key
                display_name = self.trigger_key.upper() if len(self.trigger_key) == 1 else self.trigger_key
                self.toggle_key_label.setText(f"Trigger Key: {display_name}")
                print(f"[*] Trigger key set to: {self.trigger_key}")

                if self.triggerbot:
                    self.triggerbot.triggerKey = self.trigger_key

                # Save the updated config
                try:
                    config_path = os.path.join("configs", "general.json")
                    write_json(config_path, self.get_current_config_data())
                    print(f"[*] Saved trigger key '{self.trigger_key}' to config")
                except Exception as e:
                    print(f"[!] Failed to save trigger key to config: {e}")
                
                QApplication.processEvents()
    
    def process_captured_trigger_key(self, pressed_key, waiting_dialog):
        # Process UI events to ensure responsiveness
        QApplication.processEvents()
        
        try:
            # Debug information about the raw key press
            print(f"[DEBUG] Raw key pressed: {pressed_key}")
            
            # Special handling for letter keys
            if hasattr(pressed_key, 'name') and pressed_key.name and len(pressed_key.name) == 1 and pressed_key.name.isalpha():
                self.trigger_key = pressed_key.name.lower()
                print(f"[DEBUG] Letter key detected directly: {self.trigger_key}")
            elif hasattr(pressed_key, 'char') and pressed_key.char and len(pressed_key.char) == 1 and pressed_key.char.isalpha():
                self.trigger_key = pressed_key.char.lower()
                print(f"[DEBUG] Letter key character detected: {self.trigger_key}")
            elif hasattr(pressed_key, 'name') and pressed_key.name == 'g':
                # Special handling for 'g' key which seems problematic
                self.trigger_key = 'g'
                print(f"[DEBUG] Special handling for g key")
            else:
                # Use KeyMapper to normalize the key name
                self.trigger_key = key_mapper.normalize_key_name(pressed_key)
                print(f"[DEBUG] Key normalized to: {self.trigger_key}")
            
            # Play a beep in a separate thread to indicate key was captured
            def play_beep():
                try:
                    winsound.Beep(1000, 200)
                except Exception as e:
                    print(f"[ERROR] Failed to play sound: {e}")
            
            beep_thread = threading.Thread(target=play_beep, daemon=True)
            beep_thread.start()
            
            # Process UI events to ensure responsiveness
            QApplication.processEvents()
                
            # Check if the trigger key is the same as the menu toggle key
            if self.trigger_key == self.menu_toggle_key:
                waiting_dialog.close()
                msg = QMessageBox(self.window)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Key Conflict")
                msg.setText(f"The trigger key cannot be the same as the menu toggle key ({self.menu_toggle_key.upper()})!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                return
                
            # Update UI with the new key
            display_name = self.trigger_key.upper() if len(self.trigger_key) == 1 else self.trigger_key
            print(f"[*] Trigger key set to: {self.trigger_key}")
            
            # For letter keys, ensure GLFW mapping is correct
            if len(self.trigger_key) == 1 and self.trigger_key.isalpha():
                glfw_code = ord(self.trigger_key.upper())
                print(f"[DEBUG] Letter key GLFW code: {glfw_code}")
            self.toggle_key_label.setText(f"Trigger Key: {display_name}")
            print(f"Trigger key set to: {self.trigger_key}")

            if self.triggerbot:
                self.triggerbot.triggerKey = self.trigger_key
                print(f"[DEBUG] Updated triggerbot key to: {self.trigger_key}")
            
            # Process events to ensure UI updates
            QApplication.processEvents()
            
            # Close the waiting dialog before showing the confirmation
            waiting_dialog.close()
            
            # Process events to ensure UI updates
            QApplication.processEvents()
            
            # Show confirmation message with the entered key
            QMessageBox.information(self.window, "Key Set", f"You entered: {display_name}\n\nTrigger key has been set to: {display_name}")
                
            # Save the config to ensure the trigger key is persisted
            try:
                config_path = os.path.join("configs", "general.json")
                write_json(config_path, self.get_current_config_data())
                print(f"[*] Saved trigger key '{self.trigger_key}' to config")
            except Exception as e:
                print(f"[!] Failed to save trigger key to config: {e}")
                QApplication.processEvents()
        except Exception as e:
            # Handle any errors in the main processing
            self.handle_trigger_key_error(waiting_dialog, str(e))
    
    def handle_trigger_key_error(self, waiting_dialog, error_message):
        # Process UI events to ensure responsiveness
        QApplication.processEvents()
        
        # Close the waiting dialog if an error occurs
        if waiting_dialog and waiting_dialog.isVisible():
            waiting_dialog.close()
        
        print(f"[ERROR] Failed to set trigger key: {error_message}")
        
        # Process UI events before showing error message
        QApplication.processEvents()
        
        # Show error message
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self.window, "Error", f"Failed to set trigger key: {error_message}")
        
        # Process UI events after showing error message
        QApplication.processEvents()

    def set_menu_key(self):
        """Optimized menu key setting"""
        dialog = SetMenuKeyDialog(self.window)
        dialog.key_label.setText(f"Current: {self.menu_toggle_key.upper()}")
        if dialog.exec_():
            new_key = dialog.get_selected_key()
            if new_key:
                # Check if the new menu key is the same as the trigger key
                if new_key == getattr(self, 'trigger_key', None):
                    # Import QMessageBox at the top level to avoid UnboundLocalError
                    msg = QMessageBox(self.window)
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Key Conflict")
                    msg.setText(f"The menu toggle key cannot be the same as the trigger key ({self.trigger_key.upper()})!")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.exec_()
                    return
                
                old_key = self.menu_toggle_key
                self.menu_toggle_key = new_key
                
                # Update UI elements efficiently
                self.menu_key_display.setText(self.menu_toggle_key.upper())
                self.window.setWindowTitle(f"GameBarOverlay")
                self.toggle_key_label.setText(f"Press {self.menu_toggle_key.upper()} to Toggle Menu")
                
                # Process events to ensure UI updates
                QApplication.processEvents()
                
                print(f"Menu key: {old_key} -> {self.menu_toggle_key}")
                
                # Start the menu key listener in a try-except block to handle errors
                try:
                    self.start_menu_key_listener()
                except Exception as e:
                    print(f"[ERROR] Failed to start menu key listener: {e}")
                    QMessageBox.critical(self.window, "Error", f"Failed to start menu key listener: {e}")
                    return
                
                # Show confirmation message with the entered key
                display_name = self.menu_toggle_key.upper() if len(self.menu_toggle_key) == 1 else self.menu_toggle_key
                QMessageBox.information(self.window, "Key Set", f"You entered: {display_name}\n\nMenu toggle key has been set to: {display_name}")
                
                # Save the config to ensure the menu toggle key is persisted
                try:
                    config_path = os.path.join("configs", "general.json")
                    write_json(config_path, self.get_current_config_data())
                    print(f"[*] Saved menu toggle key '{self.menu_toggle_key}' to config")
                except Exception as e:
                    print(f"[!] Failed to save menu toggle key to config: {e}")

    def Run(self):
        pw_module.overlay_init(target=self.window.windowTitle(), title=self.window.windowTitle(), fps=self.fps)

        while pw_module.overlay_loop():
            try:
                if self.wall.enabled:
                    self.wall.Render()
                if self.triggerbot:  
                    self.triggerbot.enable()
            except:
                pass
            QApplication.processEvents()

class SetMenuKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Menu Toggle Key")
        self.setFixedSize(300, 200)
        self.setModal(True)
        
        # Pre-import modules to avoid import delays during key events
        import threading
        import winsound
        
        # Process UI events to ensure dialog is fully initialized
        QApplication.processEvents()

        layout = QVBoxLayout()
        instruction = QLabel("Press any key to set as menu toggle key:")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(instruction)

        self.key_label = QLabel("Current: Insert")
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setStyleSheet("font-size: 12px; color: #90EE90; margin: 10px;")
        layout.addWidget(self.key_label)

        self.info_label = QLabel("Click OK after selecting a key")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 11px; color: #cccccc; margin: 5px;")
        layout.addWidget(self.info_label)
        
        # Add a note about supported keys
        note_label = QLabel("Supports all keys including function keys, numpad, and special keys")
        note_label.setAlignment(Qt.AlignCenter)
        note_label.setStyleSheet("font-size: 10px; color: #aaaaaa; margin: 5px;")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        button_layout = QHBoxLayout()
        for text, slot in [("OK", self.accept), ("Cancel", self.reject)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            button_layout.addWidget(btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.selected_key = None
        
        # Install event filter to handle key events at application level
        QApplication.instance().installEventFilter(self)
        
        # Process UI events after layout setup
        QApplication.processEvents()

        # Expanded map of Qt keys to names
        self.special_keys = {
            # Special keys
            Qt.Key_Escape: "escape", Qt.Key_Insert: "insert", Qt.Key_Delete: "delete",
            Qt.Key_Home: "home", Qt.Key_End: "end", Qt.Key_PageUp: "page_up",
            Qt.Key_PageDown: "page_down", Qt.Key_Tab: "tab",
            Qt.Key_CapsLock: "caps_lock", Qt.Key_Shift: "shift",
            Qt.Key_Control: "ctrl", Qt.Key_Alt: "alt", Qt.Key_Space: "space",
            Qt.Key_Enter: "enter", Qt.Key_Return: "enter", Qt.Key_Backspace: "backspace",
            
            # Function keys
            Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3", Qt.Key_F4: "f4",
            Qt.Key_F5: "f5", Qt.Key_F6: "f6", Qt.Key_F7: "f7", Qt.Key_F8: "f8",
            Qt.Key_F9: "f9", Qt.Key_F10: "f10", Qt.Key_F11: "f11", Qt.Key_F12: "f12",
            
            # Arrow keys
            Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
            
            # Numpad keys
            Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3",
            Qt.Key_4: "4", Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7",
            Qt.Key_8: "8", Qt.Key_9: "9", Qt.Key_NumLock: "num_lock",
            
            # Media keys
            Qt.Key_MediaPlay: "media_play_pause", Qt.Key_MediaStop: "media_stop",
            Qt.Key_MediaPrevious: "media_previous", Qt.Key_MediaNext: "media_next",
            Qt.Key_VolumeDown: "media_volume_down", Qt.Key_VolumeUp: "media_volume_up",
            Qt.Key_VolumeMute: "media_volume_mute"
        }

    def keyPressEvent(self, event):
        # Process UI events at the start to ensure UI is responsive
        QApplication.processEvents()
        
        try:
            key = event.key()
            key_name = self.special_keys.get(key)
            
            # Debug output for all key events
            print(f"[SetMenuKeyDialog] Key press event - key: {key}, text: '{event.text()}'")

            # Process UI events after logging
            QApplication.processEvents()

            # If not in our special keys map, try to get it from text
            if not key_name:
                text = event.text()
                if text and text.strip():
                    # Accept any printable character
                    key_name = text.lower()
                    # Debug output
                    print(f"[SetMenuKeyDialog] Got text key: '{text}', key code: {key}")
                elif key >= 0x01000000:  # Special key not in our map
                    # For any other special key, use a generic name with the key code
                    key_name = f"special_{key}"
                elif key >= 65 and key <= 90:  # ASCII range for A-Z
                    # Handle letter keys directly by their ASCII value
                    key_name = chr(key + 32)  # Convert to lowercase
                    print(f"[SetMenuKeyDialog] Got letter key: '{key_name}', key code: {key}")
                    
                # Special handling for 'g' key which seems problematic
                if text.lower() == 'g' or (key == 71):
                    key_name = 'g'
                    print(f"[SetMenuKeyDialog] Special handling for 'g' key")
                
                # Process UI events after key determination
                QApplication.processEvents()

            if key_name:
                # Store the raw key name in a non-blocking way
                self.selected_key = key_name
                
                # Process UI events after setting selected key
                QApplication.processEvents()
                
                # Get display name for UI
                display_name = key_name.upper() if len(key_name) == 1 else key_name
                self.key_label.setText(f"Selected: {display_name}")
                
                # Process events to ensure UI updates
                QApplication.processEvents()
                
                # Show key code and GLFW mapping if available
                glfw_code = 0
                if len(key_name) == 1 and key_name.isalpha():
                    # For letter keys, get GLFW code from uppercase ASCII value
                    glfw_code = ord(key_name.upper())
                    print(f"[SetMenuKeyDialog] Letter key GLFW code: {glfw_code}")
                elif len(key_name) == 1:
                    glfw_code = key_mapper.get_glfw_key_code(key_name.upper())
                
                if glfw_code > 0:
                    self.info_label.setText(f"Key code: {key} (GLFW: {glfw_code})")
                else:
                    self.info_label.setText(f"Key code: {key}")
                
                # Process events again to ensure UI updates
                QApplication.processEvents()
                
                # Accept the event immediately to prevent Qt from processing it further
                event.accept()
                
                # Process UI events before attempting to play sound
                QApplication.processEvents()
                
                # Play a sound to indicate key was captured in a non-blocking way
                try:
                    # Use a QTimer with a slightly longer delay to ensure UI responsiveness
                    QTimer.singleShot(50, lambda: self._play_sound())
                except Exception as e:
                    print(f"[SetMenuKeyDialog] Error setting up sound timer: {e}")
                    # Process UI events after exception
                    QApplication.processEvents()
                
                # Process UI events again after handling the key
                QApplication.processEvents()
                
                # Return to prevent further processing
                return
        except Exception as e:
            print(f"[ERROR] Error in keyPressEvent: {e}")
            # Process UI events after exception
            QApplication.processEvents()
            
    def _play_sound(self):
        """Play a sound in a way that won't block the UI thread"""
        # Process UI events before attempting to play sound
        QApplication.processEvents()
        
        try:
            # Use a separate thread for sound playback to avoid blocking UI
            def play_beep():
                try:
                    import winsound
                    winsound.Beep(800, 100)
                except Exception as e:
                    print(f"[SetMenuKeyDialog] Error playing sound: {e}")
            
            # Create and start thread
            import threading
            sound_thread = threading.Thread(target=play_beep)
            sound_thread.daemon = True  # Allow app to exit even if thread is running
            sound_thread.start()
            
            # Process UI events after starting sound thread
            QApplication.processEvents()
        except Exception as e:
            print(f"[SetMenuKeyDialog] Error in sound playback: {e}")
            # Process UI events after exception
            QApplication.processEvents()

            
    def eventFilter(self, obj, event):
        # Handle key press events at application level
        if event.type() == QEvent.KeyPress:
            try:
                # Process UI events before handling key
                QApplication.processEvents()
                
                # Get key information
                key = event.key()
                text = event.text()
                
                print(f"[SetMenuKeyDialog] Event filter - key: {key}, text: '{text}'")
                
                # Process key using our existing logic
                key_name = self.special_keys.get(key)
                
                if not key_name:
                    if text and text.strip():
                        key_name = text.lower()
                    elif key >= 0x01000000:
                        key_name = f"special_{key}"
                    elif key >= 65 and key <= 90:
                        key_name = chr(key + 32)
                        
                    # Special handling for 'g' key
                    if text.lower() == 'g' or (key == 71):
                        key_name = 'g'
                
                if key_name:
                    # Store the key and update UI
                    self.selected_key = key_name
                    display_name = key_name.upper() if len(key_name) == 1 else key_name
                    self.key_label.setText(f"Selected: {display_name}")
                    
                    # Update info label with key code
                    glfw_code = 0
                    if len(key_name) == 1 and key_name.isalpha():
                        glfw_code = ord(key_name.upper())
                    elif len(key_name) == 1:
                        glfw_code = key_mapper.get_glfw_key_code(key_name.upper())
                    
                    if glfw_code > 0:
                        self.info_label.setText(f"Key code: {key} (GLFW: {glfw_code})")
                    else:
                        self.info_label.setText(f"Key code: {key}")
                    
                    # Process UI events to update labels
                    QApplication.processEvents()
                    
                    # Play sound in a separate thread
                    import threading
                    sound_thread = threading.Thread(target=self._play_sound)
                    sound_thread.daemon = True
                    sound_thread.start()
                    
                    # Process UI events after handling key
                    QApplication.processEvents()
                    
                    # Consume the event
                    return True
            except Exception as e:
                print(f"[ERROR] Error in event filter: {e}")
                QApplication.processEvents()
        
        # Let other events pass through
        return super().eventFilter(obj, event)
    
    def get_selected_key(self):
        return self.selected_key

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

