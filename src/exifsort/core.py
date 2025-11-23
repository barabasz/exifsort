#!/usr/bin/env python3
"""
Sort media files into date-based folders by reading EXIF creation date.
Requires: ExifTool command-line tool and PyExifTool Python library.
"""

import datetime
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import exiftool

from exifsort.args import get_config
from exifsort.models import AppConfig, FileItem, colorize, colors


def check_exiftool_availability() -> None:
    """Check if ExifTool command-line tool is available."""
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("\033[0;31mExifTool command-line tool is not installed or not in PATH.\033[0m")
        print("Please download and install it from: \033[0;36mhttps://exiftool.org/\033[0m")
        sys.exit(1)


def get_status(value: bool) -> str:
    return colorize("ON", colors.green) if value else colorize("OFF", colors.red)


def print_progress(
    item: int, total: int, message: str, cfg: AppConfig, show_percentage: bool = True
) -> None:
    if show_percentage:
        percentage = (item / total) * 100 if total > 0 else 0
        msg = (
            f"{cfg.terminal_clear}{cfg.indent}File {item} of {total}: {message} ({percentage:.0f}%)"
        )
    else:
        msg = f"{cfg.terminal_clear}{cfg.indent}File {item} of {total}: {message}"
    print(msg, end="", flush=True)


def printe(message: str, exit_code: int = 1) -> None:
    msg = message if exit_code == 0 else f"{colorize('Error', colors.red)}: {message}"
    print(msg)
    sys.exit(exit_code)


def check_conditions(cfg: AppConfig) -> None:
    """Check if all conditions are met to run the script."""
    check_exiftool_availability()

    if cfg.show_version:
        date_str = f" ({cfg.script_date})" if cfg.script_date else ""
        msg = (
            f"{colorize(cfg.script_name, colors.green)} "
            f"version {colorize(cfg.script_version, colors.cyan)}{date_str} "
            f"by {colorize(cfg.script_author, colors.cyan)}"
        )
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


def get_schema(cfg: AppConfig) -> str:
    file_org = "FileName.Ext"
    arrow = colorize("→", colors.yellow)
    folder = colorize(cfg.directory_template, colors.cyan)
    folder = f"{folder}/" if cfg.use_subdirs else ""
    prefix = colorize(cfg.file_template, colors.cyan)
    file_new = file_org.lower() if cfg.normalize_ext else file_org
    if cfg.use_prefix:
        interfix = cfg.interfix
        sep = f"-{interfix}-" if interfix else "-"
        file_new = f"{prefix}{sep}{file_new}"
    return f"{file_org} {arrow} {folder}{file_new}"


def print_schema(cfg: AppConfig) -> None:
    print(f"{colorize('Schema:', colors.yellow)}")
    print(f"{cfg.indent}{get_schema(cfg)}")


def print_settings(cfg: AppConfig) -> None:
    """Print settings using AppConfig internal method."""
    cfg.print_config(show_all=False)


def print_header(cfg: AppConfig) -> None:
    print(
        f"{colorize('Media Organizer Script', colors.green)} ({colorize(cfg.script_name, colors.green)}) v{cfg.script_version}"
    )
    if cfg.show_settings and not cfg.quiet:
        print_settings(cfg)
    print_schema(cfg)
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


def get_elapsed_time(start_time: float) -> tuple[str, str]:
    """Get elapsed time since script start."""
    elapsed_time = (time.time() - start_time) * 1000
    time_factor = "ms" if elapsed_time < 1000 else "s"
    elapsed_time = elapsed_time / 1000 if elapsed_time >= 1000 else elapsed_time
    return f"{elapsed_time:.2f}", time_factor


def print_footer(folder_info: dict[str, Any], cfg: AppConfig) -> None:
    time_elapsed, time_factor = get_elapsed_time(cfg.start_time)
    print(f"{colorize('Summary:', colors.yellow)}")
    if cfg.test:
        print(f"{cfg.indent}Test mode (no changes made).")
    else:
        print(f"{cfg.indent}Processed files: {len(folder_info['processed_files'])}")
        print(f"{cfg.indent}Skipped files: {len(folder_info['skipped_files'])}")
        print(f"{cfg.indent}Directories created: {len(folder_info['created_dirs'])}")
    print(f"{cfg.indent}Completed in: {colorize(time_elapsed, colors.cyan)} {time_factor}.")


def prompt_user(folder_info: dict[str, Any], cfg: AppConfig) -> bool:
    if cfg.yes or cfg.test:
        return True
    file_count = folder_info["valid_files"]
    question = f"Do you want to continue with {file_count} files? (yes/No): "
    answer = input(colorize(question, colors.yellow)).strip().lower()
    if answer in ("y", "yes"):
        return True
    print("Operation cancelled by user.")
    return False


