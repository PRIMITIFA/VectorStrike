#V3.2
# Updates - Spectator List Fixes
# - added safe read wrappers to handle partial read errors (Error 299) gracefully
# - wrapped all memory reads in try-except blocks to prevent crashes from invalid pointers
# - used cached variables and fallback defaults to avoid accessing null or invalid memory
# - added filtering to skip invalid or self-controller entities early in the loop
# - error logging to identify problematic memory reads without spamming errors
# - ensured robust handling of pointer chains for online spectator detection
# - maintained 1-second caching

# Updated distance ESP to display infront of the box esp for easier readibility

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

from Features.triggerbot import TriggerBot, SetTriggerKeyDialog
from Features.aimbot import start_aim_rcs
from Features.bhop import BHopProcess
from Features.glow import CS2GlowManager 

# === Weapon ID map ===
WEAPON_NAMES = {
    1: "Desert Eagle", 2: "Dual Berettas", 3: "Five-SeveN", 4: "Glock", 7: "AK-47", 8: "AUG", 9: "AWP",
    10: "FAMAS", 11: "G3SG1", 14: "M249", 16: "M4A4", 17: "MAC-10", 19: "P90", 23: "MP5-SD", 24: "UMP-45",
    25: "XM1014", 26: "Bizon", 27: "MAG-7", 28: "Negev", 29: "Sawed-Off", 30: "Tec-9", 31: "Taser",
    32: "P2000", 33: "MP7", 34: "MP9", 35: "Nova", 36: "P250", 38: "SCAR-20", 39: "SG 553", 40: "SSG 08",
    41: "Knife Gold", 42: "Knife", 43: "Galil", 44: "Hegrenade", 45: "Smoke", 46: "Molotov", 47: "Decoy",
    48: "Incgrenade", 49: "C4", 59: "Knife", 60: "M4A1-S", 61: "USP-S", 63: "CZ75-Auto", 64: "R8",
    80: "Knife Ghost", 500: "Knife Bayonet", 505: "Knife Flip", 506: "Knife Gut", 507: "Knife Karambit",
    508: "Knife M9", 509: "Knife Tactical", 512: "Knife Falchion", 514: "Knife Survival Bowie",
    515: "Knife Butterfly", 516: "Knife Rush", 519: "Knife Ursus", 520: "Knife Gypsy Jackknife",
    522: "Knife Stiletto", 523: "Knife Widowmaker"
}

