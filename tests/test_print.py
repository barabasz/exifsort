"""
Tests for output formatting in print.py
"""
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from exifsort.models import AppConfig, FileItem
from exifsort.print import (
    get_elapsed_time,
    get_schema,
    get_status,
    print_check_results,
    print_file_errors,
    print_file_info,
    print_files_info,
    print_folder_info,
    print_footer,
    print_header,
    print_process_file,
    print_progress,
    print_schema,
    print_settings,
    print_templates,
    printe,
)


@pytest.fixture
def base_config(tmp_path: Path) -> AppConfig:
    """Provide base AppConfig for tests."""
    return AppConfig(source_dir=tmp_path, extensions=["jpg"], quiet=False)


def test_get_status():
    """Test get_status returns colored ON/OFF strings."""
    assert "ON" in get_status(True)
    assert "OFF" in get_status(False)


def test_get_elapsed_time():
    """Test elapsed time calculation."""
    start_time = time.time() - 0.5  # 500ms ago
    elapsed, factor = get_elapsed_time(start_time)

    assert factor == "ms"
    assert float(elapsed) >= 500
    assert float(elapsed) < 600


def test_get_elapsed_time_seconds():
    """Test elapsed time in seconds."""
    start_time = time.time() - 2.0  # 2 seconds ago
    elapsed, factor = get_elapsed_time(start_time)

    assert factor == "s"
    assert float(elapsed) >= 2.0
    assert float(elapsed) < 3.0


def test_print_templates(capsys):
    """Test templates printing."""
    print_templates()
    output = capsys.readouterr().out

    # Check for main sections
    assert "Available Templates" in output
    assert "Directory Templates" in output
    assert "File Prefix Templates" in output

    # Check for some directory templates
    assert "YYYYMMDD" in output
    assert "YYYY-MM-DD" in output
    assert "YYYY.MM.DD" in output
    assert "YYYY/MM/DD" in output

    # Check for some file templates
    assert "YYYYMMDD-HHMMSS" in output
    assert "YYYY-MM-DD-HH-MM-SS" in output
    assert "HHMMSS" in output

    # Check for examples
    assert "20240115" in output
    assert "2024-01-15" in output
    assert "Example Usage" in output


def test_get_schema_default(base_config):
    """Test schema generation with default settings."""
    schema = get_schema(base_config)

    assert "FileName.Ext" in schema
    assert "→" in schema
    assert "YYYYMMDD" in schema
    assert "/" in schema  # subdirectory separator


def test_get_schema_no_subdirs(base_config):
    """Test schema without subdirectories."""
    import dataclasses

    config = dataclasses.replace(base_config, use_subdirs=False)
    schema = get_schema(config)

    assert "FileName.Ext" in schema
    # Should not have subdirectory part
    assert schema.count("/") == 0


def test_get_schema_no_prefix(base_config):
    """Test schema without prefix."""
    import dataclasses

    config = dataclasses.replace(base_config, use_prefix=False)
    schema = get_schema(config)

    assert "FileName.Ext" in schema
    # After the arrow, we should have folder/filename without the timestamp prefix
    after_arrow = schema.split("→")[1]
    # Should have filename.ext but not as part of a prefix-filename.ext pattern
    assert "filename.ext" in after_arrow.lower()


def test_get_schema_with_interfix(base_config):
    """Test schema with interfix."""
    import dataclasses

    config = dataclasses.replace(base_config, interfix="vacation")
    schema = get_schema(config)

    assert "vacation" in schema


def test_print_schema(base_config, capsys):
    """Test schema printing."""
    print_schema(base_config)
    output = capsys.readouterr().out

    assert "Schema:" in output
    assert "FileName.Ext" in output


def test_print_progress(base_config, capsys):
    """Test progress printing with percentage."""
    print_progress(5, 10, "test.jpg", base_config, show_percentage=True)
    output = capsys.readouterr().out

    assert "5 of 10" in output
    assert "test.jpg" in output
    assert "50%" in output


def test_print_progress_no_percentage(base_config, capsys):
    """Test progress printing without percentage."""
    print_progress(3, 10, "test.jpg", base_config, show_percentage=False)
    output = capsys.readouterr().out

    assert "3 of 10" in output
    assert "test.jpg" in output
    assert "%" not in output


