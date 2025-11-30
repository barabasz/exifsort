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


# Template format mappings to eliminate if/elif chains
DIRECTORY_TEMPLATES: dict[str, str] = {
    "YYYYMMDD": "%Y%m%d",
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYY.MM.DD": "%Y.%m.%d",
    "YYYY_MM_DD": "%Y_%m_%d",
    "YYYY-MM": "%Y-%m",
    "YYYY/MM/DD": "%Y/%m/%d",
    "YYYY/MM": "%Y/%m",
}

FILE_TEMPLATES: dict[str, str] = {
    "YYYYMMDD-HHMMSS": "%Y%m%d-%H%M%S",
    "YYYY-MM-DD-HH-MM-SS": "%Y-%m-%d-%H-%M-%S",
    "YYYY.MM.DD.HH.MM.SS": "%Y.%m.%d.%H.%M.%S",
    "YYYYMMDD_HHMMSS": "%Y%m%d_%H%M%S",
    "YYYYMMDD": "%Y%m%d",
    "YYYY-MM-DD": "%Y-%m-%d",
    "HHMMSS": "%H%M%S",
    "YYYYMMDDHHMM": "%Y%m%d%H%M",
    "YYYY-MM-DD_HH-MM-SS": "%Y-%m-%d_%H-%M-%S",
}


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


def get_normalized_extension(path: Path) -> str:
    """
    Extract and normalize file extension from path.

    Args:
        path: Path object to extract extension from

    Returns:
        Lowercase extension without leading dot
    """
    return path.suffix.lstrip(".").lower()


@dataclass(frozen=True)
class AppConfig:
    """Application configuration with default values."""

    # Settings
    extensions: tuple[str, ...] = ("jpg", "jpeg", "heic", "dng", "mov", "mp4", "orf", "ori", "raw")
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
    check_mode: bool = False
    normalize_ext: bool = True
    offset: int = 0
    overwrite: bool = False
    quiet: bool = False
    show_version: bool = False
    show_templates: bool = False
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


class PathGenerator:
    """
    Generates target paths and filenames for media files.

    Separates path generation logic from file validation and EXIF parsing.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize PathGenerator with configuration.

        Args:
            config: Application configuration
        """
        self.cfg = config

    def generate_subdir(
        self, date_time: datetime.datetime | None, fallback_folder: str
    ) -> str | None:
        """
        Generate subdirectory name based on date and configuration.

        Args:
            date_time: DateTime with offset applied (if any)
            fallback_folder: Name of fallback folder for files without dates

        Returns:
            Subdirectory name or None if subdirs disabled
        """
        if not self.cfg.use_subdirs:
            return None

        if date_time is None:
            return fallback_folder

        try:
            h, m, s = map(int, self.cfg.time_day_starts.split(":"))
            day_start_time = datetime.time(h, m, s)
        except (ValueError, AttributeError):
            # Invalid time format, fall back to default behavior (00:00:00)
            day_start_time = datetime.time(0, 0, 0)

        target_date = date_time
        if target_date.time() < day_start_time:
            target_date = target_date - datetime.timedelta(days=1)

        # Use template dictionary with fallback to default format
        format_str = DIRECTORY_TEMPLATES.get(self.cfg.directory_template, "%Y%m%d")
        return target_date.strftime(format_str)

    def generate_prefix(self, date_time: datetime.datetime) -> str:
        """
        Generate timestamp prefix for filename.

        Args:
            date_time: DateTime with offset applied (if any)

        Returns:
            Formatted timestamp prefix
        """
        # Use template dictionary with fallback to default format
        format_str = FILE_TEMPLATES.get(self.cfg.file_template, "%Y%m%d-%H%M%S")
        return date_time.strftime(format_str)

    def generate_filename(
        self, original_stem: str, prefix: str, interfix: str, extension: str
    ) -> str:
        """
        Generate new filename from components.

        Args:
            original_stem: Original filename without extension
            prefix: Timestamp prefix (if any)
            interfix: Text to insert between prefix and filename (if any)
            extension: File extension (normalized)

        Returns:
            New filename with all components
        """
        name = ""
        if prefix:
            name += prefix + "-"
        if interfix:
            name += interfix + "-"
        return f"{name}{original_stem}.{extension}"

    def generate_path(self, source_dir: Path, subdir: str | None, filename: str) -> Path:
        """
        Generate full target path for file.

        Args:
            source_dir: Source directory path
            subdir: Subdirectory name (if any)
            filename: Target filename

        Returns:
            Absolute path to target location
        """
        if self.cfg.use_subdirs:
            if subdir is None:
                return (source_dir / self.cfg.fallback_folder / filename).absolute()
            return (source_dir / subdir / filename).absolute()
        else:
            return (source_dir / filename).absolute()

    def generate_unique_path(self, base_path: Path, subdir: str) -> tuple[Path, str]:
        """
        Generate unique file path by adding _1, _2, etc. suffix if file exists.

        Args:
            base_path: The original target path
            subdir: Subdirectory name to check if it's fallback folder

        Returns:
            Tuple of (unique path, new filename)

        Raises:
            RuntimeError: If unable to find unique name after 9999 attempts
        """
        # Only apply unique naming for fallback folder
        if subdir != self.cfg.fallback_folder:
            return base_path, base_path.name

        if not base_path.exists():
            return base_path, base_path.name

        # Extract stem and extension
        stem = base_path.stem
        ext = base_path.suffix
        parent = base_path.parent

        # Try adding _1, _2, _3, etc. until we find a unique name
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{ext}"
            if not new_path.exists():
                return new_path, new_path.name
            counter += 1
            # Safety limit to prevent infinite loop
            if counter > 9999:
                raise RuntimeError(f"Could not generate unique filename after {counter} attempts")


