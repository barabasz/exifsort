#!/usr/bin/env python3
"""
Sort media files into date-based folders by reading EXIF creation date.
Requires: ExifTool command-line tool and PyExifTool Python library.
"""

import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path
from tyconf import TyConf
from exifsort import __date__, __version__
from exifsort.models import Colors, FileItem

# Global config instance (initialized in main)
cfg: TyConf | None = None
start_time: float = 0.0
colors = Colors()


def init_config() -> TyConf:
    return TyConf(
        script_name=(str, "exifsort", True),  # Poprawiłem nazwę skryptu na exifsort
        script_version=(str, __version__, True),
        script_date=(str, __date__, True),
        script_author=(str, "github.com/barabasz", True),
        extensions=(list, ["jpg", "jpeg", "dng", "mov", "mp4", "orf", "ori", "raw"]),
        change_extensions=(dict, {"jpeg": "jpg", "tiff": "tif"}, True),
        exif_date_tags=(
            list,
            ["EXIF:DateTimeOriginal", "EXIF:CreateDate", "XMP:CreateDate", "QuickTime:CreateDate"],
            True,
        ),
        fallback_folder=(str, "_UNKNOWN"),
        file_template=(str, "YYYYMMDD-HHMMSS"),
        directory_template=(str, "YYYYMMDD"),
        interfix=(str, ""),
        indent=(str, "    ", True),
        terminal_clear=(str, "\r\033[K\r", True),
        normalize_ext=(bool, True),
        offset=(int, 0),
        overwrite=(bool, False),
        quiet=(bool, False),
        show_version=(bool, False),
        show_files_details=(bool, False),
        show_errors=(bool, False),
        show_settings=(bool, False),
        test=(bool, False),
        time_day_starts=(str, "04:00:00"),
        use_fallback_folder=(bool, False),
        use_prefix=(bool, True),
        use_subdirs=(bool, True),
        verbose=(bool, False),
        yes=(bool, False),
        source_dir=(Path, Path.cwd()),
        source_dir_writable=(bool, False),
    )


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{colors.reset}"


def get_status(value: bool) -> str:
    return colorize("ON", colors.green) if value else colorize("OFF", colors.red)


def print_progress(item: int, total: int, message: str, show_percentage: bool = True) -> None:
    if show_percentage:
        percentage = (item / total) * 100 if total > 0 else 0
        msg = (
            f"{cfg.terminal_clear}{cfg.indent}File {item} of {total}: {message} ({percentage:.0f}%)"
        )
    else:
        msg = f"{cfg.terminal_clear}{cfg.indent}File {item} of {total}: {message}"
    print(msg, end="", flush=True)


def update_config_from_args(args) -> None:
    special_handling = {"directory", "_skip_fallback"}
    for arg_name, arg_value in vars(args).items():
        if arg_name in special_handling:
            continue
        if hasattr(cfg, arg_name):
            if arg_name == "extensions":
                cfg.extensions = [ext.lower().lstrip(".") for ext in arg_value]
            else:
                setattr(cfg, arg_name, arg_value)
    cfg.use_fallback_folder = not args._skip_fallback
    cfg.source_dir = Path(args.directory).resolve()
    cfg.source_dir_writable = os.access(cfg.source_dir, os.W_OK)


