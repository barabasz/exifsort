import datetime
import os
import time
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def _get_pyproject_data() -> dict[str, Any]:
    """
    Load data from pyproject.toml located in the project root.
    Cached to prevent multiple file reads.
    Assumes structure: project_root/src/exifsort/models.py
    """
    try:
        # Navigate up from src/exifsort/models.py to project root
        pyproject_path = Path(__file__).parents[2] / "pyproject.toml"

        if not pyproject_path.is_file():
            return {}

        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _get_script_version() -> str:
    """Get version directly from pyproject.toml [project] section."""
    data = _get_pyproject_data()
    return str(data.get("project", {}).get("version", "0.0.0"))


def _get_script_date() -> str:
    """Get date directly from pyproject.toml [tool.exifsort] section."""
    data = _get_pyproject_data()
    return str(data.get("tool", {}).get("exifsort", {}).get("date", ""))


def _get_script_repo() -> str:
    """Get repository URL from [project.urls]."""
    data = _get_pyproject_data()
    return str(data.get("project", {}).get("urls", {}).get("Repository", ""))


def _get_script_name() -> str:
    """Get project name from [project]."""
    data = _get_pyproject_data()
    return str(data.get("project", {}).get("name", "exifsort"))


def _get_script_author() -> str:
    """Get first author name from [project.authors]."""
    data = _get_pyproject_data()
    # Structure: authors = [ { name = "...", email = "..." } ]
    authors = data.get("project", {}).get("authors", [])
    if isinstance(authors, list) and len(authors) > 0:
        return str(authors[0].get("name", ""))
    return ""


def _get_script_license() -> str:
    """Get license identifier from [project]."""
    data = _get_pyproject_data()
    # New format: license = "MIT" (string)
    # Old format: license = { text = "MIT" } (dict)
    lic = data.get("project", {}).get("license", "")
    if isinstance(lic, dict):
        return str(lic.get("text", ""))
    return str(lic)


@dataclass
class Colors:
    """Terminal color codes."""

    reset: str = "\033[0m"
    red: str = "\033[31m"
    green: str = "\033[32m"
    yellow: str = "\033[33m"
    cyan: str = "\033[36m"
    magenta: str = "\033[35m"


# global Colors instance
colors = Colors()


def colorize(text: str, color: str) -> str:
    """Wrap text in color codes."""
    return f"{color}{text}{colors.reset}"


@dataclass(frozen=True)
class AppConfig:
    """Application configuration with default values."""

    # Settings
    extensions: tuple[str, ...] = ("jpg", "jpeg", "dng", "mov", "mp4", "orf", "ori", "raw")
    change_extensions: dict[str, str] = field(
        default_factory=lambda: {"jpeg": "jpg", "tiff": "tif"}
    )
    exif_date_tags: tuple[str, ...] = (
        "EXIF:DateTimeOriginal",
        "EXIF:CreateDate",
        "XMP:CreateDate",
        "QuickTime:CreateDate",
    )

    # Templates & Formatting
    fallback_folder: str = "_UNKNOWN"
    file_template: str = "YYYYMMDD-HHMMSS"
    directory_template: str = "YYYYMMDD"
    interfix: str = ""
    indent: str = "    "
    terminal_clear: str = "\r\033[K\r"
    time_day_starts: str = "04:00:00"

    # Flags & Values
    normalize_ext: bool = True
    offset: int = 0
    overwrite: bool = False
    quiet: bool = False
    show_version: bool = False
    show_files_details: bool = False
    show_errors: bool = False
    show_settings: bool = False
    test: bool = False
    use_fallback_folder: bool = True
    use_prefix: bool = True
    use_subdirs: bool = True
    verbose: bool = False
    yes: bool = False

    # Runtime metadata
    script_name: str = field(default_factory=_get_script_name)
    script_version: str = field(default_factory=_get_script_version)
    script_date: str = field(default_factory=_get_script_date)
    script_author: str = field(default_factory=_get_script_author)
    script_repo: str = field(default_factory=_get_script_repo)
    script_license: str = field(default_factory=_get_script_license)

    # Runtime state
    start_time: float = field(default_factory=time.time)
    source_dir: Path = field(default_factory=Path.cwd)
    source_dir_writable: bool = False

    def print_config(self, show_all: bool = False) -> None:
        """
        Print all configuration properties alphabetically.
        """
        print(f"{colorize('RAW Settings:', colors.yellow)}")

        for key in sorted(self.__dict__.keys()):
            if not show_all and key.startswith("_"):
                continue
            if key == "terminal_clear":
                continue

            value = getattr(self, key)
            print(f"{self.indent}{key}: {colorize(str(value), colors.cyan)}")


