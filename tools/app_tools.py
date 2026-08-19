from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

import psutil


class AppTools:
    """Desktop application and path control helpers.

    All launch functions avoid shell=True. Higher layers are responsible for
    asking the user for permission before executing side-effecting actions.
    """

    _WINDOWS_ALIASES: dict[str, tuple[str, ...]] = {
        "vscode": ("code", "Code.exe"),
        "vs code": ("code", "Code.exe"),
        "code": ("code", "Code.exe"),
        "chrome": ("chrome.exe", "chrome"),
        "google chrome": ("chrome.exe", "chrome"),
        "edge": ("msedge.exe", "msedge"),
        "microsoft edge": ("msedge.exe", "msedge"),
        "notepad": ("notepad.exe", "notepad"),
        "calculator": ("calc.exe", "calc"),
        "calc": ("calc.exe", "calc"),
        "explorer": ("explorer.exe", "explorer"),
        "file explorer": ("explorer.exe", "explorer"),
        "powershell": ("powershell.exe", "powershell"),
        "terminal": ("wt.exe", "wt"),
        "windows terminal": ("wt.exe", "wt"),
        "cmd": ("cmd.exe", "cmd"),
    }

    @staticmethod
    def list_running_apps(limit: int = 30) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        apps: list[dict[str, Any]] = []
        seen: set[str] = set()

        for process in psutil.process_iter(["pid", "name", "exe"]):
            try:
                name = (process.info.get("name") or "").strip()
                if not name:
                    continue

                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)

                apps.append(
                    {
                        "name": name,
                        "pid": process.info.get("pid"),
                        "exe": process.info.get("exe") or "",
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        apps.sort(key=lambda item: item["name"].lower())
        return apps[:limit]

    @classmethod
    def open_app(cls, app_name: str) -> dict[str, str]:
        requested = app_name.strip()
        if not requested:
            raise ValueError("app_name cannot be empty")

        executable = cls._resolve_application(requested)
        cls._launch(executable)
        return {
            "app": requested,
            "resolved": executable,
            "message": f"Opened {requested}.",
        }

    @classmethod
    def open_path(cls, path: str) -> dict[str, str]:
        target = cls._normalise_existing_path(path)

        system = platform.system()
        if system == "Windows":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])

        return {
            "path": str(target),
            "message": f"Opened {target}.",
        }

    @classmethod
    def open_project(cls, path: str) -> dict[str, str]:
        target = cls._normalise_existing_path(path)
        if not target.is_dir():
            raise ValueError("Project path must be a directory.")

        executable = cls._resolve_application("vscode")
        cls._launch(executable, [str(target)])
        return {
            "path": str(target),
            "app": "Visual Studio Code",
            "resolved": executable,
            "message": f"Opened project {target} in Visual Studio Code.",
        }

    @classmethod
    def _resolve_application(cls, app_name: str) -> str:
        direct_path = Path(os.path.expandvars(os.path.expanduser(app_name)))
        if direct_path.is_file():
            return str(direct_path.resolve())

        candidates: tuple[str, ...]
        if platform.system() == "Windows":
            candidates = cls._WINDOWS_ALIASES.get(
                app_name.lower(),
                (app_name,),
            )
        else:
            candidates = (app_name,)

        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

        if platform.system() == "Windows":
            common = cls._windows_common_paths(app_name.lower())
            for candidate in common:
                if candidate.is_file():
                    return str(candidate)

        raise FileNotFoundError(
            f"Could not find an installed application matching '{app_name}'."
        )

    @staticmethod
    def _windows_common_paths(app_name: str) -> list[Path]:
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        program_files = Path(os.environ.get("PROGRAMFILES", ""))
        program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", ""))

        paths: list[Path] = []

        if app_name in {"vscode", "vs code", "code"}:
            paths.extend(
                [
                    local / "Programs" / "Microsoft VS Code" / "Code.exe",
                    program_files / "Microsoft VS Code" / "Code.exe",
                ]
            )

        if app_name in {"chrome", "google chrome"}:
            paths.extend(
                [
                    program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
                    program_files_x86 / "Google" / "Chrome" / "Application" / "chrome.exe",
                    local / "Google" / "Chrome" / "Application" / "chrome.exe",
                ]
            )

        if app_name in {"edge", "microsoft edge"}:
            paths.extend(
                [
                    program_files / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    program_files_x86 / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                ]
            )

        return paths

    @staticmethod
    def _normalise_existing_path(path: str) -> Path:
        raw = path.strip()
        if not raw:
            raise ValueError("path cannot be empty")

        target = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: {target}")
        return target

    @staticmethod
    def _launch(executable: str, arguments: list[str] | None = None) -> None:
        command = [executable, *(arguments or [])]
        subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