def test_printe_with_error():
    """Test printe exits with error code and message."""
    with pytest.raises(SystemExit) as exc_info:
        printe("Something went wrong", 1)

    assert exc_info.value.code == 1


def test_printe_with_success():
    """Test printe can exit with code 0."""
    with pytest.raises(SystemExit) as exc_info:
        printe("Success message", 0)

    assert exc_info.value.code == 0


def test_print_settings(base_config, capsys):
    """Test settings printing."""
    print_settings(base_config)
    output = capsys.readouterr().out

    assert "RAW Settings:" in output


def test_print_header(base_config, capsys):
    """Test header printing."""
    print_header(base_config)
    output = capsys.readouterr().out

    assert "Media Organizer Script" in output
    assert "Schema:" in output
    assert "Settings:" in output


def test_print_header_quiet(capsys):
    """Test header printing in quiet mode."""
    config = AppConfig(quiet=True)
    print_header(config)
    output = capsys.readouterr().out

    assert "Schema:" in output
    # Quiet mode should suppress settings
    assert "Settings:" not in output or output.count("Settings:") == 1


def test_print_header_verbose(base_config, capsys):
    """Test header printing in verbose mode."""
    import dataclasses

    config = dataclasses.replace(base_config, verbose=True)
    print_header(config)
    output = capsys.readouterr().out

    assert "Verbose mode:" in output


def test_print_header_test_mode(base_config, capsys):
    """Test header printing in test mode."""
    import dataclasses

    config = dataclasses.replace(base_config, test=True)
    print_header(config)
    output = capsys.readouterr().out

    assert "Test mode:" in output


def test_print_folder_info(base_config, capsys):
    """Test folder info printing."""
    folder_info = {
        "path": base_config.source_dir,
        "file_count": 10,
        "media_count": 7,
        "media_types": {"jpg": 5, "mp4": 2},
        "created": "2024-01-01 12:00:00",
        "modified": "2024-01-02 14:00:00",
    }

    print_folder_info(folder_info, base_config)
    output = capsys.readouterr().out

    assert "Folder info:" in output
    assert "Path:" in output
    assert "Total files: " in output
    assert "10" in output
    assert "Matching files: " in output
    assert "7" in output


def test_print_folder_info_verbose(base_config, capsys):
    """Test folder info printing in verbose mode."""
    import dataclasses

    config = dataclasses.replace(base_config, verbose=True)
    folder_info = {
        "path": config.source_dir,
        "file_count": 10,
        "media_count": 7,
        "media_types": {"jpg": 5, "mp4": 2},
        "created": "2024-01-01 12:00:00",
        "modified": "2024-01-02 14:00:00",
    }

    print_folder_info(folder_info, config)
    output = capsys.readouterr().out

    assert "JPG" in output
    assert "MP4" in output
    assert "Created:" in output
    assert "Modified:" in output


def test_print_footer(base_config, capsys):
    """Test footer printing."""
    folder_info = {"processed_files": ["a.jpg", "b.jpg"], "skipped_files": [], "created_dirs": ["20240101"]}

    print_footer(folder_info, base_config)
    output = capsys.readouterr().out

    assert "Summary:" in output
    assert "Processed files: 2" in output
    assert "Skipped files: 0" in output
    assert "Directories created: 1" in output
    assert "Completed in:" in output


def test_print_footer_test_mode(base_config, capsys):
    """Test footer in test mode."""
    import dataclasses

    config = dataclasses.replace(base_config, test=True)
    folder_info = {"processed_files": [], "skipped_files": [], "created_dirs": []}

    print_footer(folder_info, config)
    output = capsys.readouterr().out

    assert "Test mode (no changes made)" in output


def test_print_file_info(base_config, capsys):
    """Test file info printing."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"fake_content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, base_config, metadata)

    print_file_info(file_item, base_config)
    output = capsys.readouterr().out

    assert "File:" in output
    assert "test.jpg" in output


def test_print_files_info(base_config, capsys):
    """Test files summary info printing."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"fake_content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, base_config, metadata)

    folder_info = {}
    print_files_info([file_item], folder_info, base_config)
    output = capsys.readouterr().out

    assert "Files Summary:" in output
    # Check for the values, not exact strings (due to color codes)
    assert "1" in output
    assert "Total files analyzed" in output
    assert "Valid files" in output
    assert "Invalid files" in output
    assert folder_info["valid_files"] == 1
    assert folder_info["invalid_files"] == 0


