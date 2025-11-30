"""
Argument parsing logic for ExifSort.
"""

import argparse
import dataclasses
import os
from pathlib import Path
from typing import Any

from exifsort.models import AppConfig, colorize, colors


def get_default_value(field_name: str) -> Any:
    """Extract default value from AppConfig dataclass field."""
    f = AppConfig.__dataclass_fields__[field_name]
    if f.default_factory is not dataclasses.MISSING:
        return f.default_factory()
    return f.default


def get_default_info(default_val: Any) -> str:
    """Generate a string with default settings for help message."""
    return f"(default: '{colorize(str(default_val), colors.yellow)}')"


def get_config() -> AppConfig:
    """Parse command line arguments and return the AppConfig object."""

    parser = argparse.ArgumentParser(
        prog="exifsort",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Organize media files into date-based folders by reading EXIF creation date.\n"
        f"Requires {colorize('ExifTool', colors.green)} command-line tool and {colorize('PyExifTool', colors.green)} Python library.",
        epilog=f"Example: {colorize('exifsort', colors.green)} -o 3600 --fallback-folder UNSORTED",
    )

    def_dir_tmpl: str = get_default_value("directory_template")
    parser.add_argument(
        "-d",
        "--directory-template",
        dest="directory_template",
        type=str,
        default=def_dir_tmpl,
        metavar="TEMPLATE",
        help=f"Template for directory names {get_default_info(def_dir_tmpl)}",
    )

    parser.add_argument(
        "-D",
        "--files-details",
        dest="show_files_details",
        action="store_true",
        help="Show detailed information about each file",
    )

    def_extensions = get_default_value("extensions")
    parser.add_argument(
        "-e",
        "--extensions",
        dest="extensions",
        type=str,
        nargs="+",
        default=def_extensions,
        metavar="EXT",
        help=f"List of file extensions to process {get_default_info(def_extensions)}",
    )
    parser.add_argument(
        "-E",
        "--show-errors",
        dest="show_errors",
        action="store_true",
        help="Show files with errors",
    )

    def_file_tmpl = get_default_value("file_template")
    parser.add_argument(
        "-f",
        "--file-template",
        dest="file_template",
        type=str,
        default=def_file_tmpl,
        metavar="TEMPLATE",
        help=f"Template for file names {get_default_info(def_file_tmpl)}",
    )
    parser.add_argument(
        "-i",
        "--interfix",
        dest="interfix",
        type=str,
        default=get_default_value("interfix"),
        metavar="TEXT",
        help="Text to insert between timestamp prefix and original filename",
    )

    def_day_starts = get_default_value("time_day_starts")
    parser.add_argument(
        "-n",
        "--new-day",
        dest="time_day_starts",
        type=str,
        default=def_day_starts,
        metavar="HH:MM:SS",
        help=f"Time when the new day starts {get_default_info(def_day_starts)}",
    )
    parser.add_argument(
        "-N",
        "--no-normalize",
        dest="normalize_ext",
        action="store_false",
        default=get_default_value("normalize_ext"),
        help="Do not normalize extensions to 3-letter lowercase",
    )

    def_fallback = get_default_value("fallback_folder")
    parser.add_argument(
        "-F",
        "--fallback-folder",
        dest="fallback_folder",
        type=str,
        default=def_fallback,
        metavar="FOLDER",
        help=f"Folder name for images without EXIF date {get_default_info(def_fallback)}",
    )
    parser.add_argument(
        "-o",
        "--offset",
        dest="offset",
        type=int,
        default=get_default_value("offset"),
        metavar="SECONDS",
        help="Time offset in seconds to apply to EXIF dates",
    )
    parser.add_argument(
        "-O",
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="Overwrite existing files during move/rename operation",
    )
    parser.add_argument(
        "-c",
        "--check",
        dest="check_mode",
        action="store_true",
        help="Check mode: validate files and report issues without moving them",
    )
    parser.add_argument(
        "-p",
        "--no-prefix",
        dest="use_prefix",
        action="store_false",
        default=get_default_value("use_prefix"),
        help="Do not add timestamp prefix to filenames",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Quiet mode (suppress non-error messages)",
    )
    parser.add_argument(
        "-s",
        "--skip-fallback",
        dest="_skip_fallback",
        action="store_true",
        help="Do not move files without date to fallback folder",
    )
    parser.add_argument(
        "-S",
        "--settings",
        dest="show_settings",
        action="store_true",
        help="Show raw settings (variable values)",
    )
    parser.add_argument(
        "-r",
        "--rename",
        dest="use_subdirs",
        action="store_false",
        default=get_default_value("use_subdirs"),
        help="Rename in place (do not move files in subdirectories)",
    )
    parser.add_argument(
        "-t",
        "--test",
        dest="test",
        action="store_true",
        help="Test mode: show what would be done without making changes",
    )
    parser.add_argument(
        "-v", "--version", dest="show_version", action="store_true", help="Print version and exit"
    )
    parser.add_argument(
        "-T",
        "--templates",
        dest="show_templates",
        action="store_true",
        help="Show available directory and file templates and exit",
    )
    parser.add_argument(
        "-V",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Print detailed information during processing",
    )
    parser.add_argument(
        "-y", "--yes", dest="yes", action="store_true", help="Assume 'yes' to all prompts"
    )
    parser.add_argument(
        "directory",
        type=str,
        default=os.getcwd(),
        nargs="?",
        help="Directory to organize (default: current working directory)",
    )

    args = parser.parse_args()

    # Validate time_day_starts format
    try:
        time_parts = args.time_day_starts.split(":")
        if len(time_parts) != 3:
            raise ValueError("Must be in HH:MM:SS format")
        h, m, s = map(int, time_parts)
        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
            raise ValueError("Invalid time values (hours: 0-23, minutes/seconds: 0-59)")
    except ValueError as e:
        print(
            f"{colorize('Error', colors.red)}: Invalid time format for --new-day: {args.time_day_starts}"
        )
        print("       Expected format: HH:MM:SS (e.g., 04:00:00)")
        print(f"       {str(e)}")
        import sys

        sys.exit(1)

    # Process extensions (remove dots, lowercase)
    extensions = tuple(ext.lower().lstrip(".") for ext in args.extensions)

    # Determine directory writable status
    source_dir = Path(args.directory).resolve()
    source_dir_writable = os.access(source_dir, os.W_OK)

    # Construct and return the immutable AppConfig
    return AppConfig(
        extensions=extensions,
        fallback_folder=args.fallback_folder,
        file_template=args.file_template,
        directory_template=args.directory_template,
        interfix=args.interfix,
        normalize_ext=args.normalize_ext,
        offset=args.offset,
        overwrite=args.overwrite,
        check_mode=args.check_mode,
        quiet=args.quiet,
        show_version=args.show_version,
        show_templates=args.show_templates,
        show_files_details=args.show_files_details,
        show_errors=args.show_errors,
        show_settings=args.show_settings,
        test=args.test,
        time_day_starts=args.time_day_starts,
        use_fallback_folder=not args._skip_fallback,
        use_prefix=args.use_prefix,
        use_subdirs=args.use_subdirs,
        verbose=args.verbose,
        yes=args.yes,
        source_dir=source_dir,
        source_dir_writable=source_dir_writable,
    )
