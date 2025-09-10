from Features.aimbot import start_aim_rcs
from Features.bhop import BHopProcess
from Features.glow import CS2GlowManager

def aim_process(shared_config):
    try:
        start_aim_rcs(shared_config)
    except Exception as e:
        if "Could not find process: cs2.exe" in str(e):
            print("\n"+"="*60)
            print("[!] CS2 IS NOT RUNNING")
            print("[!] Please start Counter-Strike 2 first")
            print("[!] Make sure to run this cheat as Administrator for proper permissions")
            print("="*60)
        else:
            print(f"[!] Error in aim process: {e}")

def bhop_process(shared_config):
    try:
        bhop = BHopProcess(shared_config)
        bhop.run()
    except Exception as e:
        if any(x in str(e) for x in ["Process not found", "not running", "cs2.exe"]):
            print("\n"+"="*60)
            print("[!] CS2 IS NOT RUNNING")
            print("[!] Please start Counter-Strike 2 first")
            print("[!] Make sure to run this cheat as Administrator for proper permissions")
            print("="*60)
        else:
            print(f"[!] Error in bhop process: {e}")

def glow_process(shared_config):
    try:
        glow_manager = CS2GlowManager(shared_config)
        glow_manager.run()
    except Exception as e:
        if "Process not found" in str(e):
            print("\n"+"="*60)
            print("[!] CS2 IS NOT RUNNING")
            print("[!] Please start Counter-Strike 2 first")
            print("[!] Make sure to run this cheat as Administrator for proper permissions")
            print("="*60)
        else:
            print(f"[!] Error in glow process: {e}")