def test_print_files_info_quiet(base_config, capsys):
    """Test files info in quiet mode."""
    import dataclasses

    config = dataclasses.replace(base_config, quiet=True)
    folder_info = {}

    print_files_info([], folder_info, config)
    output = capsys.readouterr().out

    # Should not print in quiet mode
    assert output == ""


def test_print_file_errors(base_config, capsys):
    """Test printing file errors."""
    invalid_file = base_config.source_dir / "invalid.jpg"
    # Don't create the file so it's invalid

    file_item = FileItem(invalid_file, base_config, metadata=None)

    print_file_errors([file_item], base_config)
    output = capsys.readouterr().out

    assert "Files not valid:" in output
    assert "invalid.jpg" in output


def test_print_file_errors_with_valid_but_errored(base_config, capsys):
    """Test printing errors for files that are valid but had processing errors."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"fake_content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, base_config, metadata)
    file_item.error = "Target file already exists."

    print_file_errors([file_item], base_config)
    output = capsys.readouterr().out

    assert "Files with errors:" in output
    assert "test.jpg" in output
    assert "already exists" in output


def test_print_process_file_verbose(base_config, capsys):
    """Test process file printing in verbose mode."""
    import dataclasses

    config = dataclasses.replace(base_config, verbose=True, use_subdirs=True)

    test_file = config.source_dir / "test.jpg"
    test_file.write_bytes(b"fake_content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, config, metadata)

    print_process_file(file_item, 1, 10, config)
    output = capsys.readouterr().out

    assert "test.jpg" in output
    assert "→" in output


def test_print_process_file_non_verbose(base_config, capsys):
    """Test process file printing in non-verbose mode."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"fake_content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, base_config, metadata)

    print_process_file(file_item, 5, 10, base_config)
    output = capsys.readouterr().out

    assert "5 of 10" in output


def test_print_check_results_no_issues(base_config, capsys):
    """Test print_check_results with no issues."""
    issues = {
        "no_exif": [],
        "empty": [],
        "non_media": [],
        "not_readable": [],
        "not_writable": [],
    }

    print_check_results(issues, base_config)
    output = capsys.readouterr().out

    assert "Invalid files:" in output
    assert "No issues found!" in output


def test_print_check_results_with_no_exif(base_config, capsys):
    """Test print_check_results with files missing EXIF."""
    issues = {
        "no_exif": [("file1.jpg", "No EXIF date found"), ("file2.jpg", "Metadata not provided")],
        "empty": [],
        "non_media": [],
        "not_readable": [],
        "not_writable": [],
    }

    print_check_results(issues, base_config)
    output = capsys.readouterr().out

    assert "Invalid files:" in output
    assert "Files without EXIF date (2):" in output
    assert "file1.jpg" in output
    assert "file2.jpg" in output
    assert "No EXIF date found" in output


def test_print_check_results_with_empty_files(base_config, capsys):
    """Test print_check_results with empty files."""
    issues = {
        "no_exif": [],
        "empty": [("empty.jpg", "File is empty (0 bytes)")],
        "non_media": [],
        "not_readable": [],
        "not_writable": [],
    }

    print_check_results(issues, base_config)
    output = capsys.readouterr().out

    assert "Empty files (1):" in output
    assert "empty.jpg" in output
    assert "empty" in output.lower()


def test_print_check_results_multiple_issues(base_config, capsys):
    """Test print_check_results with multiple issue types."""
    issues = {
        "no_exif": [("noexif.jpg", "No EXIF date found")],
        "empty": [("empty.jpg", "File is empty (0 bytes)")],
        "non_media": [("unknown.dat", "File type could not be determined")],
        "not_readable": [],
        "not_writable": [],
    }

    print_check_results(issues, base_config)
    output = capsys.readouterr().out

    assert "Invalid files:" in output
    assert "issue(s) in total" in output  # Don't check exact number due to color codes
    assert "3" in output  # Check the number is there
    assert "Files without EXIF date (1):" in output
    assert "Empty files (1):" in output
    assert "Non-media files (1):" in output
    assert "noexif.jpg" in output
    assert "empty.jpg" in output
    assert "unknown.dat" in output