def parse_args() -> None:
    parser = argparse.ArgumentParser(
        prog=cfg.script_name,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Organize media files into date-based folders by reading EXIF creation date.\n"
        f"Requires {colorize('ExifTool', colors.green)} command-line tool and {colorize('PyExifTool', colors.green)} Python library.\n"
        f"Default schema: {get_schema()}",
        epilog=f"Example: {colorize(cfg.script_name, colors.green)} -o 3600 --fallback-folder UNSORTED",
    )
    parser.add_argument(
        "-d",
        "--directory-template",
        dest="directory_template",
        type=str,
        default=cfg.directory_template,
        metavar="TEMPLATE",
        help=f"Template for directory names (default: '{colorize(cfg.directory_template, colors.yellow)}')",
    )
    parser.add_argument(
        "-D",
        "--files-details",
        dest="show_files_details",
        action="store_true",
        help="Show detailed information about each file",
    )
    parser.add_argument(
        "-e",
        "--extensions",
        dest="extensions",
        type=str,
        nargs="+",
        default=cfg.extensions,
        metavar="EXT",
        help=f"List of file extensions to process (default: '{colorize(', '.join(cfg.extensions), colors.yellow)}')",
    )
    parser.add_argument(
        "-E",
        "--show-errors",
        dest="show_errors",
        action="store_true",
        help="Show files with errors",
    )
    parser.add_argument(
        "-f",
        "--file-template",
        dest="file_template",
        type=str,
        default=cfg.file_template,
        metavar="TEMPLATE",
        help=f"Template for file names (default: '{colorize(cfg.file_template, colors.yellow)}')",
    )
    parser.add_argument(
        "-i",
        "--interfix",
        dest="interfix",
        type=str,
        default=cfg.interfix,
        metavar="TEXT",
        help="Text to insert between timestamp prefix and original filename",
    )
    parser.add_argument(
        "-n",
        "--new-day",
        dest="time_day_starts",
        type=str,
        default=cfg.time_day_starts,
        metavar="HH:MM:SS",
        help=f"Time when the new day starts (default: '{colorize(cfg.time_day_starts, colors.yellow)}')",
    )
    parser.add_argument(
        "-N",
        "--no-normalize",
        dest="normalize_ext",
        action="store_false",
        help="Do not normalize extensions to 3-letter lowercase",
    )
    parser.add_argument(
        "-F",
        "--fallback-folder",
        dest="fallback_folder",
        type=str,
        default=cfg.fallback_folder,
        metavar="FOLDER",
        help=f"Folder name for images without EXIF date (default: '{colorize(cfg.fallback_folder, colors.yellow)}')",
    )
    parser.add_argument(
        "-o",
        "--offset",
        dest="offset",
        type=int,
        default=cfg.offset,
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
        "-p",
        "--no-prefix",
        dest="use_prefix",
        action="store_false",
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
        default=str(cfg.source_dir),
        nargs="?",
        help="Directory to organize (default: current working directory)",
    )
    args = parser.parse_args()
    update_config_from_args(args)


def printe(message: str, exit_code: int = 1) -> None:
    msg = message if exit_code == 0 else f"{colorize('Error', colors.red)}: {message}"
    print(msg)
    sys.exit(exit_code)


def check_conditions() -> None:
    # Check if ExifTool command-line tool is available (binary check)
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("\033[0;31mExifTool command-line tool is not installed or not in PATH.\033[0m")
        print("Please download and install it from: \033[0;36mhttps://exiftool.org/\033[0m")
        sys.exit(1)
    if cfg.show_version:
        msg = f"{colorize(cfg.script_name, colors.green)} version {colorize(cfg.script_version, colors.cyan)} ({cfg.script_date}) by {colorize(cfg.script_author, colors.cyan)}"
        printe(msg, 0)
    if not cfg.source_dir.is_dir():
        printe(
            f"The specified directory '{colorize(str(cfg.source_dir), colors.cyan)}' does not exist or is not a directory.",
            1,
        )
    if not cfg.source_dir_writable:
        printe(
            f"The specified directory '{colorize(str(cfg.source_dir), colors.cyan)}' is not writable.",
            1,
        )
    if not cfg.extensions or all(ext.strip() == "" for ext in cfg.extensions):
        printe("At least one file extension must be specified.", 1)
    if cfg.quiet and cfg.verbose:
        printe("Cannot use both quiet mode and verbose mode.", 1)


def get_schema() -> str:
    file_org = "FileName.Ext"
    arrow = colorize("→", colors.yellow)
    folder = colorize(cfg.directory_template, colors.cyan)
    folder = f"{folder}/" if cfg.use_subdirs else ""
    prefix = colorize(cfg.file_template, colors.cyan)
    file_new = file_org.lower() if cfg.normalize_ext else file_org
    if cfg.use_prefix:
        sep = f"-{cfg.interfix}-" if cfg.interfix else "-"
        file_new = f"{prefix}{sep}{file_new}"
    return f"{file_org} {arrow} {folder}{file_new}"


def print_schema() -> None:
    print(f"{colorize('Schema:', colors.yellow)}")
    print(f"{cfg.indent}{get_schema()}")


