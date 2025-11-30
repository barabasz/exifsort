#!/usr/bin/env python3
"""
Sort media files into date-based folders by reading EXIF creation date.
Requires: ExifTool command-line tool and PyExifTool Python library.
"""

import datetime
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import exiftool

from exifsort.args import get_config
from exifsort.models import AppConfig, FileItem, colorize, colors, get_normalized_extension
from exifsort.print import (
    print_file_errors,
    print_file_info,
    print_files_info,
    print_folder_info,
    print_footer,
    print_header,
    print_process_file,
    print_progress,
    printe,
)


def skip_file_with_error(file: FileItem, error: str, skipped_files: list[str]) -> None:
    """
    Mark file as skipped with error message.

    Args:
        file: FileItem to mark as skipped
        error: Error message to set
        skipped_files: List to append filename to
    """
    file.error = error
    skipped_files.append(file.name_old)


def check_exiftool_availability() -> None:
    """Check if ExifTool command-line tool is available."""
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("\033[0;31mExifTool command-line tool is not installed or not in PATH.\033[0m")
        print("Please download and install it from: \033[0;36mhttps://exiftool.org/\033[0m")
        sys.exit(1)


def check_conditions(cfg: AppConfig) -> None:
    """Check if all conditions are met to run the script."""
    check_exiftool_availability()

    # Show version and exit when requested with --version
    if cfg.show_version:
        date_str = f" ({cfg.script_date})" if cfg.script_date else ""
        msg = (
            f"{colorize(cfg.script_name, colors.green)} "
            f"version {colorize(cfg.script_version, colors.cyan)}{date_str} "
            f"by {colorize(cfg.script_author, colors.cyan)}"
        )
        printe(msg, 0)

    # Show templates and exit when requested with --templates
    if cfg.show_templates:
        from exifsort.print import print_templates

        print_templates()
        sys.exit(0)

    # Exit if source directory does not exist or is not writable
    if not cfg.source_dir.is_dir():
        printe(
            f"The specified directory '{colorize(str(cfg.source_dir), colors.cyan)}' does not exist or is not a directory.",
            1,
        )

    # Exit if source directory is not writable
    if not cfg.source_dir_writable:
        printe(
            f"The specified directory '{colorize(str(cfg.source_dir), colors.cyan)}' is not writable.",
            1,
        )

    # Validate extensions list specified by user
    if not cfg.extensions or all(ext.strip() == "" for ext in cfg.extensions):
        printe("At least one file extension must be specified.", 1)

    # Check for conflicting quiet and verbose modes
    if cfg.quiet and cfg.verbose:
        printe("Cannot use both quiet mode and verbose mode.", 1)


def prompt_user(folder_info: dict[str, Any], cfg: AppConfig) -> bool:
    """Prompt user for confirmation before proceeding."""
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
    media_files = [f for f in file_list if get_normalized_extension(f) in cfg.extensions]

    # Process files with progress
    media_objects = []

    # Run ExifTool once for all files to improve performance
    try:
        with exiftool.ExifToolHelper() as et:
            for item, file in enumerate(media_files, start=1):
                metadata = None
                try:
                    data = et.get_metadata(str(file))
                    if data:
                        metadata = data[0]
                except Exception as e:
                    # Log individual file errors but continue processing
                    if cfg.verbose:
                        print(
                            f"\n{cfg.indent}Warning: Could not read metadata from {file.name}: {str(e)}"
                        )
                    metadata = None

                media_item = FileItem(file, cfg, metadata)

                if cfg.show_files_details and not cfg.quiet:
                    print_file_info(media_item, cfg)
                else:
                    print_progress(
                        item, media_count, colorize(media_item.name_old, colors.cyan), cfg
                    )

                media_objects.append(media_item)

    except Exception as e:
        # Handle critical ExifTool errors
        print(f"\n{colorize('Error:', colors.red)} ExifTool failed: {str(e)}")
        print(f"{cfg.indent}Attempting to continue without metadata...")

        # If ExifTool completely fails, create FileItems without metadata
        for file in media_files:
            if not any(obj.path_old == file for obj in media_objects):
                media_item = FileItem(file, cfg, metadata=None)
                media_objects.append(media_item)

    if not cfg.show_files_details and not cfg.quiet:
        print(f"{cfg.terminal_clear}{cfg.indent}Completed.")

    return media_objects


def get_file_list(directory: Path) -> list[Path]:
    """Get a sorted list of files in the specified directory."""
    files = [directory / file for file in os.listdir(directory) if (directory / file).is_file()]
    return sorted(files, key=lambda x: x.name.lower())


