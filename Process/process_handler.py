import time
import pyMeow as pw_module

class CS2Process:
    def __init__(self, process_name="cs2.exe", module_name="client.dll", wait_timeout=30):
        self.process_name = process_name
        self.module_name = module_name
        self.wait_timeout = wait_timeout

        self.process = None
        self.module_base = None

    def _wait_for_process(self):
        start_time = time.time()
        while True:
            try:
                process = pw_module.open_process(self.process_name)
                return process
            except:
                if time.time() - start_time > self.wait_timeout:
                    return None
                time.sleep(1)

    def wait_for_process(self):
        self.process = self._wait_for_process()
        if not self.process:
            raise RuntimeError(f"{self.process_name} not running after waiting {self.wait_timeout} seconds")

    def get_module_base(self):
        if not self.process:
            raise RuntimeError("Process not found; cannot get module")
        mod = pw_module.get_module(self.process, self.module_name)
        if not mod or "base" not in mod:
            raise RuntimeError(f"Module {self.module_name} not found in process {self.process_name}")
        self.module_base = mod["base"]

    def initialize(self):
        self.wait_for_process()
        self.get_module_base()

    def __repr__(self):
        if self.module_base:
            return f"<CS2Process process={self.process} module_base=0x{self.module_base:x}>"
        else:
            return "<CS2Process uninitialized>"