def print_settings() -> None:
    print(f"{colorize('RAW Settings:', colors.yellow)}")
    settings = {
        "change_extensions": cfg.change_extensions,
        "exif_date_tags": cfg.exif_date_tags,
        "extensions": cfg.extensions,
        "fallback_folder": cfg.fallback_folder,
        "file_template": cfg.file_template,
        "directory_template": cfg.directory_template,
        "interfix": cfg.interfix,
        "normalize_ext": cfg.normalize_ext,
        "offset": cfg.offset,
        "overwrite": cfg.overwrite,
        "quiet": cfg.quiet,
        "show_version": cfg.show_version,
        "show_files_details": cfg.show_files_details,
        "show_settings": cfg.show_settings,
        "source_dir": cfg.source_dir,
        "source_dir_writable": cfg.source_dir_writable,
        "test": cfg.test,
        "time_day_starts": cfg.time_day_starts,
        "use_fallback_folder": cfg.use_fallback_folder,
        "use_prefix": cfg.use_prefix,
        "use_subdirs": cfg.use_subdirs,
        "verbose": cfg.verbose,
        "yes": cfg.yes,
    }
    for key, value in settings.items():
        print(f"{cfg.indent}{key}: {colorize(str(value), colors.cyan)}")


def print_header() -> None:
    global start_time
    start_time = time.time()
    print(
        f"{colorize('Media Organizer Script', colors.green)} ({colorize(cfg.script_name, colors.green)}) v{cfg.script_version}"
    )
    if cfg.show_settings and not cfg.quiet:
        print_settings()
    print_schema()
    if cfg.quiet:
        return
    print(f"{colorize('Settings:', colors.yellow)}")
    if cfg.verbose:
        print(f"{cfg.indent}Verbose mode: {get_status(cfg.verbose)}")
    if cfg.test or cfg.verbose:
        print(f"{cfg.indent}Test mode: {get_status(cfg.test)}")
    if cfg.extensions:
        print(f"{cfg.indent}Include extensions: {colorize(', '.join(cfg.extensions), colors.cyan)}")
    if cfg.verbose or not cfg.use_subdirs:
        print(f"{cfg.indent}Process to subdirectories: {get_status(cfg.use_subdirs)}")
    if cfg.use_subdirs:
        print(f"{cfg.indent}Subfolder template: {colorize(cfg.directory_template, colors.cyan)}")
    if cfg.verbose or cfg.time_day_starts != "00:00:00":
        print(f"{cfg.indent}Day starts time set to: {colorize(cfg.time_day_starts, colors.cyan)}")
    if cfg.verbose or cfg.overwrite:
        print(f"{cfg.indent}Overwrite existing files: {get_status(cfg.overwrite)}")
    if cfg.verbose or not cfg.normalize_ext:
        print(f"{cfg.indent}Normalize extensions: {get_status(cfg.normalize_ext)}")
    if cfg.verbose or not cfg.use_prefix:
        print(f"{cfg.indent}Add prefix to filenames: {get_status(cfg.use_prefix)}")
    if cfg.verbose or cfg.use_prefix:
        print(f"{cfg.indent}Prefix format: {colorize(cfg.file_template, colors.cyan)}")
    if cfg.verbose or not cfg.use_fallback_folder:
        print(f"{cfg.indent}Use fallback folder: {get_status(cfg.use_fallback_folder)}")
    if cfg.use_fallback_folder:
        print(f"{cfg.indent}Fallback folder name: {colorize(cfg.fallback_folder, colors.cyan)}")
    if cfg.verbose or cfg.offset != 0:
        print(f"{cfg.indent}Time offset: {colorize(f'{cfg.offset} seconds', colors.cyan)}")
    if cfg.interfix or cfg.verbose:
        print(f"{cfg.indent}Interfix: {colorize(cfg.interfix, colors.cyan)}")


def get_elapsed_time() -> tuple[str, str]:
    elapsed_time = (time.time() - start_time) * 1000
    time_factor = "ms" if elapsed_time < 1000 else "s"
    elapsed_time = elapsed_time / 1000 if elapsed_time >= 1000 else elapsed_time
    return f"{elapsed_time:.2f}", time_factor


