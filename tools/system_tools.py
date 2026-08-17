import platform
from datetime import datetime


class SystemTools:

    @staticmethod
    def get_time():
        return datetime.now().strftime("%I:%M:%S %p")

    @staticmethod
    def get_system_info():
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }