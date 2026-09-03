import os
import platform
import shutil
import subprocess
from pathlib import Path


class ApplicationTools:
    """Launch a small allowlist of desktop applications without a shell.

    The model chooses only an alias. JARVIS resolves that alias to a fixed
    executable candidate, preventing arbitrary command execution through the
    application-launch tool.
    """

    @classmethod
    def _windows_candidates(cls):
        program_files = Path(os.getenv("ProgramFiles", "C:/Program Files"))
        program_files_x86 = Path(
            os.getenv("ProgramFiles(x86)", "C:/Program Files (x86)")
        )
        local_app_data = Path(os.getenv("LOCALAPPDATA", ""))

        return {
            "notepad": [["notepad.exe"]],
            "calculator": [["calc.exe"]],
            "explorer": [["explorer.exe"]],
            "terminal": [["wt.exe"], ["powershell.exe"]],
            "powershell": [["powershell.exe"]],
            "vscode": [
                [str(local_app_data / "Programs/Microsoft VS Code/Code.exe")],
                [str(program_files / "Microsoft VS Code/Code.exe")],
                ["code.exe"],
                ["code"],
            ],
            "chrome": [
                [str(program_files / "Google/Chrome/Application/chrome.exe")],
                [str(program_files_x86 / "Google/Chrome/Application/chrome.exe")],
                [str(local_app_data / "Google/Chrome/Application/chrome.exe")],
                ["chrome.exe"],
            ],
            "edge": [
                [str(program_files_x86 / "Microsoft/Edge/Application/msedge.exe")],
                [str(program_files / "Microsoft/Edge/Application/msedge.exe")],
                ["msedge.exe"],
            ],
        }

    @classmethod
    def _posix_candidates(cls):
        if platform.system() == "Darwin":
            return {
                "terminal": [["open", "-a", "Terminal"]],
                "vscode": [["code"]],
                "chrome": [["open", "-a", "Google Chrome"]],
            }

        return {
            "terminal": [
                ["x-terminal-emulator"],
                ["gnome-terminal"],
                ["konsole"],
            ],
            "vscode": [["code"]],
            "chrome": [["google-chrome"], ["chromium"], ["chromium-browser"]],
        }

    @classmethod
    def aliases(cls):
        if platform.system() == "Windows":
            return cls._windows_candidates()
        return cls._posix_candidates()

    @staticmethod
    def _resolved_command(command):
        """Return an executable command safe for subprocess with shell=False.

        On Windows, shutil.which("code") commonly resolves to code.cmd. Passing
        the unresolved alias to CreateProcess can raise WinError 2, while a
        batch file is not directly executable with shell=False. Prefer the real
        executable and derive Code.exe from VS Code's bin/code.cmd when needed.
        """
        if not command:
            return None

        executable = command[0]
        path = Path(executable)
        if path.is_absolute():
            if path.exists() and path.is_file():
                return [str(path), *command[1:]]
            return None

        resolved = shutil.which(executable)
        if not resolved:
            return None

        resolved_path = Path(resolved)
        if platform.system() == "Windows" and resolved_path.suffix.lower() in {".cmd", ".bat"}:
            if resolved_path.stem.lower() == "code":
                code_exe = resolved_path.parent.parent / "Code.exe"
                if code_exe.exists() and code_exe.is_file():
                    return [str(code_exe), *command[1:]]
            return None

        return [str(resolved_path), *command[1:]]

    @classmethod
    def _command_exists(cls, command):
        return cls._resolved_command(command) is not None

    @classmethod
    def resolve(cls, name):
        key = str(name or "").lower().strip()
        candidates = cls.aliases().get(key)
        if not candidates:
            return None

        for command in candidates:
            resolved = cls._resolved_command(command)
            if resolved is not None:
                return resolved
        return None

    @classmethod
    def list_applications(cls):
        result = []
        for name in sorted(cls.aliases()):
            result.append(
                {
                    "name": name,
                    "available": cls.resolve(name) is not None,
                }
            )
        return result

    @classmethod
    def open_application(cls, name):
        command = cls.resolve(name)
        if command is None:
            known = ", ".join(sorted(cls.aliases()))
            return (
                f"Application '{name}' is not available in the JARVIS "
                f"allowlist. Known aliases: {known}"
            )

        try:
            subprocess.Popen(
                command,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as error:
            return f"Could not open {name}: {error}"

        return f"Opened application: {str(name).lower().strip()}"