def print_footer(folder_info: dict) -> None:
    time_elapsed, time_factor = get_elapsed_time()
    print(f"{colorize('Summary:', colors.yellow)}")
    if cfg.test:
        print(f"{cfg.indent}Test mode (no changes made).")
    else:
        print(f"{cfg.indent}Processed files: {len(folder_info['processed_files'])}")
        print(f"{cfg.indent}Skipped files: {len(folder_info['skipped_files'])}")
        print(f"{cfg.indent}Directories created: {len(folder_info['created_dirs'])}")
    print(f"{cfg.indent}Completed in: {colorize(time_elapsed, colors.cyan)} {time_factor}.")


def prompt_user(folder_info: dict[str, int]) -> bool:
    if cfg.yes or cfg.test:
        return True
    file_count = folder_info["valid_files"]
    question = f"Do you want to continue with {file_count} files? (yes/No): "
    answer = input(colorize(question, colors.yellow)).strip().lower()
    if answer in ("y", "yes"):
        return True
    print("Operation cancelled by user.")
    return False


def get_media_objects(file_list: list[Path], folder_info: dict) -> list[FileItem]:
    """Convert list of Paths to list of FileItem objects."""
    media_count = folder_info.get("media_count", 0)

    print(f"{colorize('Analyzing files:', colors.yellow)}")

    # Filter media files by extension
    media_files = [f for f in file_list if f.suffix.lstrip(".").lower() in cfg.extensions]

    # Process files with progress
    media_objects = []
    for item, file in enumerate(media_files, start=1):
        media_item = FileItem(file, cfg)

        if cfg.show_files_details and not cfg.quiet:
            print_file_info(media_item)
        else:
            print_progress(item, media_count, colorize(media_item.name_old, colors.cyan))

        media_objects.append(media_item)

    if not cfg.show_files_details:
        print(f"{cfg.terminal_clear}{cfg.indent}Completed.")

    return media_objects


def get_file_list(directory: Path) -> list[Path]:
    files = [directory / file for file in os.listdir(directory) if (directory / file).is_file()]
    return sorted(files, key=lambda x: x.name.lower())


