from pathlib import Path


class FileTools:

    @staticmethod
    def list_files(directory="."):
        path = Path(directory)

        if not path.exists():
            return "Directory does not exist."

        items = []

        for item in path.iterdir():
            if item.name.startswith("."):
                continue

            if item.is_dir():
                items.append(f"[DIR]  {item.name}")
            else:
                items.append(f"[FILE] {item.name}")

        if not items:
            return "Directory is empty."

        return "\n".join(sorted(items))
    