class FileItem:
    """Class representing a media file with its properties."""

    def __init__(self, path: Path, config: AppConfig, metadata: dict[str, str | int] | None = None):
        self.cfg = config
        self.path_gen = PathGenerator(config)
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
        # Initialize attributes to None in case of early return
        self.exif_date = None
        self.date_time = None
        self.exif_type = None
        self.type = "unknown"

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

        # Generate prefix using PathGenerator
        if self.exif_date and self.cfg.use_prefix and self.date_time is not None:
            self.prefix = self.path_gen.generate_prefix(self.date_time)
        else:
            self.prefix = ""

        self.interfix = self.cfg.interfix if self.cfg.interfix else ""

        # Generate subdirectory using PathGenerator
        if self.cfg.use_subdirs:
            self.subdir = self.path_gen.generate_subdir(self.date_time, self.cfg.fallback_folder)

        # Generate filename using PathGenerator
        self.name_new = self.path_gen.generate_filename(
            self.stem, self.prefix, self.interfix, self.ext_new
        )

        # Generate path using PathGenerator
        self.path_new = self.path_gen.generate_path(self.cfg.source_dir, self.subdir, self.name_new)

    def get_exif_date(self) -> datetime.datetime | None:
        if not self.metadata:
            return None

        for tag in self.cfg.exif_date_tags:
            if tag in self.metadata:
                try:
                    date_str = str(self.metadata[tag])

                    # Validate minimum length to avoid index errors
                    if len(date_str) < 19:
                        continue

                    # Handle EXIF date format: YYYY:MM:DD HH:MM:SS -> YYYY-MM-DD HH:MM:SS
                    if ":" in date_str[:10] and date_str[4:5] == ":":
                        date_str = date_str.replace(":", "-", 2)

                    return datetime.datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError) as e:
                    # Try next tag if this one fails to parse
                    if self.cfg.verbose:
                        self.error = f"Invalid date format in {tag}: {str(e)}"
                    continue
                except Exception as e:
                    # Unexpected error, try next tag
                    if self.cfg.verbose:
                        self.error = f"Unexpected error parsing {tag}: {str(e)}"
                    continue

        # No valid date found in any tag
        if not self.error:
            self.error = "No valid EXIF date found in any tag."
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

    def get_new_extension(self) -> str:
        ext = self.ext_old.lower() if self.cfg.normalize_ext else self.ext_old
        return self.cfg.change_extensions.get(ext, ext)

    def get_unique_path(self, base_path: Path) -> Path:
        """
        Generate a unique file path by adding _1, _2, etc. suffix if file exists.
        Only applies to files going to fallback folder.

        Args:
            base_path: The original target path

        Returns:
            Unique path that doesn't conflict with existing files
        """
        # Use PathGenerator to generate unique path
        subdir = self.subdir if self.subdir is not None else self.cfg.fallback_folder
        new_path, new_filename = self.path_gen.generate_unique_path(base_path, subdir)
        # Update internal state to reflect the new unique name
        self.name_new = new_filename
        return new_path