def get_folder_info(file_list: list[Path]) -> dict:
    info = {
        "path": cfg.source_dir,
        "created": datetime.datetime.fromtimestamp(cfg.source_dir.stat().st_ctime).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "modified": datetime.datetime.fromtimestamp(cfg.source_dir.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "file_count": len(file_list),
        "media_count": sum(1 for f in file_list if f.suffix.lstrip(".").lower() in cfg.extensions),
        "media_types": {},
        "processed_files": [],
        "skipped_files": [],
        "created_dirs": [],
    }
    for f in file_list:
        ext = f.suffix.lstrip(".").lower()
        if ext in cfg.extensions:
            info["media_types"][ext] = info["media_types"].get(ext, 0) + 1
    return info


def print_folder_info(folder_info: dict) -> None:
    print(f"{colorize('Folder info:', colors.yellow)}")
    print(f"{cfg.indent}Path: {colorize(str(cfg.source_dir), colors.cyan)}")
    print(f"{cfg.indent}Total files: {colorize(str(folder_info['file_count']), colors.cyan)}")
    if cfg.verbose:
        media_types_str = ", ".join(
            f"{colorize(str(count), colors.cyan)} x {colorize(ext.upper(), colors.cyan)}"
            for ext, count in folder_info["media_types"].items()
        )
        print(
            f"{cfg.indent}Matching files: {colorize(str(folder_info['media_count']), colors.cyan)} ({media_types_str})"
        )
        print(f"{cfg.indent}Created: {colorize(folder_info['created'], colors.cyan)}")
        print(f"{cfg.indent}Modified: {colorize(folder_info['modified'], colors.cyan)}")
    else:
        print(
            f"{cfg.indent}Matching files: {colorize(str(folder_info['media_count']), colors.cyan)}"
        )


def print_file_errors(files: list[FileItem]) -> None:
    invalid = [f for f in files if not f.is_valid]
    if invalid:
        print(f"{colorize('Files not valid:', colors.yellow)}")
        for file in invalid:
            print(
                f"{cfg.indent}{colorize(file.name_old, colors.cyan)}: {colorize(file.error, colors.red)}"
            )
    errors = [f for f in files if f.is_valid and f.error]
    if errors:
        print(f"{colorize('Files with errors:', colors.yellow)}")
        for file in errors:
            print(
                f"{cfg.indent}{colorize(file.name_old, colors.cyan)}: {colorize(file.error, colors.red)}"
            )


def print_files_info(files: list[FileItem], folder_info: dict) -> None:
    total_files = len(files)
    valid_files = sum(1 for f in files if f.is_valid)
    invalid_files = total_files - valid_files
    folder_info["valid_files"] = valid_files
    folder_info["invalid_files"] = invalid_files
    if not cfg.quiet:
        print(f"{colorize('Files Summary:', colors.yellow)}")
        print(f"{cfg.indent}Total files analyzed: {colorize(str(total_files), colors.cyan)}")
        print(f"{cfg.indent}Valid files: {colorize(str(valid_files), colors.cyan)}")
        print(f"{cfg.indent}Invalid files: {colorize(str(invalid_files), colors.cyan)}")
    if (cfg.verbose or cfg.show_errors) and invalid_files > 0:
        print_file_errors(files)


def print_file_info(file: FileItem) -> None:
    print(f"{colorize('File:', colors.yellow)} {colorize(file.name_old, colors.yellow)}")
    for prop, value in file.__dict__.items():
        if prop == "metadata" or prop == "cfg":
            continue
        if value in (None, "", [], {}):
            continue
        if prop == "error" and value:
            print(f"{cfg.indent}{prop}: {colorize(value, colors.red)}")
        elif prop == "is_valid" and not value:
            print(f"{cfg.indent}{prop}: {colorize(str(value), colors.red)}")
        else:
            print(f"{cfg.indent}{prop}: {colorize(str(value), colors.cyan)}")


def print_process_file(file: FileItem, item: int, total_items: int) -> None:
    if cfg.verbose:
        old = colorize(f"{file.name_old:<13}", colors.cyan)
        arr = colorize("→", colors.yellow)
        sub = f"{colorize(file.subdir, colors.cyan)}/" if cfg.use_subdirs else ""
        new = colorize(file.name_new, colors.cyan)
        exf_color = colors.cyan if file.exif_date else colors.red
        exf = file.exif_date if file.exif_date else "EXIF data not found"
        print(f"{cfg.indent}{old} ({colorize(str(exf), exf_color)}) {arr} {sub}{new}")
    else:
        print_progress(item, total_items, colorize(file.name_old, colors.cyan))


def process_files(media_list: list[FileItem], folder_info: dict) -> None:
    processed_files = []
    skipped_files = []
    created_dirs = []
    total_items = folder_info["valid_files"]
    action = "Moving" if cfg.use_subdirs else "Renaming"
    print(f"{colorize(f'{action} files:', colors.yellow)}")

    for item, file in enumerate((f for f in media_list if f.is_valid), start=1):
        if cfg.use_subdirs:
            target_dir = cfg.source_dir / file.subdir
            if not target_dir.exists() and not cfg.test:
                target_dir.mkdir(parents=True, exist_ok=True)
                created_dirs.append(file.subdir)
        if file.path_new.exists() and not cfg.overwrite:
            file.error = "Target file already exists."
            skipped_files.append(file.name_old)
            continue
        if not cfg.test:
            try:
                file.path_old.rename(file.path_new)
            except Exception as e:
                file.error = f"Error moving file: {str(e)}"
                skipped_files.append(file.name_old)
                continue
        print_process_file(file, item, total_items)
        processed_files.append(file.name_old)

    if not cfg.verbose and processed_files:
        print(f"{cfg.terminal_clear}{cfg.indent}Done.")
    if not processed_files and not cfg.quiet:
        print(f"{cfg.indent}No files were processed.")
    if (cfg.verbose or cfg.show_errors) and skipped_files:
        print_file_errors(media_list)
    folder_info["processed_files"] = processed_files
    folder_info["skipped_files"] = skipped_files
    folder_info["created_dirs"] = created_dirs


def main() -> None:
    global cfg
    cfg = init_config()
    parse_args()
    cfg.freeze()
    check_conditions()
    print_header()
    file_list = get_file_list(cfg.source_dir)
    folder_info = get_folder_info(file_list)
    print_folder_info(folder_info)
    files = get_media_objects(file_list, folder_info)
    print_files_info(files, folder_info)
    if folder_info["valid_files"] == 0:
        print("No valid media files to process. Exiting.")
        sys.exit(0)
    if not prompt_user(folder_info):
        sys.exit(0)
    process_files(files, folder_info)
    print_footer(folder_info)


if __name__ == "__main__":
    main()
