import datetime
import os
import time
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path


def _get_pkg_metadata() -> tuple[str, str, str]:
    """
    Parse version and date from package version string (PEP 440 local version).
    Returns: (clean_version, date_str, full_version)
    Example: '0.2.3+20251123' -> ('0.2.3', '2025-11-23', '0.2.3+20251123')
    """
    try:
        full_version = version("exifsort")
    except PackageNotFoundError:
        return "0.0.0-dev", "", "0.0.0-dev"

    clean_ver = full_version
    date_str = ""

    if "+" in full_version:
        ver_part, build_part = full_version.split("+", 1)
        clean_ver = ver_part
        if len(build_part) == 8 and build_part.isdigit():
            date_str = f"{build_part[:4]}-{build_part[4:6]}-{build_part[6:]}"
        else:
            date_str = build_part

    return clean_ver, date_str, full_version


def _get_script_version() -> str:
    return _get_pkg_metadata()[0]


def _get_script_date() -> str:
    return _get_pkg_metadata()[1]


def _get_script_version_full() -> str:
    return _get_pkg_metadata()[2]


def _get_script_repo() -> str:
    """Extract 'Repository' URL from Project-URL metadata."""
    try:
        urls = metadata("exifsort").get_all("Project-URL")
        if not urls:
            return ""
        for url_def in urls:
            if "," in url_def:
                label, url = url_def.split(",", 1)
                if label.strip().lower() == "repository":
                    # Rzutowanie na str dla bezpieczeństwa typów
                    return str(url.strip())
        return ""
    except PackageNotFoundError:
        return ""


def _get_script_name() -> str:
    try:
        val = metadata("exifsort").get("Name")
        return str(val) if val else "exifsort"
    except PackageNotFoundError:
        return "exifsort"


def _get_script_author() -> str:
    """Get author name, preferring 'Author' field, falling back to 'Author-email'."""
    try:
        meta = metadata("exifsort")
        author = meta.get("Author")
        if author:
            return str(author)
        author_email = meta.get("Author-email")
        if author_email:
            val = str(author_email)
            if "<" in val:
                return val.split("<")[0].strip()
            return val
        return ""
    except PackageNotFoundError:
        return ""


def _get_script_license() -> str:
    """Get license info, supporting both legacy 'License' and new 'License-Expression'."""
    try:
        meta = metadata("exifsort")
        lic_expr = meta.get("License-Expression")
        if lic_expr:
            return str(lic_expr)
        val = meta.get("License")
        return str(val) if val else ""
    except PackageNotFoundError:
        return ""


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
    extensions: list[str] = field(
        default_factory=lambda: ["jpg", "jpeg", "dng", "mov", "mp4", "orf", "ori", "raw"]
    )
    change_extensions: dict[str, str] = field(
        default_factory=lambda: {"jpeg": "jpg", "tiff": "tif"}
    )
    exif_date_tags: list[str] = field(
        default_factory=lambda: [
            "EXIF:DateTimeOriginal",
            "EXIF:CreateDate",
            "XMP:CreateDate",
            "QuickTime:CreateDate",
        ]
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
    script_version_full: str = field(default_factory=_get_script_version_full)
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
