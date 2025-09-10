import keyboard
from pynput.keyboard import Key, KeyCode
import glfw
from Process.offsets import Offsets
from Process.process_handler import CS2Process

class KeyMapper:
    """
    Utility class for mapping between different key representations and handling key input
    from various sources including GLFW, Qt, keyboard module, and pynput.
    """
    
    @staticmethod
    def send_key_to_game(process: CS2Process, key_code, pressed):
        """
        Send a key press or release event to the game process
        
        Args:
            process (CS2Process): The game process to send the key to
            key_code (int): The key code to send
            pressed (bool): True for key press, False for key release
        """
        if process and process.is_running():
            try:
                process.write_int(Offsets.dwForceAttack, 1 if pressed else 0) if key_code == 0 else \
                process.write_int(Offsets.dwForceAttack2, 1 if pressed else 0) if key_code == 1 else \
                process.write_int(Offsets.dwForceForward, 1 if pressed else 0) if key_code == 87 else \
                process.write_int(Offsets.dwForceBackward, 1 if pressed else 0) if key_code == 83 else \
                process.write_int(Offsets.dwForceLeft, 1 if pressed else 0) if key_code == 65 else \
                process.write_int(Offsets.dwForceRight, 1 if pressed else 0) if key_code == 68 else \
                process.write_int(Offsets.dwForceJump, 1 if pressed else 0) if key_code == 32 else None
            except Exception as e:
                print(f"[KeyMapper] Error sending key {key_code} to game: {e}")
    
    @staticmethod
    def convert_pynput_to_glfw(key):
        """
        Convert a pynput key to a GLFW key code
        
        Args:
            key: A pynput key object or character
            
        Returns:
            int: The corresponding GLFW key code
        """
        if isinstance(key, KeyCode) and key.char:
            # For character keys, convert to uppercase ASCII value
            return ord(key.char.upper())
        elif isinstance(key, Key):
            # Map common special keys
            key_mapping = {
                Key.shift: 340,      # GLFW_KEY_LEFT_SHIFT
                Key.shift_r: 344,    # GLFW_KEY_RIGHT_SHIFT
                Key.ctrl: 341,       # GLFW_KEY_LEFT_CONTROL
                Key.ctrl_r: 345,     # GLFW_KEY_RIGHT_CONTROL
                Key.alt: 342,        # GLFW_KEY_LEFT_ALT
                Key.alt_r: 346,      # GLFW_KEY_RIGHT_ALT
                Key.space: 32,       # GLFW_KEY_SPACE
                Key.enter: 257,      # GLFW_KEY_ENTER
                Key.esc: 256,        # GLFW_KEY_ESCAPE
                Key.tab: 258,        # GLFW_KEY_TAB
                Key.up: 265,         # GLFW_KEY_UP
                Key.down: 264,       # GLFW_KEY_DOWN
                Key.left: 263,       # GLFW_KEY_LEFT
                Key.right: 262       # GLFW_KEY_RIGHT
            }
            return key_mapping.get(key, 0)
        return 0
    
    def __init__(self):
        # GLFW key mapping
        self.glfw_key_mapping = {
            "NONE": 0, 
            "MOUSE1": 0, "MOUSE2": 1, "MOUSE3": 2, 
            "MOUSE4": 3, "MOUSE5": 4, "MOUSEWHEEL_UP": -1, "MOUSEWHEEL_DOWN": -2, 
            "LSHIFT": 340, "RSHIFT": 344, "LCTRL": 341, 
            "RCTRL": 345, "LALT": 342, "RALT": 346, 
            "SPACE": 32, "ENTER": 257, "ESCAPE": 256, "TAB": 258, 
            "UP": 265, "DOWN": 264, "LEFT": 263, "RIGHT": 262, 
            "F1": 290, "F2": 291, "F3": 292, "F4": 293, "F5": 294, 
            "F6": 295, "F7": 296, "F8": 297, "F9": 298, "F10": 299, 
            "F11": 300, "F12": 301, "A": 65, "B": 66, "C": 67, 
            "D": 68, "E": 69, "F": 70, "G": 71, "H": 72, "I": 73, 
            "J": 74, "K": 75, "L": 76, "M": 77, "N": 78, "O": 79, 
            "P": 80, "Q": 81, "R": 82, "S": 83, "T": 84, "U": 85, 
            "V": 86, "W": 87, "X": 88, "Y": 89, "Z": 90, "0": 48, 
            "1": 49, "2": 50, "3": 51, "4": 52, "5": 53, "6": 54, 
            "7": 55, "8": 56, "9": 57,
        }
        
        # Reverse mapping for looking up key names by code
        self.glfw_name_mapping = {v: k for k, v in self.glfw_key_mapping.items()}
        
        # Mapping between pynput Key objects and string names
        self.pynput_key_mapping = {
            Key.alt: "alt",
            Key.alt_l: "alt_l",
            Key.alt_r: "alt_r",
            Key.alt_gr: "alt_gr",
            Key.backspace: "backspace",
            Key.caps_lock: "caps_lock",
            Key.cmd: "cmd",
            Key.cmd_l: "cmd_l",
            Key.cmd_r: "cmd_r",
            Key.ctrl: "ctrl",
            Key.ctrl_l: "ctrl_l",
            Key.ctrl_r: "ctrl_r",
            Key.delete: "delete",
            Key.down: "down",
            Key.end: "end",
            Key.enter: "enter",
            Key.esc: "esc",
            Key.f1: "f1",
            Key.f2: "f2",
            Key.f3: "f3",
            Key.f4: "f4",
            Key.f5: "f5",
            Key.f6: "f6",
            Key.f7: "f7",
            Key.f8: "f8",
            Key.f9: "f9",
            Key.f10: "f10",
            Key.f11: "f11",
            Key.f12: "f12",
            Key.home: "home",
            Key.insert: "insert",
            Key.left: "left",
            Key.menu: "menu",
            Key.num_lock: "num_lock",
            Key.page_down: "page_down",
            Key.page_up: "page_up",
            Key.pause: "pause",
            Key.print_screen: "print_screen",
            Key.right: "right",
            Key.scroll_lock: "scroll_lock",
            Key.shift: "shift",
            Key.shift_l: "shift_l",
            Key.shift_r: "shift_r",
            Key.space: "space",
            Key.tab: "tab",
            Key.up: "up",
        }
    
    def normalize_key_name(self, key):
        """
        Normalize a key name or object to a consistent string representation.
        
        Args:
            key: Can be a string, pynput.keyboard.Key, keyboard module event, or other key representation
            
        Returns:
            str: A normalized string representation of the key
        """
        # Special handling for 'g' key which seems problematic
        if (hasattr(key, 'name') and key.name == 'g') or \
           (isinstance(key, str) and key.lower() == 'g') or \
           (isinstance(key, KeyCode) and hasattr(key, 'char') and key.char == 'g'):
            print(f"[KeyMapper] Special handling for 'g' key")
            return 'g'
            
        # Handle pynput Key objects
        if isinstance(key, Key):
            return self.pynput_key_mapping.get(key, str(key).replace("Key.", ""))
            
        # Handle keyboard module events
        if hasattr(key, 'name') and key.name:
            return key.name.lower()
        
        if hasattr(key, 'char') and key.char:
            # Ensure single character keys are preserved as-is
            return key.char.lower()
            
        # Handle scan codes
        if hasattr(key, 'scan_code'):
            return f"special_{key.scan_code}"
            
        # Handle string keys
        if isinstance(key, str):
            # Ensure single character keys are preserved as-is
            return key.lower()
            
        # Default fallback
        return str(key).lower()
    
    def get_glfw_key_code(self, key_name):
        """
        Get the GLFW key code for a given key name
        
        Args:
            key_name (str): The name of the key
            
        Returns:
            int: The GLFW key code, or 0 if not found
        """
        normalized_key = key_name.upper() if isinstance(key_name, str) else key_name
        return self.glfw_key_mapping.get(normalized_key, 0)
    
    def get_key_name_from_glfw(self, key_code):
        """
        Get the key name for a given GLFW key code
        
        Args:
            key_code (int): The GLFW key code
            
        Returns:
            str: The key name, or "UNKNOWN" if not found
        """
        return self.glfw_name_mapping.get(key_code, "UNKNOWN")
    
    def is_key_pressed(self, key_name):
        """
        Check if a key is currently pressed using the keyboard module
        
        Args:
            key_name (str): The name of the key to check
            
        Returns:
            bool: True if the key is pressed, False otherwise
        """
        try:
            # Normalize the key name
            normalized_key = self.normalize_key_name(key_name)
            
            # Debug output
            # print(f"[KeyMapper] Checking key press for '{key_name}', normalized to '{normalized_key}'")
            
            # Special handling for 'g' key
            if normalized_key == 'g':
                # print(f"[KeyMapper] Special handling for 'g' key press check")
                # Try multiple ways to detect 'g' key
                return (keyboard.is_pressed('g') or 
                        keyboard.is_pressed('G') or 
                        any(keyboard._pressed_events.get(code, False) for code in [34, 71]))
            
            # Handle special keys
            if normalized_key.startswith('special_'):
                # For special keys identified by scan code
                scan_code = normalized_key.split('_')[1]
                try:
                    scan_code = int(scan_code)
                    # Use low-level check for scan code
                    return any(keyboard._pressed_events.get(code, False) 
                              for code in [scan_code, scan_code+1000])
                except ValueError:
                    return False
            elif normalized_key.startswith('f') and len(normalized_key) <= 3 and normalized_key[1:].isdigit():
                # It's a function key, ensure correct format for keyboard module
                return keyboard.is_pressed(normalized_key)
            elif len(normalized_key) == 1 and normalized_key.isalpha():
                # Single letter keys - try both the letter itself and its uppercase version
                return keyboard.is_pressed(normalized_key) or keyboard.is_pressed(normalized_key.upper())
            else:
                # Standard keys
                return keyboard.is_pressed(normalized_key)
        except Exception as e:
            print(f"[KeyMapper] Error checking key press for '{key_name}': {e}")
            return False
            
    def is_key_match(self, pressed_key, target_key):
        """
        Check if a pressed key matches a target key
        
        Args:
            pressed_key: The key that was pressed (pynput Key or KeyCode object)
            target_key: The target key to match against (pynput Key, KeyCode, or string)
            
        Returns:
            bool: True if the keys match, False otherwise
        """
        try:
            # Handle direct string comparison for single letter keys
            if isinstance(pressed_key, KeyCode) and hasattr(pressed_key, 'char') and pressed_key.char and \
               isinstance(target_key, str) and len(target_key) == 1:
                # Direct character comparison for single letters
                match = pressed_key.char.lower() == target_key.lower()
                # print(f"[KeyMapper] Direct character match: '{pressed_key.char}' vs '{target_key}' = {match}")
                return match
                
            # Normalize both keys to string representation
            pressed_key_str = self.normalize_key_name(pressed_key)
            target_key_str = self.normalize_key_name(target_key)
            
            # Debug output
            # print(f"[KeyMapper] Matching keys: '{pressed_key}' (normalized: '{pressed_key_str}') vs '{target_key}' (normalized: '{target_key_str}')")
            
            # Compare the normalized strings (case-insensitive)
            return pressed_key_str.lower() == target_key_str.lower()
        except Exception as e:
            print(f"[KeyMapper] Error matching keys: {e}")
            return False
            
    def get_pynput_key(self, key_name):
        """
        Get a pynput Key object or KeyCode from a key name
        
        Args:
            key_name (str): The name of the key
            
        Returns:
            pynput.keyboard.Key or pynput.keyboard.KeyCode or str: The pynput key object
        """
        from pynput.keyboard import Key, KeyCode
        
        # Normalize the key name
        normalized_key = key_name.lower() if isinstance(key_name, str) else key_name
        
        # Debug output
        # print(f"[KeyMapper] Getting pynput key for '{key_name}', normalized to '{normalized_key}'")
        
        # Reverse mapping from string to pynput Key
        reverse_mapping = {v: k for k, v in self.pynput_key_mapping.items()}
        
        if normalized_key in reverse_mapping:
            return reverse_mapping[normalized_key]
        elif isinstance(normalized_key, str) and len(normalized_key) == 1:
            # Single character key - create KeyCode from character
            # For letters, we need to ensure case sensitivity works correctly
            if normalized_key.isalpha():
                # For letters, create a case-insensitive matcher
                return normalized_key
            else:
                # For other characters, use KeyCode
                return KeyCode.from_char(normalized_key)
        else:
            # Return as string for custom handling
            return normalized_key

# Create a singleton instance
key_mapper = KeyMapper()