def get_media_objects(
    file_list: list[Path], folder_info: dict[str, Any], cfg: AppConfig
) -> list[FileItem]:
    """Convert list of Paths to list of FileItem objects."""
    media_count = folder_info.get("media_count", 0)

    print(f"{colorize('Analyzing files:', colors.yellow)}")

    # Filter media files by extension
    media_files = [f for f in file_list if f.suffix.lstrip(".").lower() in cfg.extensions]

    # Process files with progress
    media_objects = []

    # Uruchamiamy ExifTool tylko raz dla całej pętli
    with exiftool.ExifToolHelper() as et:
        for item, file in enumerate(media_files, start=1):
            metadata = None
            try:
                data = et.get_metadata(str(file))
                if data:
                    metadata = data[0]
            except Exception:
                metadata = None

            media_item = FileItem(file, cfg, metadata)

            if cfg.show_files_details and not cfg.quiet:
                print_file_info(media_item, cfg)
            else:
                print_progress(item, media_count, colorize(media_item.name_old, colors.cyan), cfg)

            media_objects.append(media_item)

    if not cfg.show_files_details:
        print(f"{cfg.terminal_clear}{cfg.indent}Completed.")

    return media_objects


def get_file_list(directory: Path) -> list[Path]:
    files = [directory / file for file in os.listdir(directory) if (directory / file).is_file()]
    return sorted(files, key=lambda x: x.name.lower())


def get_folder_info(file_list: list[Path], cfg: AppConfig) -> dict[str, Any]:
    info: dict[str, Any] = {
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


def print_folder_info(folder_info: dict[str, Any], cfg: AppConfig) -> None:
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


def print_file_errors(files: list[FileItem], cfg: AppConfig) -> None:
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


def print_files_info(files: list[FileItem], folder_info: dict[str, Any], cfg: AppConfig) -> None:
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
        print_file_errors(files, cfg)


def print_file_info(file: FileItem, cfg: AppConfig) -> None:
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


def print_process_file(file: FileItem, item: int, total_items: int, cfg: AppConfig) -> None:
    if cfg.verbose:
        old = colorize(f"{file.name_old:<13}", colors.cyan)
        arr = colorize("→", colors.yellow)

        sub = f"{colorize(file.subdir, colors.cyan)}/" if file.subdir else ""

        new = colorize(file.name_new, colors.cyan)
        exf_color = colors.cyan if file.exif_date else colors.red
        exf = file.exif_date if file.exif_date else "EXIF data not found"
        print(f"{cfg.indent}{old} ({colorize(str(exf), exf_color)}) {arr} {sub}{new}")
    else:
        print_progress(item, total_items, colorize(file.name_old, colors.cyan), cfg)


def process_files(media_list: list[FileItem], folder_info: dict[str, Any], cfg: AppConfig) -> None:
    processed_files = []
    skipped_files = []
    created_dirs = []
    total_items = folder_info["valid_files"]
    action = "Moving" if cfg.use_subdirs else "Renaming"

    print(f"{colorize(f'{action} files:', colors.yellow)}")

    for item, file in enumerate((f for f in media_list if f.is_valid), start=1):
        if cfg.use_subdirs and file.subdir:
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

        print_process_file(file, item, total_items, cfg)
        processed_files.append(file.name_old)

    if not cfg.verbose and processed_files:
        print(f"{cfg.terminal_clear}{cfg.indent}Done.")
    if not processed_files and not cfg.quiet:
        print(f"{cfg.indent}No files were processed.")
    if (cfg.verbose or cfg.show_errors) and skipped_files:
        print_file_errors(media_list, cfg)
    folder_info["processed_files"] = processed_files
    folder_info["skipped_files"] = skipped_files
    folder_info["created_dirs"] = created_dirs


def main() -> None:
    # 1. Get configuration (from args module)
    cfg = get_config()

    # 2. Condition checks
    check_conditions(cfg)

    # 3. Print header
    print_header(cfg)

    # 4. Main processing
    file_list = get_file_list(cfg.source_dir)
    folder_info = get_folder_info(file_list, cfg)
    print_folder_info(folder_info, cfg)

    files = get_media_objects(file_list, folder_info, cfg)
    print_files_info(files, folder_info, cfg)

    if folder_info["valid_files"] == 0:
        print("No valid media files to process. Exiting.")
        sys.exit(0)

    if not prompt_user(folder_info, cfg):
        sys.exit(0)

    process_files(files, folder_info, cfg)

    # 5. Print footer
    print_footer(folder_info, cfg)


if __name__ == "__main__":
    main()
