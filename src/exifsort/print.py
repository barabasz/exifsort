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


def print_templates() -> None:
    """Print all available directory and file templates with examples."""
    indent = "  "

    print(f"\n{colorize('Available Templates', colors.green)}\n")

    # Directory templates
    print(f"{colorize('Directory Templates (-d, --directory-template):', colors.yellow)}")
    dir_templates = [
        ("YYYYMMDD", "20240115", "Compact format (default)"),
        ("YYYY-MM-DD", "2024-01-15", "ISO format with dashes"),
        ("YYYY.MM.DD", "2024.01.15", "Format with dots"),
        ("YYYY_MM_DD", "2024_01_15", "Format with underscores"),
        ("YYYY-MM", "2024-01", "Monthly folders"),
        ("YYYY/MM/DD", "2024/01/15", "Nested year/month/day"),
        ("YYYY/MM", "2024/01", "Nested year/month"),
    ]

    for template, example, description in dir_templates:
        template_str = colorize(f"{template:<20}", colors.cyan)
        example_str = colorize(f"{example:<20}", colors.green)
        print(f"{indent}{template_str} → {example_str} {description}")

    print(f"\n{colorize('File Prefix Templates (-f, --file-template):', colors.yellow)}")
    file_templates = [
        ("YYYYMMDD-HHMMSS", "20240115-143045", "Compact date-time (default)"),
        ("YYYY-MM-DD-HH-MM-SS", "2024-01-15-14-30-45", "Full format with dashes"),
        ("YYYY.MM.DD.HH.MM.SS", "2024.01.15.14.30.45", "Full format with dots"),
        ("YYYYMMDD_HHMMSS", "20240115_143045", "Underscore separator"),
        ("YYYYMMDD", "20240115", "Date only (no time)"),
        ("YYYY-MM-DD", "2024-01-15", "Date only with dashes"),
        ("HHMMSS", "143045", "Time only (use with date folders)"),
        ("YYYYMMDDHHMM", "202401151430", "Without seconds (shorter)"),
        ("YYYY-MM-DD_HH-MM-SS", "2024-01-15_14-30-45", "Mixed separators"),
    ]

    for template, example, description in file_templates:
        template_str = colorize(f"{template:<25}", colors.cyan)
        example_str = colorize(f"{example:<25}", colors.green)
        print(f"{indent}{template_str} → {example_str} {description}")

    print(f"\n{colorize('Example Usage:', colors.yellow)}")
    print(
        f"{indent}exifsort -d {colorize('YYYY-MM-DD', colors.cyan)} -f {colorize('HHMMSS', colors.cyan)} /path/to/photos"
    )
    print(f"{indent}Results in: {colorize('2024-01-15/143045-photo.jpg', colors.green)}\n")


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


def print_check_results(issues: dict[str, list[tuple[str, str]]], cfg: AppConfig) -> None:
    """Print results of file check mode."""
    print(f"{colorize('Invalid files:', colors.yellow)}")

    # Count total issues
    total_issues = sum(len(file_list) for file_list in issues.values())

    if total_issues == 0:
        print(f"{cfg.indent}{colorize('No issues found!', colors.green)} All files are valid.")
        return

    # Print summary
    print(f"{cfg.indent}Found {colorize(str(total_issues), colors.red)} issue(s) in total:\n")

    # Print files with no EXIF data
    if issues["no_exif"]:
        count = len(issues["no_exif"])
        print(f"{cfg.indent}{colorize(f'Files without EXIF date ({count}):', colors.yellow)}")
        for filename, reason in issues["no_exif"]:
            print(f"{cfg.indent}{cfg.indent}{colorize(filename, colors.cyan)}: {reason}")
        print()

    # Print empty files
    if issues["empty"]:
        count = len(issues["empty"])
        print(f"{cfg.indent}{colorize(f'Empty files ({count}):', colors.yellow)}")
        for filename, reason in issues["empty"]:
            print(f"{cfg.indent}{cfg.indent}{colorize(filename, colors.cyan)}: {reason}")
        print()

    # Print non-media files
    if issues["non_media"]:
        count = len(issues["non_media"])
        print(f"{cfg.indent}{colorize(f'Non-media files ({count}):', colors.yellow)}")
        for filename, reason in issues["non_media"]:
            print(f"{cfg.indent}{cfg.indent}{colorize(filename, colors.cyan)}: {reason}")
        print()

    # Print not readable files
    if issues["not_readable"]:
        count = len(issues["not_readable"])
        print(f"{cfg.indent}{colorize(f'Files not readable ({count}):', colors.yellow)}")
        for filename, reason in issues["not_readable"]:
            print(f"{cfg.indent}{cfg.indent}{colorize(filename, colors.cyan)}: {reason}")
        print()

    # Print not writable files
    if issues["not_writable"]:
        count = len(issues["not_writable"])
        print(f"{cfg.indent}{colorize(f'Files not writable ({count}):', colors.yellow)}")
        for filename, reason in issues["not_writable"]:
            print(f"{cfg.indent}{cfg.indent}{colorize(filename, colors.cyan)}: {reason}")
        print()