def get_folder_info(file_list: list[Path], cfg: AppConfig) -> dict[str, Any]:
    """Gather information about the folder and its files."""
    info: dict[str, Any] = {
        "path": cfg.source_dir,
        "created": datetime.datetime.fromtimestamp(cfg.source_dir.stat().st_ctime).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "modified": datetime.datetime.fromtimestamp(cfg.source_dir.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "file_count": len(file_list),
        "media_count": sum(1 for f in file_list if get_normalized_extension(f) in cfg.extensions),
        "media_types": {},
        "processed_files": [],
        "skipped_files": [],
        "created_dirs": [],
    }
    for f in file_list:
        ext = get_normalized_extension(f)
        if ext in cfg.extensions:
            info["media_types"][ext] = info["media_types"].get(ext, 0) + 1
    return info


def process_files(media_list: list[FileItem], folder_info: dict[str, Any], cfg: AppConfig) -> None:
    """Process and move/rename media files based on EXIF data."""
    processed_files: list[str] = []
    skipped_files: list[str] = []
    created_dirs: list[str] = []
    total_items = folder_info["valid_files"]
    action = "Moving" if cfg.use_subdirs else "Renaming"

    print(f"{colorize(f'{action} files:', colors.yellow)}")

    for item, file in enumerate((f for f in media_list if f.is_valid), start=1):
        if cfg.use_subdirs and file.subdir:
            target_dir = cfg.source_dir / file.subdir

            if not cfg.test:
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    if file.subdir not in created_dirs:
                        created_dirs.append(file.subdir)
                except PermissionError:
                    skip_file_with_error(
                        file,
                        f"Permission denied: cannot create directory '{file.subdir}'.",
                        skipped_files,
                    )
                    continue
                except OSError as e:
                    skip_file_with_error(
                        file, f"Error creating directory '{file.subdir}': {str(e)}", skipped_files
                    )
                    continue

        # Handle file conflicts
        if file.path_new.exists() and not cfg.overwrite:
            # For fallback folder, generate unique name instead of skipping
            if file.subdir == cfg.fallback_folder:
                try:
                    file.path_new = file.get_unique_path(file.path_new)
                except RuntimeError as e:
                    skip_file_with_error(
                        file, f"Unable to generate unique filename: {str(e)}", skipped_files
                    )
                    continue
            else:
                skip_file_with_error(file, "Target file already exists.", skipped_files)
                continue

        if not cfg.test:
            try:
                file.path_old.rename(file.path_new)
            except PermissionError:
                skip_file_with_error(
                    file, "Permission denied: cannot move or rename file.", skipped_files
                )
                continue
            except FileNotFoundError:
                skip_file_with_error(file, "Source file no longer exists.", skipped_files)
                continue
            except FileExistsError:
                skip_file_with_error(
                    file, "Target file already exists (race condition).", skipped_files
                )
                continue
            except OSError as e:
                skip_file_with_error(file, f"File system error: {str(e)}", skipped_files)
                continue
            except Exception as e:
                skip_file_with_error(file, f"Unexpected error moving file: {str(e)}", skipped_files)
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


def check_files(
    media_list: list[FileItem], folder_info: dict[str, Any], cfg: AppConfig
) -> dict[str, list[tuple[str, str]]]:
    """
    Check files for issues without moving them.

    Returns a dictionary with issue categories and affected files:
    {
        "no_exif": [(filename, reason), ...],
        "empty": [(filename, reason), ...],
        "non_media": [(filename, reason), ...],
    }
    """
    issues: dict[str, list[tuple[str, str]]] = {
        "no_exif": [],
        "empty": [],
        "non_media": [],
        "not_readable": [],
        "not_writable": [],
    }

    total_items = len(media_list)

    print(f"{colorize('Checking files:', colors.yellow)}")

    # Media type patterns
    audio_video_types = ["audio", "video"]

    for item, file in enumerate(media_list, start=1):
        if not cfg.quiet:
            print_progress(item, total_items, colorize(file.name_old, colors.cyan), cfg)

        # Check if file is empty
        if file.path_old.exists() and file.path_old.stat().st_size == 0:
            issues["empty"].append((file.name_old, "File is empty (0 bytes)"))
            continue

        # Check if file is not readable
        if file.path_old.exists() and not os.access(file.path_old, os.R_OK):
            issues["not_readable"].append((file.name_old, "File is not readable"))
            continue

        # Check if file is not writable
        if file.path_old.exists() and not os.access(file.path_old, os.W_OK):
            issues["not_writable"].append((file.name_old, "File is not writable"))
            continue

        # Check if file has no EXIF date
        if not file.is_valid or file.exif_date is None:
            # Check if it's audio/video (which might not have EXIF)
            if hasattr(file, "type") and file.type in audio_video_types:
                # Audio/video without EXIF is acceptable, but note it
                pass
            else:
                reason = file.error if file.error else "No EXIF date found"
                issues["no_exif"].append((file.name_old, reason))
                continue

        # Check if file is not audio/video but lacks proper EXIF
        if hasattr(file, "type") and file.type not in audio_video_types and file.type == "unknown":
            issues["non_media"].append((file.name_old, "File type could not be determined"))

    if not cfg.quiet:
        print(f"{cfg.terminal_clear}{cfg.indent}Completed.")

    folder_info["issues"] = issues
    return issues


def main() -> None:
    """Main function to run the EXIF sorting process."""
    # Get configuration (from args module)
    cfg = get_config()
    # Condition checks
    check_conditions(cfg)
    # Print header
    print_header(cfg)
    # Main processing
    file_list = get_file_list(cfg.source_dir)
    folder_info = get_folder_info(file_list, cfg)
    print_folder_info(folder_info, cfg)

    files = get_media_objects(file_list, folder_info, cfg)
    print_files_info(files, folder_info, cfg)

    # Check mode: validate files and report issues
    if cfg.check_mode:
        issues = check_files(files, folder_info, cfg)
        from exifsort.print import print_check_results

        print_check_results(issues, cfg)
        sys.exit(0)

    if folder_info["valid_files"] == 0:
        print("No valid media files to process. Exiting.")
        sys.exit(0)

    if not prompt_user(folder_info, cfg):
        sys.exit(0)

    process_files(files, folder_info, cfg)

    # Print footer
    print_footer(folder_info, cfg)


if __name__ == "__main__":
    main()
