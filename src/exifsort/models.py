import datetime
import os
from dataclasses import dataclass
from pathlib import Path

import exiftool
from tyconf import TyConf


@dataclass
class Colors:
    """Terminal color codes."""

    reset: str = "\033[0m"
    red: str = "\033[31m"
    green: str = "\033[32m"
    yellow: str = "\033[33m"
    cyan: str = "\033[36m"
    magenta: str = "\033[35m"


class FileItem:
    """Class representing a media file with its properties."""

    def __init__(self, path: Path, config: TyConf):
        """
        Initialize FileItem with path and configuration.

        Args:
            path: Path to the media file.
            config: Configuration object (TyConf instance).
        """
        self.cfg = config
        self.path_old = path.absolute()
        self.name_old = path.name
        self.stem = path.stem
        self.ext_old = path.suffix.lstrip(".")
        self.error = ""
        self.metadata = None
        self.is_valid = True

        # Validate file
        if not self._validate_file():
            return

        # Process EXIF data
        self._process_exif()

        # Generate new name and path
        self._generate_new_name()

    def _validate_file(self) -> bool:
        """Validate file accessibility and size."""
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
        """Read and process EXIF metadata."""
        if not self.read_exif_metadata():
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
        """Generate new filename and path."""
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
        """Format a subdirectory name according to the provided template."""
        if not self.cfg.use_subdirs:
            return None

        if self.exif_date is None:
            return self.cfg.fallback_folder

        # Parse time_day_starts
        h, m, s = map(int, self.cfg.time_day_starts.split(":"))
        day_start_time = datetime.time(h, m, s)

        # Adjust date if time is before day_start_time
        target_date = self.date_time
        if target_date.time() < day_start_time:
            target_date = target_date - datetime.timedelta(days=1)

        # Format the folder name according to template
        if self.cfg.directory_template == "YYYYMMDD":
            return target_date.strftime("%Y%m%d")
        elif self.cfg.directory_template == "YYYY-MM-DD":
            return target_date.strftime("%Y-%m-%d")
        else:
            return target_date.strftime("%Y%m%d")

    def get_prefix(self) -> str:
        """Format a timestamp prefix according to the provided template."""
        if self.cfg.file_template == "YYYYMMDD-HHMMSS":
            return self.date_time.strftime("%Y%m%d-%H%M%S")
        return self.date_time.strftime("%Y%m%d-%H%M%S")

    def read_exif_metadata(self) -> bool:
        """Read all EXIF metadata at once and store it."""
        try:
            with exiftool.ExifToolHelper() as et:
                self.metadata = et.get_metadata(self.path_old)[0]
                return True
        except Exception as e:
            self.error = f"Error reading EXIF metadata: {str(e)}"
            return False

    def get_exif_date(self) -> datetime.datetime | None:
        """Extract creation date from stored EXIF data."""
        if not self.metadata:
            return None

        try:
            for tag in self.cfg.exif_date_tags:
                if tag in self.metadata:
                    date_str = self.metadata[tag]
                    if isinstance(date_str, str):
                        if ":" in date_str[:10] and date_str[4:5] == ":":
                            date_str = date_str.replace(":", "-", 2)
                        return datetime.datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError, IndexError) as e:
            self.error = f"Error extracting EXIF date: {str(e)}"

        return None

    def get_exif_type(self) -> str | None:
        """Extract media type from stored EXIF data."""
        if not self.metadata:
            return None

        try:
            if "File:MIMEType" in self.metadata:
                return self.metadata["File:MIMEType"]
        except Exception as e:
            self.error = f"Error extracting EXIF type: {str(e)}"

        return None

    def get_new_name(self) -> str:
        """Generate new filename based on prefix, interfix, stem, and extension."""
        name = ""
        if self.prefix:
            name += self.prefix + "-"
        if self.interfix:
            name += self.interfix + "-"
        return f"{name}{self.stem}.{self.ext_new}"

    def get_new_path(self) -> Path:
        """Get new absolute path for the file based on settings."""
        if self.cfg.use_subdirs:
            return (self.cfg.source_dir / self.subdir / self.name_new).absolute()
        else:
            return (self.cfg.source_dir / self.name_new).absolute()

    def get_new_extension(self) -> str:
        """Get new file extension based on change_extensions mapping."""
        ext = self.ext_old.lower() if self.cfg.normalize_ext else self.ext_old
        return self.cfg.change_extensions.get(ext, ext)