class WallHack:
    class RadarOverlay(QWidget):
        def __init__(self, shared_config=None):
            super().__init__()
            self.shared_config = shared_config
            self.setWindowTitle("CS2 External Radar")

            self.setWindowFlags(
                Qt.WindowStaysOnTopHint |
                Qt.FramelessWindowHint |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_NoSystemBackground)

            screen = QApplication.primaryScreen().geometry()
            self.setGeometry(-127, -127, 500, 500)

            # --- Radar state ---
            self.entities = []
            self.local_pos = (0, 0)
            self.local_yaw = 0
            self.dynamic_scale = 0.24

            # --- Drag and resize state ---
            self.dragging = False
            self.resizing = False
            self.drag_pos = None
            self.resize_edge = None
            self.margin = 10  # resize edge margin

            # --- Paint/update loop ---
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update)
            self.timer.start(16)  # ~60 FPS

            self.show()


        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.resize_edge = self.get_resize_edge(event.pos())
                if self.resize_edge:
                    self.resizing = True
                    self.drag_pos = event.globalPos()
                    self.original_geometry = self.geometry()
                else:
                    self.dragging = True
                    self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()

        def mouseMoveEvent(self, event):
            if self.resizing:
                self.handle_resize(event.globalPos())
            elif self.dragging:
                self.move(event.globalPos() - self.drag_pos)
            else:
                edge = self.get_resize_edge(event.pos())
                self.setCursor(self.get_cursor_for_edge(edge) if edge else Qt.ArrowCursor)

        def mouseReleaseEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.dragging = False
                self.resizing = False
                self.resize_edge = None
                self.setCursor(Qt.ArrowCursor)

        def get_resize_edge(self, pos):
            x, y, w, h, m = pos.x(), pos.y(), self.width(), self.height(), self.margin
            left = x <= m
            right = x >= w - m
            top = y <= m
            bottom = y >= h - m

            if top and left:
                return "top_left"
            if top and right:
                return "top_right"
            if bottom and left:
                return "bottom_left"
            if bottom and right:
                return "bottom_right"
            if left:
                return "left"
            if right:
                return "right"
            if top:
                return "top"
            if bottom:
                return "bottom"
            return None

        def get_cursor_for_edge(self, edge):
            return {
                "left": Qt.SizeHorCursor,
                "right": Qt.SizeHorCursor,
                "top": Qt.SizeVerCursor,
                "bottom": Qt.SizeVerCursor,
                "top_left": Qt.SizeFDiagCursor,
                "bottom_right": Qt.SizeFDiagCursor,
                "top_right": Qt.SizeBDiagCursor,
                "bottom_left": Qt.SizeBDiagCursor,
            }.get(edge, Qt.ArrowCursor)

        def handle_resize(self, global_pos):
            dx = global_pos.x() - self.drag_pos.x()
            dy = global_pos.y() - self.drag_pos.y()
            rect = self.original_geometry

            if self.resize_edge == "right":
                new_width = max(200, rect.width() + dx)
                self.setGeometry(rect.left(), rect.top(), new_width, rect.height())
            elif self.resize_edge == "left":
                new_x = rect.x() + dx
                new_width = max(200, rect.width() - dx)
                self.setGeometry(new_x, rect.y(), new_width, rect.height())
            elif self.resize_edge == "bottom":
                new_height = max(200, rect.height() + dy)
                self.setGeometry(rect.x(), rect.y(), rect.width(), new_height)
            elif self.resize_edge == "top":
                new_y = rect.y() + dy
                new_height = max(200, rect.height() - dy)
                self.setGeometry(rect.x(), new_y, rect.width(), new_height)
            elif self.resize_edge == "top_left":
                new_x = rect.x() + dx
                new_y = rect.y() + dy
                new_width = max(200, rect.width() - dx)
                new_height = max(200, rect.height() - dy)
                self.setGeometry(new_x, new_y, new_width, new_height)
            elif self.resize_edge == "top_right":
                new_y = rect.y() + dy
                new_width = max(200, rect.width() + dx)
                new_height = max(200, rect.height() - dy)
                self.setGeometry(rect.x(), new_y, new_width, new_height)
            elif self.resize_edge == "bottom_left":
                new_x = rect.x() + dx
                new_width = max(200, rect.width() - dx)
                new_height = max(200, rect.height() + dy)
                self.setGeometry(new_x, rect.y(), new_width, new_height)
            elif self.resize_edge == "bottom_right":
                new_width = max(200, rect.width() + dx)
                new_height = max(200, rect.height() + dy)
                self.setGeometry(rect.x(), rect.y(), new_width, new_height)

        def update_data(self, entities, local_pos, local_yaw):
            self.entities = entities
            self.local_pos = local_pos
            self.local_yaw = local_yaw

            max_distance = max((math.hypot(x - local_pos[0], y - local_pos[1]) for x, y, *_ in entities), default=1)
            scale = (min(self.width(), self.height()) / 2.2) / max_distance
            self.dynamic_scale = max(0.05, min(scale, 0.5))

        def paintEvent(self, _):
            qp = QPainter(self)
            qp.setRenderHint(QPainter.Antialiasing)
            w, h = self.width(), self.height()
            center_x, center_y = w // 2, h // 2

            # Transparent fill
            qp.setPen(Qt.NoPen)
            qp.setBrush(QColor(128, 0, 128, 160))
            qp.drawRect(0, 0, w, h)

            # White border
            qp.setPen(QColor(255, 255, 255))
            qp.setBrush(Qt.NoBrush)
            qp.drawRect(0, 0, w - 1, h - 1)

            # Center point
            qp.setBrush(QColor(255, 255, 255))
            qp.drawEllipse(center_x - 3, center_y - 3, 6, 6)

            yaw_rad = math.radians(self.local_yaw)
            fx, fy = math.cos(yaw_rad), math.sin(yaw_rad)
            dx, dy = fy * 100, fx * 100
            angle = math.radians(self.local_yaw + 180)
            rx = dx * math.cos(angle) - dy * math.sin(angle)
            ry = dx * math.sin(angle) + dy * math.cos(angle)
            scale = self.dynamic_scale
            qp.setPen(QColor(0, 255, 0))
            qp.drawLine(center_x, center_y, int(center_x + rx * scale), int(center_y + ry * scale))

            for x, y, color, yaw in self.entities:
                dx, dy = y - self.local_pos[1], x - self.local_pos[0]
                rx = dx * math.cos(angle) - dy * math.sin(angle)
                ry = dx * math.sin(angle) + dy * math.cos(angle)
                draw_x, draw_y = int(center_x + rx * scale), int(center_y + ry * scale)

                qp.setBrush(QColor(*color))
                qp.drawEllipse(draw_x - 4, draw_y - 4, 8, 8)

                yaw_rad = math.radians(yaw)
                fx, fy = x + math.cos(yaw_rad) * 100, y + math.sin(yaw_rad) * 100
                dx2, dy2 = fy - self.local_pos[1], fx - self.local_pos[0]
                rx2 = dx2 * math.cos(angle) - dy2 * math.sin(angle)
                ry2 = dx2 * math.sin(angle) + dy2 * math.cos(angle)

                qp.setPen(QColor(255, 255, 0))
                qp.drawLine(draw_x, draw_y, int(center_x + rx2 * scale), int(center_y + ry2 * scale))

    
    
    class FOVOverlay(QWidget):
        def __init__(self, shared_config, thickness=3):
            super().__init__()
            self.shared_config = shared_config
            self.thickness = thickness

            # Use QColor with the string color name
            color_name = getattr(shared_config, 'fov_overlay_color', "green")
            self.color = QColor(color_name)

            self._init_window()
            self._init_geometry()
            self._init_timer()

            print("[*] FOV Overlay running at 60 FPS")
            self.show()

        def _init_window(self):
            """Sets up the window to be transparent and non-interactive."""
            self.setWindowFlags(
                Qt.WindowStaysOnTopHint |
                Qt.FramelessWindowHint |
                Qt.WindowTransparentForInput |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_NoSystemBackground)

        def _init_geometry(self):
            """Gets screen size and centers overlay."""
            screen = QApplication.primaryScreen()
            geom = screen.geometry()
            self.screen_width, self.screen_height = geom.width(), geom.height()
            self.center_x, self.center_y = self.screen_width // 2, self.screen_height // 2
            self.setGeometry(0, 0, self.screen_width, self.screen_height)

        def _init_timer(self):
            """Starts a 60 FPS update timer."""
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update)
            self.timer.start(1000 // 60)

        def paintEvent(self, _):
            # Update color dynamically in case config changes
            color_name = getattr(self.shared_config, 'fov_overlay_color', "green")
            self.color = QColor(color_name)

            aim_fov = getattr(self.shared_config, 'FOV', 90)
            ellipse_rect = self._calculate_fov_ellipse(aim_fov)

            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(self.color, self.thickness))
            painter.drawEllipse(*ellipse_rect)

        def _calculate_fov_ellipse(self, aim_fov):
            """Calculates the bounding rectangle of the FOV ellipse."""
            game_fov = 90  # Default CS2 FOV
            aspect_ratio = self.screen_height / self.screen_width
            fudge_factor = 1.6  # Manual tweak for better appearance

            aim_rad = math.radians(aim_fov)
            game_rad = math.radians(game_fov)
            vert_rad = 2 * math.atan(math.tan(game_rad / 2) * aspect_ratio)

            radius_x = (math.tan(aim_rad / 2) / math.tan(game_rad / 2)) * (self.screen_width / 2) * fudge_factor
            radius_y = (math.tan(aim_rad / 2) / math.tan(vert_rad / 2)) * (self.screen_height / 2) * fudge_factor

            x = int(self.center_x - radius_x)
            y = int(self.center_y - radius_y)
            w = int(radius_x * 2)
            h = int(radius_y * 2)
            return x, y, w, h


    BONE_POSITIONS = {
        "head": 6,
        "chest": 15,
        "left_hand": 10,
        "right_hand": 2,
        "left_leg": 23,
        "right_leg": 26,
    }

    BONE_CONNECTIONS = [
        (0, 2),
        (2, 4),
        (4, 5),
        (5, 6),
        (4, 8),
        (8, 9),
        (9, 10),
        (4, 13),
        (13, 14),
        (14, 15),
        (0, 22),
        (22, 23),
        (23, 24),
        (0, 25),
        (25, 26),
        (26, 27),
    ]

    def __init__(self, process, module, shared_config=None):
        self.process = process
        self.module = module
        self.shared_config = shared_config

        self.enabled = True
        self.last_render_time = 0
        self.watermark_enabled = False
        self.crosshair_enabled = False
        self.enemy_only_enabled = False
        self.team_only_enabled = False

        self.distance_esp_enabled = False
        self.box_esp_enabled = False
        self.healthbar_enabled = False
        self.health_esp_enabled = False
        self.name_esp_enabled = False
        self.line_esp_enabled = False
        self.head_esp_enabled = False
        self.skeletonesp = False
        self.bone_esp_enabled = False
        self.weapon_esp_enabled = False
        self.bomb_plant_time = 0
        self.bomb_defuse_time = 0
        self.bomb_esp_enabled = False  # Toggleable if needed
        self.spectator_list_enabled = False
        self.last_spec_check = 0
        self.cached_spectators = []
        self.noflash_enabled = False
        self.armorbar_enabled = False
        self.armor_esp_enabled = False
        self.flash_esp_enabled = False
        self.scope_esp_enabled = False

        self.radar_overlay_enabled = False
        self.radar_overlay = None

        self.esp_font_settings = {"size": 10, "color": "cyan"}
        self.head_esp_shape = "square"
        self.head_esp_size = 10
        self.bone_esp_shape = "square"
        self.bone_esp_size = 5

        self.team_esp_color = "blue"
        self.box_esp_color = "red"
        self.head_esp_color = "yellow"
        self.line_color = "white"
        self.skeleton_esp_color = "orange"
        self.bone_esp_color = "yellow"
        self.box_background_color = "black"
        self.crosshair_color = "white"
        self.fov_overlay_color = "green"
        self.weapon_esp_color = "cyan"

        self.fov_overlay_enabled = False
        self.fov_overlay = None

        if self.shared_config and self.fov_overlay_enabled:
            self.fov_overlay = WallHack.FOVOverlay(shared_config=self.shared_config)

        if self.shared_config and self.radar_overlay_enabled:
            self.radar_overlay = WallHack.RadarOverlay(shared_config=self.shared_config)

    def SetFOVOverlayColor(self, color_str):
        if self.shared_config:
            self.shared_config.fov_overlay_color = color_str
        else:
            print("[WARN] Cannot set FOV overlay color — shared_config is None.")


    def GetFOVOverlayColor(self):
        return getattr(self.shared_config, 'fov_overlay_color', 'green')

    def ToggleSpectatorList(self, state):
        self.spectator_list_enabled = state

    def ToggleNoFlash(self, state):
        self.noflash_enabled = state

    def ToggleBombESP(self, state):
        self.bomb_esp_enabled = state

    def toggle_fov_overlay(self, state: bool):
        self.fov_overlay_enabled = state
        if state and self.shared_config:
            if not self.fov_overlay:
                self.fov_overlay = WallHack.FOVOverlay(shared_config=self.shared_config)
        elif self.fov_overlay:
            self.fov_overlay.close()
            self.fov_overlay = None

    def toggle_radar_overlay(self, state: bool):
        self.radar_overlay_enabled = state

        if state and self.shared_config:
            if not self.radar_overlay:
                self.radar_overlay = WallHack.RadarOverlay(shared_config=self.shared_config)
            else:
                self.radar_overlay.show()  # if it was hidden
        elif self.radar_overlay:
            self.radar_overlay.close()
            self.radar_overlay.deleteLater()
            self.radar_overlay = None


    def __del__(self):
        if self.fov_overlay:
            self.fov_overlay.close()
            self.fov_overlay = None

    def GetLocalPlayerTeam(self):
        try:
            pawn = pw_module.r_int64(
                self.process, self.module + Offsets.dwLocalPlayerPawn
            )
            return (
                pw_module.r_int(self.process, pawn + Offsets.m_iTeamNum)
                if pawn
                else None
            )
        except:
            return None

    def ToggleFeature(self, attr, state):
        setattr(self, attr, state)

    def ToggleDistanceESP(self, state): self.ToggleFeature("distance_esp_enabled", state)
    def ToggleBoxESP(self, state): self.ToggleFeature("box_esp_enabled", state)
    def ToggleHealthBar(self, state): self.ToggleFeature("healthbar_enabled", state)
    def ToggleHealthESP(self, state): self.ToggleFeature("health_esp_enabled", state)
    def ToggleEnemyOnly(self, state): self.ToggleFeature("enemy_only_enabled", state)
    def ToggleTeamOnly(self, state): self.ToggleFeature("team_only_enabled", state)
    def ToggleNameESP(self, state): self.ToggleFeature("name_esp_enabled", state)
    def ToggleLineESP(self, state): self.ToggleFeature("line_esp_enabled", state)
    def ToggleHeadESP(self, state): self.ToggleFeature("head_esp_enabled", state)
    def ToggleSkeletonESP(self, state): self.ToggleFeature("skeletonesp", state)
    def ToggleBoneESP(self, state): self.ToggleFeature("bone_esp_enabled", state)
    def ToggleWatermark(self, state): self.ToggleFeature("watermark_enabled", state)
    def ToggleCrosshair(self, state): self.ToggleFeature("crosshair_enabled", state)
    def ToggleWeaponESP(self, state): self.ToggleFeature("weapon_esp_enabled", state)
    def ToggleArmorBar(self, state): self.ToggleFeature("armorbar_enabled", state)
    def ToggleArmorESP(self, state): self.ToggleFeature("armor_esp_enabled", state)
    def ToggleFlashESP(self, state): self.flash_esp_enabled = state
    def ToggleScopeESP(self, state): self.scope_esp_enabled = state



    def SetColor(self, attr, color_name):
        """Set color directly by name"""
        setattr(self, attr, color_name)

    def SetWeaponESPColor(self, color_name):
        self.weapon_esp_color = color_name

    def SetBoxESPColor(self, color_name): self.SetColor("box_esp_color", color_name)
    def SetTeamESPColor(self, color_name): self.SetColor("team_esp_color", color_name)
    def SetESPFontColor(self, color_name): self.esp_font_settings["color"] = color_name
    def SetLineESPColor(self, color_name): self.SetColor("line_color", color_name)
    def SetHeadESPColor(self, color_name): self.SetColor("head_esp_color", color_name)
    def SetSkeletonESPColor(self, color_name): self.SetColor("skeleton_esp_color", color_name)
    def SetBoneESPColor(self, color_name): self.SetColor("bone_esp_color", color_name)
    def SetBoxBackgroundColor(self, color_name): self.SetColor("box_background_color", color_name)
    def SetCrosshairColor(self, color_name): self.SetColor("crosshair_color", color_name)

    def ChangeSize(self, attr, title, label, default):
        size, ok = QInputDialog.getInt(None, title, label, value=default)
        if ok:
            setattr(self, attr, size)

    def ChangeHeadESPSize(self): self.ChangeSize("head_esp_size", "Head ESP Size", "Enter Head ESP Size:", self.head_esp_size)
    def ChangeBoneESPSize(self): self.ChangeSize("bone_esp_size", "Bone ESP Size", "Enter Bone ESP Size:", self.bone_esp_size)
    def ChangeESPFontSize(self): self.esp_font_settings["size"], _ = QInputDialog.getInt(None, "Font Size", "Enter Font Size:", value=self.esp_font_settings["size"])

    def SetBoneESPShape(self, shape):
        self.bone_esp_shape = shape.lower()

    def SetHeadESPShape(self, shape):
        self.head_esp_shape = shape.lower()

    def SetHeadESPSize(self, value):
        self.head_esp_size = value

    def SetBoneESPSize(self, value):
        self.bone_esp_size = value

    def ChangeHeadESPShape(self): self.ChangeShape("head_esp_shape", "Head ESP Shape")
    def ChangeBoneESPShape(self): self.ChangeShape("bone_esp_shape", "Bone ESP Shape")

    def RenderBoneESP(self, entity, matrix):
        if not self.bone_esp_enabled:
            return

        for bone_name, bone_index in self.BONE_POSITIONS.items():
            bone_pos = entity.BonePos(bone_index)
            try:
                screen = pw_module.world_to_screen(matrix, bone_pos, 1)
            except:
                continue

            if screen:
                x, y = screen["x"], screen["y"]
                size = self.bone_esp_size
                color = pw_module.get_color(self.bone_esp_color)
                if self.bone_esp_shape == "square":
                    pw_module.draw_rectangle_lines(x - size / 2, y - size / 2, size, size, color, 1)
                elif self.bone_esp_shape == "circle":
                    pw_module.draw_circle_lines(x, y, size / 2, color)

    def resolve_entity(self, entity_list_base, index, local_controller):
        try:
            entity_size = 0x78
            high_index = (index & 0x7FFF) >> 9
            low_index = index & 0x1FF

            entry_ptr = pw_module.r_int64(self.process, entity_list_base + 8 * high_index + 16)
            if not entry_ptr:
                return None

            controller = pw_module.r_int64(self.process, entry_ptr + entity_size * low_index)
            if not controller or controller == local_controller:
                return None

            player_pawn_handle = pw_module.r_int64(self.process, controller + Offsets.m_hPlayerPawn)
            if not player_pawn_handle:
                return None

            pawn_entry_ptr = pw_module.r_int64(self.process, entity_list_base + 8 * ((player_pawn_handle & 0x7FFF) >> 9) + 16)
            if not pawn_entry_ptr:
                return None

            pawn = pw_module.r_int64(self.process, pawn_entry_ptr + entity_size * (player_pawn_handle & 0x1FF))
            if not pawn:
                return None

            return Entity(controller, pawn, self.process)
        except:
            return None

    def GetEntities(self):
        entity_list = pw_module.r_int64(self.process, self.module + Offsets.dwEntityList)
        local_controller = pw_module.r_int64(self.process, self.module + Offsets.dwLocalPlayerController)

        if not entity_list or not local_controller:
            return

        for i in range(1, 65):
            entity = self.resolve_entity(entity_list, i, local_controller)
            if entity:
                yield entity

    def _safe_read_int64(self, address):
        try:
            return pw_module.r_int64(self.process, address)
        except Exception as e:
            if "handle is invalid" in str(e).lower():
                print("[Error] Process handle invalid. Attempting to reopen...")
                try:
                    self.process = pymem.Pymem("cs2.exe")
                    self.module = pymem.process.module_from_name(self.process.process_handle, "client.dll").lpBaseOfDll
                    print("[Info] Process handle reopened successfully.")
                except Exception as e2:
                    print("[Error] Failed to reopen process:", e2)
                return None
            else:
                print(f"[Error] Unexpected read error: {e}")
                return None

    def _safe_read_int(self, address):
        try:
            return pw_module.r_int(self.process, address)
        except Exception as e:
            if "handle is invalid" in str(e).lower():
                print("[Error] Process handle invalid. Attempting to reopen...")
                try:
                    self.process = pymem.Pymem("cs2.exe")
                    self.module = pymem.process.module_from_name(self.process.process_handle, "client.dll").lpBaseOfDll
                    print("[Info] Process handle reopened successfully.")
                except Exception as e2:
                    print("[Error] Failed to reopen process:", e2)
                return None
            else:
                print(f"[Error] Unexpected read error: {e}")
                return None

    def _safe_read_int64(self, address):
        try:
            return pw_module.r_int64(self.process, address)
        except Exception:
            return 0

    def _safe_read_int(self, address):
        try:
            return pw_module.r_int(self.process, address)
        except Exception:
            return 0

    def _safe_read_string(self, address, length=32):
        try:
            return pw_module.r_string(self.process, address, length).split("\x00")[0]
        except Exception:
            return ""

    def GetSpectatorsCached(self):
        now = time.time()
        if now - getattr(self, 'last_spec_check', 0) > 1:
            self.cached_spectators = self.GetSpectators()
            self.last_spec_check = now
        return getattr(self, 'cached_spectators', [])

    def GetSpectators(self):
        try:
            client = self.module
            process = self.process

            entity_list = self._safe_read_int64(client + Offsets.dwEntityList)
            local_controller = self._safe_read_int64(client + Offsets.dwLocalPlayerController)
            if not local_controller:
                return []

            local_pawn_handle = self._safe_read_int(local_controller + Offsets.m_hPawn) & 0x7FFF
            local_pawn_entry = self._safe_read_int64(entity_list + 0x8 * (local_pawn_handle >> 9) + 0x10)
            local_pawn = self._safe_read_int64(local_pawn_entry + 120 * (local_pawn_handle & 0x1FF))
            if not local_pawn:
                return []

            spectators = []
            for i in range(1, 65):
                try:
                    controller_entry = self._safe_read_int64(entity_list + 0x8 * (i >> 9) + 0x10)
                    controller = self._safe_read_int64(controller_entry + 120 * (i & 0x1FF))
                    if not controller or controller == local_controller:
                        continue

                    observer_pawn_handle = self._safe_read_int(controller + Offsets.m_hPawn) & 0x7FFF
                    pawn_entry = self._safe_read_int64(entity_list + 0x8 * (observer_pawn_handle >> 9) + 0x10)
                    observer_pawn = self._safe_read_int64(pawn_entry + 120 * (observer_pawn_handle & 0x1FF))
                    if not observer_pawn:
                        continue

                    observer_services = self._safe_read_int64(observer_pawn + Offsets.m_pObserverServices)
                    if not observer_services:
                        continue

                    target_handle = self._safe_read_int(observer_services + Offsets.m_hObserverTarget) & 0x7FFF
                    target_entry = self._safe_read_int64(entity_list + 0x8 * (target_handle >> 9) + 0x10)
                    target_pawn = self._safe_read_int64(target_entry + 120 * (target_handle & 0x1FF))
                    if target_pawn == local_pawn:
                        name = self._safe_read_string(controller + Offsets.m_iszPlayerName)
                        spectators.append(name)

                except Exception:
                    continue

            return spectators

        except Exception as e:
            print(f"[Spectator Error] {type(e).__name__}: Unexpected error encountered: {e}")
            return []


    def update_radar_data(self):
        try:
            if not self.radar_overlay_enabled or not self.radar_overlay or not self.radar_overlay.isVisible():
                return  # Prevent crash if radar is disabled or widget is deleted

            entity_list = pw_module.r_int64(self.process, self.module + Offsets.dwEntityList)
            local_ctrl = pw_module.r_int64(self.process, self.module + Offsets.dwLocalPlayerController)
            local_pawn = pw_module.r_int64(self.process, self.module + Offsets.dwLocalPlayerPawn)
            if not (entity_list and local_ctrl and local_pawn):
                return

            local_team = pw_module.r_int(self.process, local_pawn + Offsets.m_iTeamNum)
            local_pos = pw_module.r_vec3(self.process, local_pawn + Offsets.m_vOldOrigin)
            local_yaw = pw_module.r_float(self.process, self.module + Offsets.dwViewAngles + 0x4)

            entities = []

            for i in range(1, 64):
                entry = pw_module.r_int64(self.process, entity_list + 0x8 * (i >> 9) + 0x10)
                if not entry:
                    continue

                ctrl = pw_module.r_int64(self.process, entry + 0x78 * (i & 0x1FF))
                if not ctrl or ctrl == local_ctrl:
                    continue

                handle = pw_module.r_int(self.process, ctrl + Offsets.m_hPlayerPawn) & 0x7FFF
                pawn_entry = pw_module.r_int64(self.process, entity_list + 0x8 * (handle >> 9) + 0x10)
                if not pawn_entry:
                    continue

                enemy = pw_module.r_int64(self.process, pawn_entry + 0x78 * (handle & 0x1FF))
                if not enemy:
                    continue

                if pw_module.r_int(self.process, enemy + Offsets.m_iHealth) <= 0:
                    continue
                if pw_module.r_bool(self.process, enemy + Offsets.m_bDormant):
                    continue

                team = pw_module.r_int(self.process, enemy + Offsets.m_iTeamNum)
                pos = pw_module.r_vec3(self.process, enemy + Offsets.m_vOldOrigin)
                yaw_enemy = pw_module.r_float(self.process, enemy + Offsets.m_angEyeAngles + 0x4)

                color = (255, 0, 0) if team != local_team else (0, 128, 255)
                entities.append((pos["x"], pos["y"], color, yaw_enemy))

            self.radar_overlay.update_data(entities, (local_pos["x"], local_pos["y"]), local_yaw)

        except Exception as e:
            print(f"[Radar Update Error] {type(e).__name__}: {e}")


    def Render(self):
        now = time.perf_counter()
        if hasattr(self, 'last_render_time') and now - self.last_render_time < 1 / 144:
            return
        self.last_render_time = now
        
        pw_module.begin_drawing()
        
        if self.radar_overlay_enabled and self.radar_overlay and self.radar_overlay.isVisible():
            self.update_radar_data()
        


        if not self.enabled:
            return

        local_pawn = pw_module.r_int64(self.process, self.module + Offsets.dwLocalPlayerPawn)
        if not local_pawn:
            return

        if self.noflash_enabled:
            try:
                pw_module.w_float(self.process, local_pawn + Offsets.m_flFlashDuration, 0.0)
            except Exception as e:
                print(f"[NoFlash Error] {e}")

        local_team = self.GetLocalPlayerTeam()
        if local_team is None:
            return

        matrix = pw_module.r_floats(self.process, self.module + Offsets.dwViewMatrix, 16)
        if not matrix or len(matrix) < 16:
            return

        def draw_centered(text, x, y, size, color):
            if text and x is not None and y is not None:
                text_width = pw_module.measure_text(text, size)
                pw_module.draw_text(text, x - text_width / 2, y, size, color)

        local_pos = pw_module.r_vec3(self.process, local_pawn + Offsets.m_vOldOrigin)
        if not local_pos:
            return

        font_size = self.esp_font_settings["size"]
        font_color = pw_module.get_color(self.esp_font_settings["color"])

        entities = list(self.GetEntities())
        for entity in entities:
            try:
                health = entity.Health()
                if health <= 0 or not entity.Wts(matrix):
                    continue
                    
                armor = entity.ArmorValue()
                                
                team = entity.Team()
                if team is None or (self.enemy_only_enabled and team == local_team) or (self.team_only_enabled and team != local_team):
                    continue

                head_y = entity.headPos2d["y"]
                head_x = entity.headPos2d["x"]
                feet_y = entity.pos2d["y"]
                height = feet_y - head_y
                if height <= 0:
                    continue

                width = height / 2
                center = width / 2
                box_x, box_y = head_x - center, head_y - center / 2
                box_h = height + center / 2
                color = pw_module.get_color(self.box_esp_color if team == 2 else self.team_esp_color)

                pos = entity.Pos()

                if self.box_esp_enabled:
                    fill = pw_module.fade_color(pw_module.get_color(self.box_background_color), 0.5)
                    pw_module.draw_rectangle(box_x, box_y, width, box_h, fill)
                    pw_module.draw_rectangle_lines(box_x, box_y, width, box_h, color, 0.8)

                if self.distance_esp_enabled:
                    dx, dy, dz = local_pos["x"] - pos["x"], local_pos["y"] - pos["y"], local_pos["z"] - pos["z"]
                    dist = (dx*dx + dy*dy + dz*dz) ** 0.5 / 10
                    feet_2d = pw_module.world_to_screen(matrix, pos, 1)
                    if feet_2d:
                        draw_centered(f"{int(dist)}m", feet_2d["x"], feet_2d["y"] - 10, font_size, font_color)

                # Flash and Scope ESP
                if self.flash_esp_enabled or self.scope_esp_enabled:
                    try:
                        is_scoped = pw_module.r_bool(self.process, entity.pawnPointer + Offsets.m_bIsScoped)
                        flash_duration = pw_module.r_float(self.process, entity.pawnPointer + Offsets.m_flFlashDuration)

                        flash_text = ""
                        scope_text = ""

                        if self.flash_esp_enabled and flash_duration > 0.1:
                            flash_text = "FLASHED"
                        if self.scope_esp_enabled and is_scoped:
                            scope_text = "SCOPED"

                        # Combine texts
                        status = " | ".join(filter(None, [flash_text, scope_text]))
                        if status:
                            draw_centered(status, head_x, feet_y + 15, font_size, font_color)

                    except Exception as e:
                        print(f"[State ESP Error] {e}")

                if self.healthbar_enabled:
                    bar_height = height * (health / 100)
                    bar_x = head_x - center - 5
                    bar_y = head_y + height
                    hp_color = pw_module.get_color("green" if health > 66 else "yellow" if health > 33 else "red")
                    pw_module.draw_rectangle(bar_x - 1, bar_y - bar_height - 1, 5, bar_height + 2, pw_module.get_color("black"))
                    pw_module.draw_rectangle(bar_x, bar_y - bar_height, 3, bar_height, hp_color)

                if self.health_esp_enabled:
                    pw_module.draw_text(f"HP: {health}%", head_x + center + 2, head_y - center + 10, font_size, font_color)

                if self.armorbar_enabled:
                    armor_height = height * (armor / 100)
                    # Health bar is at: head_x - center - 5
                    # Move armor bar further left
                    armor_x = head_x - center - 10 - 2  # 6 = spacing + bar width
                    armor_y = head_y + height
                    ar_color = pw_module.get_color("lightblue")
                    pw_module.draw_rectangle(armor_x - 1, armor_y - armor_height - 1, 5, armor_height + 2, pw_module.get_color("black"))
                    pw_module.draw_rectangle(armor_x, armor_y - armor_height, 3, armor_height, ar_color)

                if self.armor_esp_enabled:
                    pw_module.draw_text(f"AR: {armor}%", head_x + center + 2, head_y - center + 25, font_size, font_color)


                if self.name_esp_enabled:
                    draw_centered(entity.Name(), head_x, head_y - center - 10, font_size, font_color)

                # Weapon ESP
                if self.weapon_esp_enabled:
                    try:
                        weapon_ptr = self._safe_read_int64(entity.pawnPointer + Offsets.m_pClippingWeapon)
                        if weapon_ptr and weapon_ptr >= 0x10000:
                            def_idx = self._safe_read_int(weapon_ptr + Offsets.m_AttributeManager + Offsets.m_Item + Offsets.m_iItemDefinitionIndex)
                            weapon_name = WEAPON_NAMES.get(def_idx, "Unknown")
                            weapon_color = pw_module.get_color(self.weapon_esp_color)
                            draw_centered(weapon_name, entity.pos2d["x"], entity.pos2d["y"] + 5, font_size, weapon_color)
                    except Exception as e:
                        print(f"[WeaponESP Error] {e}")

                if self.line_esp_enabled:
                    cx = pw_module.get_screen_width() / 2
                    cy = pw_module.get_screen_height()
                    pw_module.draw_line(cx, cy, head_x, head_y, pw_module.get_color(self.line_color))

                if self.head_esp_enabled:
                    size = self.head_esp_size
                    color = pw_module.get_color(self.head_esp_color)
                    if self.head_esp_shape == "square":
                        pw_module.draw_rectangle_lines(head_x - size/2, head_y - size/2, size, size, color, 1)
                    elif self.head_esp_shape == "circle":
                        pw_module.draw_circle_lines(head_x, head_y, size/2, color)

                if self.bone_esp_enabled:
                    self.RenderBoneESP(entity, matrix)

                if self.skeletonesp:
                    skel_color = pw_module.get_color(self.skeleton_esp_color)
                    for bone_a, bone_b in self.BONE_CONNECTIONS:
                        try:
                            a = pw_module.world_to_screen(matrix, entity.BonePos(bone_a), 1)
                            b = pw_module.world_to_screen(matrix, entity.BonePos(bone_b), 1)
                            if a and b:
                                pw_module.draw_line(a["x"], a["y"], b["x"], b["y"], skel_color)
                        except Exception:
                            continue

            except Exception:
                continue

        # Bomb ESP - moved outside entity loop
        if self.bomb_esp_enabled:
            try:
                planted_c4_ptr = pw_module.r_int64(self.process, self.module + Offsets.dwPlantedC4)
                bomb_planted = planted_c4_ptr and pw_module.r_bool(self.process, self.module + Offsets.dwPlantedC4 - 0x8)
                if bomb_planted:
                    c4class = pw_module.r_int64(self.process, planted_c4_ptr)
                    node = pw_module.r_int64(self.process, c4class + Offsets.m_pGameSceneNode)
                    if node:
                        x = pw_module.r_float(self.process, node + Offsets.m_vecAbsOrigin)
                        y = pw_module.r_float(self.process, node + Offsets.m_vecAbsOrigin + 0x4)
                        z = pw_module.r_float(self.process, node + Offsets.m_vecAbsOrigin + 0x8)
                        bomb_pos = {"x": x, "y": y, "z": z}
                        
                        screen = None
                        try:
                            screen = pw_module.world_to_screen(matrix, bomb_pos, 1)
                        except Exception:
                            # world_to_screen can fail if bomb is behind the camera or offscreen
                            screen = None
                        
                        # Check screen is valid and inside screen boundaries
                        screen_width = pw_module.get_screen_width()
                        screen_height = pw_module.get_screen_height()
                        if screen and 0 <= screen["x"] <= screen_width and 0 <= screen["y"] <= screen_height:
                            if self.bomb_plant_time == 0:
                                self.bomb_plant_time = time.time()

                            time_remaining = pw_module.r_float(self.process, c4class + Offsets.m_flTimerLength) - (time.time() - self.bomb_plant_time)
                            time_remaining = max(0, time_remaining)

                            is_defusing = pw_module.r_bool(self.process, c4class + Offsets.m_bBeingDefused)
                            if is_defusing:
                                if self.bomb_defuse_time == 0:
                                    self.bomb_defuse_time = time.time()
                                defuse_remaining = pw_module.r_float(self.process, c4class + Offsets.m_flDefuseLength) - (time.time() - self.bomb_defuse_time)
                                defuse_remaining = max(0, defuse_remaining)
                                bomb_text = f"BOMB {time_remaining:.1f}s | DEF {defuse_remaining:.1f}s"
                            else:
                                self.bomb_defuse_time = 0
                                bomb_text = f"BOMB {time_remaining:.1f}s"

                            text_size = 12
                            pw_module.draw_text(
                                bomb_text, 
                                screen["x"] - pw_module.measure_text(bomb_text, text_size) // 2, 
                                screen["y"], 
                                text_size, 
                                font_color
                            )
                        else:
                            # If bomb offscreen or behind, reset timers to avoid stale info
                            self.bomb_plant_time = 0
                            self.bomb_defuse_time = 0
                else:
                    self.bomb_plant_time = 0
                    self.bomb_defuse_time = 0
            except Exception as e:
                # silently ignore errors here, or log if you want to debug
                pass

        # Spectator list
        if self.spectator_list_enabled:
            spectators = self.GetSpectatorsCached()
            base_x = 20
            line_height = 16
            header_size = 16
            text_size = 14
            start_y = pw_module.get_screen_height() // 2 - (len(spectators) * line_height + 20) // 2
            color = font_color

            # Draw header
            pw_module.draw_text("Spectator list:", base_x, start_y, header_size, color)

            # Draw each spectator name with consistent spacing
            for i, name in enumerate(spectators):
                pw_module.draw_text(name, base_x, start_y + (i + 1) * line_height, text_size, color)
                
            
        # Crosshair
        if self.crosshair_enabled:
            cx = pw_module.get_screen_width() / 2
            cy = pw_module.get_screen_height() / 2
            size = 10
            color = pw_module.get_color(self.crosshair_color)
            pw_module.draw_line(cx - size, cy, cx + size, cy, color)
            pw_module.draw_line(cx, cy - size, cx, cy + size, color)

        pw_module.end_drawing()
