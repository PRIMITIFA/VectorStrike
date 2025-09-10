from Process.offsets import Offsets
import pyMeow as pw_module

class Entity:
    def __init__(self, pointer, pawnPointer, process):
        self.pointer = pointer
        self.pawnPointer = pawnPointer
        self.process = process
        self.pos2d = None
        self.headPos2d = None

    def Health(self):
        return pw_module.r_int(self.process, self.pawnPointer + Offsets.m_iHealth)

    def Team(self):
        return pw_module.r_int(self.process, self.pawnPointer + Offsets.m_iTeamNum)

    def Pos(self):
        return pw_module.r_vec3(self.process, self.pawnPointer + Offsets.m_vOldOrigin)

    def Name(self):
        player_name = pw_module.r_string(self.process, self.pointer + Offsets.m_iszPlayerName, 32)
        return player_name.split("\x00")[0]

    def Dormant(self):
        try:
            return pw_module.r_bool(self.process, self.pawnPointer + Offsets.m_bDormant)
        except:
            return True  # treat unreadable as dormant


    def BonePos(self, index):
        # Get the address of the game scene
        gameScene = pw_module.r_int64(self.process, self.pawnPointer + Offsets.m_pGameSceneNode)
        
        # Get the bone array pointer from the game scene
        boneArrayPointer = pw_module.r_int64(self.process, gameScene + Offsets.m_pBoneArray)
        
        # Calculate the bone position and return it
        return pw_module.r_vec3(self.process, boneArrayPointer + index * 32)

    def ArmorValue(self):
        try:
            return pw_module.r_int(self.process, self.pawnPointer + Offsets.m_ArmorValue)
        except Exception:
            return 0

    def Weapon(self):
        try:
            weapon_services = pw_module.r_int64(self.process, self.pawn + Offsets.m_pWeaponServices)
            if not weapon_services:
                return None
            h_active_weapon = pw_module.r_int(self.process, weapon_services + Offsets.m_hActiveWeapon)
            if not h_active_weapon:
                return None

            entity_list = pw_module.r_int64(self.process, self.module + Offsets.dwEntityList)
            high = (h_active_weapon & 0x7FFF) >> 9
            low = h_active_weapon & 0x1FF
            entity_entry = pw_module.r_int64(self.process, entity_list + 0x8 * high + 16)
            weapon_entity = pw_module.r_int64(self.process, entity_entry + 120 * low)  # 0x78 = 120 decimal

            return pw_module.r_string(self.process, weapon_entity + Offsets.m_EntityName, 32)
        except:
            return None


    def Wts(self, matrix):
        try:
            self.pos2d = pw_module.world_to_screen(matrix, self.Pos(), 1)
            self.headPos2d = pw_module.world_to_screen(matrix, self.BonePos(6), 1)
        except:
            return False

        return True