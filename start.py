import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
import random
import string
import time
import logging
import ssl
try:
    from cryptography.fernet import Fernet
except ImportError:
    print("cryptography package not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography.fernet import Fernet

logging.basicConfig(
    level=logging.INFO,
    format='[*] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), random_string())
REQUIREMENTS_FILE = "requirements.txt"
PYMEOW_URL = "https://github.com/qb-0/pyMeow/releases/download/1.73.42/pyMeow-1.73.42.zip"
PYMEOW_ZIP = "pyMeow.zip"
PYMEOW_DIR = "pyMeow"

MAIN_SCRIPT = "VectorStrike_V1.py"
LAUNCHER_FILE = "launcher.py"
FOLDERS_TO_OBFUSCATE = ["Features", "Process"]
FERNET_KEY = Fernet.generate_key()
fernet = Fernet(FERNET_KEY)

def create_venv():
    if not os.path.exists(VENV_DIR):
        logging.info(f"Creating virtual environment: {VENV_DIR}")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    else:
        logging.info(f"Virtual environment already exists: {VENV_DIR}")

def install_requirements():
    pip_path = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    logging.info("Installing requirements...")
    result = subprocess.run([pip_path, "install", "-r", REQUIREMENTS_FILE, "-q"], cwd=os.path.dirname(os.path.abspath(__file__)),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logging.error(f"Failed to install pip requirements:\n{result.stderr}")
        sys.exit(1)
    logging.info("Requirements installed successfully.")

def is_pymeow_installed():
    pip_path = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    result = subprocess.run([pip_path, "show", "pyMeow"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode == 0

def download_and_install_pymeow():
    if is_pymeow_installed():
        logging.info("pyMeow already installed.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    pymeow_zip_path = os.path.join(base_dir, PYMEOW_ZIP)
    pymeow_dir_path = os.path.join(base_dir, PYMEOW_DIR)

    logging.info("Downloading pyMeow...")
    ssl._create_default_https_context = ssl._create_unverified_context
    urllib.request.urlretrieve(PYMEOW_URL, pymeow_zip_path)

    logging.info("Extracting pyMeow...")
    with zipfile.ZipFile(pymeow_zip_path, 'r') as zip_ref:
        zip_ref.extractall(pymeow_dir_path)

    pip_path = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    logging.info("Installing pyMeow...")
    result = subprocess.run([pip_path, "install", "."], cwd=pymeow_dir_path,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logging.error(f"Failed to install pyMeow:\n{result.stderr}")
        sys.exit(1)

    os.remove(pymeow_zip_path)
    shutil.rmtree(pymeow_dir_path)
    logging.info("pyMeow installed successfully.")

def get_py_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = [MAIN_SCRIPT]
    for folder in FOLDERS_TO_OBFUSCATE:
        folder_path = os.path.join(base_dir, folder)
        for root, _, filenames in os.walk(folder_path):
            for f in filenames:
                if f.endswith(".py"):
                    relative_path = os.path.relpath(os.path.join(root, f), base_dir)
                    files.append(relative_path)
    logging.info(f"Collected {len(files)} Python files for obfuscation.")
    return files

def encrypt_file(path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    abs_path = os.path.join(base_dir, path)
    with open(abs_path, "rb") as f:
        return fernet.encrypt(f.read()).decode("utf-8")

def module_name_from_path(path):
    path = os.path.splitext(path)[0]
    parts = path.replace("\\", "/").split("/")
    return ".".join(parts)

def generate_launcher():
    logging.info("Generating AES-encrypted launcher...")
    py_files = get_py_files()
    modules_enc = {}
    for f in py_files:
        mod_name = module_name_from_path(f)
        enc = encrypt_file(f)
        modules_enc[mod_name] = enc

    launcher_code = f'''import os
import sys
import importlib.abc
import importlib.util
from cryptography.fernet import Fernet

os.chdir(os.path.dirname(os.path.abspath(__file__)))

key = {FERNET_KEY!r}
fernet = Fernet(key)
modules = {modules_enc!r}

class AESLoader(importlib.abc.Loader):
    def __init__(self, name):
        self.name = name
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        code_enc = modules[self.name]
        code = fernet.decrypt(code_enc.encode()).decode('utf-8')
        exec(code, module.__dict__)
    def get_code(self, fullname):
        source = fernet.decrypt(modules[fullname].encode()).decode('utf-8')
        return compile(source, '<string>', 'exec')
    def get_source(self, fullname):
        return fernet.decrypt(modules[fullname].encode()).decode('utf-8')

class AESFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname in modules:
            return importlib.util.spec_from_loader(fullname, AESLoader(fullname))
        return None

sys.meta_path.insert(0, AESFinder())

if __name__ == '__main__':
    import runpy
    runpy.run_module('{module_name_from_path(MAIN_SCRIPT)}', run_name='__main__')
'''
    base_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_path = os.path.join(base_dir, LAUNCHER_FILE)
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher_code)

    logging.info(f"Launcher generated: {launcher_path} with {len(modules_enc)} modules.")
    return launcher_path

def prompt_update_offsets():
    while True:
        choice = input("[?] Do you want to update offsets? (y/n): ").strip().lower()
        if choice == 'y':
            logging.info("Updating offsets by running Process.offset_update.py...")
            python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe")
            subprocess.run([python_exe, "offset_update.py"], cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "Process"), check=True)
            break
        elif choice == 'n':
            logging.info("Skipping offset update.")
            break
        else:
            print("Please enter 'y' or 'n'.")

def main():
    print(r"""
 __      __       _             _____ _        _ _        
 \ \    / /      | |           / ____| |      (_) |       
  \ \  / /__  ___| |_ ___  _ _| (___ | |_ _ __ _| | _____ 
   \ \/ / _ \/ __| __/ _ \| '__\___ \| __| '__| | |/ / _ \
    \  /  __/ (__| || (_) | |  ____) | |_| |  | |   <  __/
     \/ \___|\___|\__\___/|_| |_____/ \__|_|  |_|_|\_\___|
    """)
    logging.info("Starting setup sequence...")

    create_venv()
    install_requirements()
    prompt_update_offsets()
    time.sleep(random.uniform(0.5, 3))
    download_and_install_pymeow()
    generate_launcher()

    python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe")
    logging.info(f"Executing: {LAUNCHER_FILE}")
    subprocess.run([python_exe, LAUNCHER_FILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
