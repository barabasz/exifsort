"""
Output logic for ExifSort.
"""

import sys
import time
from typing import Any

from exifsort.models import AppConfig, FileItem, colorize, colors


def get_schema(cfg: AppConfig) -> str:
    """Get schema string based on current configuration."""
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


def get_status(value: bool) -> str:
    """Get colored ON/OFF status."""
    return colorize("ON", colors.green) if value else colorize("OFF", colors.red)


def get_elapsed_time(start_time: float) -> tuple[str, str]:
    """Get elapsed time since script start."""
    elapsed_time = (time.time() - start_time) * 1000
    time_factor = "ms" if elapsed_time < 1000 else "s"
    elapsed_time = elapsed_time / 1000 if elapsed_time >= 1000 else elapsed_time
    return f"{elapsed_time:.2f}", time_factor


def print_schema(cfg: AppConfig) -> None:
    """Print the schema based on current configuration."""
    print(f"{colorize('Schema:', colors.yellow)}")
    print(f"{cfg.indent}{get_schema(cfg)}")


def print_progress(
    item: int, total: int, message: str, cfg: AppConfig, show_percentage: bool = True
) -> None:
    """Print progress of file processing."""
    if show_percentage:
        percentage = (item / total) * 100 if total > 0 else 0
        msg = (
            f"{cfg.terminal_clear}{cfg.indent}File {item} of {total}: {message} ({percentage:.0f}%)"
        )
    else:
        msg = f"{cfg.terminal_clear}{cfg.indent}File {item} of {total}: {message}"
    print(msg, end="", flush=True)


def printe(message: str, exit_code: int = 1) -> None:
    """Print error message and exit with given exit code."""
    msg = message if exit_code == 0 else f"{colorize('Error', colors.red)}: {message}"
    print(msg)
    sys.exit(exit_code)


def print_settings(cfg: AppConfig) -> None:
    """Print settings using AppConfig internal method."""
    cfg.print_config(show_all=False)


def print_header(cfg: AppConfig) -> None:
    """Print the header information based on current configuration."""
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


def print_footer(folder_info: dict[str, Any], cfg: AppConfig) -> None:
    """Print the footer summary based on folder information and configuration."""
    time_elapsed, time_factor = get_elapsed_time(cfg.start_time)
    print(f"{colorize('Summary:', colors.yellow)}")
    if cfg.test:
        print(f"{cfg.indent}Test mode (no changes made).")
    else:
        print(f"{cfg.indent}Processed files: {len(folder_info['processed_files'])}")
        print(f"{cfg.indent}Skipped files: {len(folder_info['skipped_files'])}")
        print(f"{cfg.indent}Directories created: {len(folder_info['created_dirs'])}")
    print(f"{cfg.indent}Completed in: {colorize(time_elapsed, colors.cyan)} {time_factor}.")


def print_folder_info(folder_info: dict[str, Any], cfg: AppConfig) -> None:
    """Print folder information based on folder info and configuration."""
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
    """Print errors for files based on their validity and error status."""
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
    """Print files information based on their validity and configuration."""
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
    """Print detailed information about a single file."""
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
    """Print processing information for a single file."""
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