class FileItem:
    """Class representing a media file with its properties."""

    def __init__(self, path: Path, config: AppConfig, metadata: dict[str, str | int] | None = None):
        self.cfg = config
        self.path_old = path.absolute()
        self.name_old = path.name
        self.stem = path.stem
        self.ext_old = path.suffix.lstrip(".")
        self.error = ""
        self.metadata = metadata
        self.is_valid = True
        self.subdir: str | None = None

        if not self._validate_file():
            return

        self._process_exif()
        self._generate_new_name()

    def _validate_file(self) -> bool:
        if not self.path_old.exists():
            self.error = "File does not exist."
            self.is_valid = False
            return False

        self.size = self.path_old.stat().st_size
        if self.size == 0:
            self.error = "File is empty."
            self.is_valid = False
            return False

        self.readable = os.access(self.path_old, os.R_OK)
        if not self.readable:
            self.error = "File is not readable."
            self.is_valid = False
            return False

        self.writable = os.access(self.path_old, os.W_OK)
        if not self.writable:
            self.error = "File is not writable."
            self.is_valid = False
            return False

        return True

    def _process_exif(self) -> None:
        if self.metadata is None:
            self.error = "Metadata not provided or could not be read."
            self.is_valid = False
            return

        self.exif_date = self.get_exif_date()
        if self.exif_date is None:
            self.error = "No EXIF date found."
            if not self.cfg.use_fallback_folder:
                self.is_valid = False
                return

        if self.exif_date is not None:
            self.date_time = self.exif_date + datetime.timedelta(seconds=self.cfg.offset)

        self.exif_type = self.get_exif_type()
        self.type = self.exif_type.split("/")[0] if self.exif_type else "unknown"

    def _generate_new_name(self) -> None:
        self.ext_new = self.get_new_extension()

        if self.exif_date and self.cfg.use_prefix:
            self.prefix = self.get_prefix()
        else:
            self.prefix = ""

        self.interfix = self.cfg.interfix if self.cfg.interfix else ""

        if self.cfg.use_subdirs:
            self.subdir = self.get_subdir()

        self.name_new = self.get_new_name()
        self.path_new = self.get_new_path()

    def get_subdir(self) -> str | None:
        if not self.cfg.use_subdirs:
            return None

        if self.exif_date is None:
            return self.cfg.fallback_folder

        h, m, s = map(int, self.cfg.time_day_starts.split(":"))
        day_start_time = datetime.time(h, m, s)

        target_date = self.date_time
        if target_date.time() < day_start_time:
            target_date = target_date - datetime.timedelta(days=1)

        if self.cfg.directory_template == "YYYYMMDD":
            return target_date.strftime("%Y%m%d")
        elif self.cfg.directory_template == "YYYY-MM-DD":
            return target_date.strftime("%Y-%m-%d")
        else:
            return target_date.strftime("%Y%m%d")

    def get_prefix(self) -> str:
        if self.cfg.file_template == "YYYYMMDD-HHMMSS":
            return self.date_time.strftime("%Y%m%d-%H%M%S")
        return self.date_time.strftime("%Y%m%d-%H%M%S")

    def get_exif_date(self) -> datetime.datetime | None:
        if not self.metadata:
            return None

        try:
            for tag in self.cfg.exif_date_tags:
                if tag in self.metadata:
                    date_str = str(self.metadata[tag])
                    if ":" in date_str[:10] and date_str[4:5] == ":":
                        date_str = date_str.replace(":", "-", 2)
                    return datetime.datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError, IndexError) as e:
            self.error = f"Error extracting EXIF date: {str(e)}"

        return None

    def get_exif_type(self) -> str | None:
        if not self.metadata:
            return None

        try:
            if "File:MIMEType" in self.metadata:
                return str(self.metadata["File:MIMEType"])
        except Exception as e:
            self.error = f"Error extracting EXIF type: {str(e)}"

        return None

    def get_new_name(self) -> str:
        name = ""
        if self.prefix:
            name += self.prefix + "-"
        if self.interfix:
            name += self.interfix + "-"
        return f"{name}{self.stem}.{self.ext_new}"

    def get_new_path(self) -> Path:
        source_dir = self.cfg.source_dir

        if self.cfg.use_subdirs:
            if self.subdir is None:
                return (source_dir / self.cfg.fallback_folder / self.name_new).absolute()
            return (source_dir / self.subdir / self.name_new).absolute()
        else:
            return (source_dir / self.name_new).absolute()

    def get_new_extension(self) -> str:
        ext = self.ext_old.lower() if self.cfg.normalize_ext else self.ext_old
        return self.cfg.change_extensions.get(ext, ext)
