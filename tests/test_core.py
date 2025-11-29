"""
Tests for the core functionality of ExifSort.
"""
import dataclasses
from pathlib import Path

import pytest

from exifsort.models import AppConfig, FileItem


# --- Fixtures ---

@pytest.fixture
def base_config(tmp_path: Path) -> AppConfig:
    """
    Returns an AppConfig instance with default settings,
    pointed at a temporary directory.
    """
    return AppConfig(
        source_dir=tmp_path,
        extensions=["jpg", "mp4"],
        quiet=True
    )


# --- Tests ---

def test_config_initialization(base_config):
    """Ensure configuration initializes with expected default values."""
    assert base_config.script_name == "ExifSort"
    assert "jpg" in base_config.extensions
    assert base_config.file_template == "YYYYMMDD-HHMMSS"


def test_file_item_validation_non_existent(base_config):
    """FileItem should be invalid if the file does not exist."""
    non_existent_file = base_config.source_dir / "ghost.jpg"
    
    # Metadata is None because file doesn't exist
    item = FileItem(non_existent_file, base_config, metadata=None)
    
    assert not item.is_valid
    assert "exist" in item.error


def test_file_item_validation_empty_file(base_config):
    """FileItem should be invalid if the file is empty."""
    empty_file = base_config.source_dir / "empty.jpg"
    empty_file.touch()  # Create empty file
    
    # Metadata is None because file is empty/unreadable
    item = FileItem(empty_file, base_config, metadata=None)
    
    assert not item.is_valid
    assert "empty" in item.error or "Metadata not provided" in item.error


@pytest.mark.parametrize("date_str, expected_prefix", [
    ("2023:12:24 18:00:00", "20231224-180000"),
    ("2020:01:01 09:30:15", "20200101-093015"),
])
def test_file_item_naming_logic(
    base_config, 
    date_str, 
    expected_prefix
):
    """
    Test if the new filename is generated correctly based on EXIF date.
    We inject metadata directly, bypassing ExifTool.
    """
    # 1. Setup: Create a dummy file
    dummy_file = base_config.source_dir / "test_photo.jpg"
    dummy_file.write_bytes(b"fake_image_content")
    
    # 2. Mock Metadata
    metadata = {
        "EXIF:DateTimeOriginal": date_str,
        "File:MIMEType": "image/jpeg"
    }
    
    # 3. Execution: Create FileItem with injected metadata
    item = FileItem(dummy_file, base_config, metadata=metadata)
    
    # 4. Assertions
    assert item.is_valid, f"File should be valid. Error: {item.error}"
    assert item.exif_date is not None
    
    # Check if the generated name matches the pattern: PREFIX-name.ext
    expected_name = f"{expected_prefix}-test_photo.jpg"
    assert item.name_new == expected_name


def test_fallback_folder_logic(base_config):
    """
    Test behavior when NO EXIF date is found.
    Should be invalid unless use_fallback_folder is True.
    """
    dummy_file = base_config.source_dir / "nodate.jpg"
    dummy_file.write_bytes(b"content")

    # Mock returning metadata WITHOUT date tags
    metadata = {
        "File:MIMEType": "image/jpeg"
        # No DateTimeOriginal here
    }

    # Case A: Default behavior (use_fallback_folder=True in AppConfig default)
    config_no_fallback = dataclasses.replace(base_config, use_fallback_folder=False)

    item = FileItem(dummy_file, config_no_fallback, metadata=metadata)
    assert not item.is_valid
    assert "No EXIF date" in item.error

    # Case B: Fallback enabled (default in base_config)
    item_fallback = FileItem(dummy_file, base_config, metadata=metadata)

    # Now it should be valid but point to fallback folder
    assert item_fallback.is_valid
    assert item_fallback.subdir == base_config.fallback_folder


def test_file_item_not_readable(base_config):
    """Test FileItem validation for non-readable files."""
    import os
    import stat

    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    # Remove read permission
    os.chmod(test_file, stat.S_IWRITE)

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00"}
    item = FileItem(test_file, base_config, metadata=metadata)

    # Restore permissions for cleanup
    os.chmod(test_file, stat.S_IREAD | stat.S_IWRITE)

    assert not item.is_valid
    assert "not readable" in item.error


def test_file_item_not_writable(base_config):
    """Test FileItem validation for non-writable files."""
    import os
    import stat

    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    # Remove write permission
    os.chmod(test_file, stat.S_IREAD)

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00"}
    item = FileItem(test_file, base_config, metadata=metadata)

    # Restore permissions for cleanup
    os.chmod(test_file, stat.S_IREAD | stat.S_IWRITE)

    assert not item.is_valid
    assert "not writable" in item.error


def test_file_item_exif_date_extraction_priority(base_config):
    """Test that EXIF date is extracted in correct priority order."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    # Test priority: EXIF:DateTimeOriginal > EXIF:CreateDate
    metadata1 = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "EXIF:CreateDate": "2023:12:31 10:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item1 = FileItem(test_file, base_config, metadata=metadata1)
    assert "20240101-120000" in item1.name_new

    # Test fallback to CreateDate when DateTimeOriginal is missing
    metadata2 = {
        "EXIF:CreateDate": "2023:12:31 10:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item2 = FileItem(test_file, base_config, metadata=metadata2)
    assert "20231231-100000" in item2.name_new


def test_file_item_xmp_createdate(base_config):
    """Test extraction of XMP:CreateDate."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "XMP:CreateDate": "2024:02:15 14:30:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, base_config, metadata=metadata)

    assert item.is_valid
    assert "20240215-143000" in item.name_new


def test_file_item_quicktime_createdate(base_config):
    """Test extraction of QuickTime:CreateDate."""
    test_file = base_config.source_dir / "test.mp4"
    test_file.write_bytes(b"content")

    metadata = {
        "QuickTime:CreateDate": "2024:03:20 16:45:00",
        "File:MIMEType": "video/mp4"
    }
    item = FileItem(test_file, base_config, metadata=metadata)

    assert item.is_valid
    assert "20240320-164500" in item.name_new


def test_file_item_time_offset(base_config):
    """Test time offset is applied correctly."""
    config_with_offset = dataclasses.replace(base_config, offset=3600)  # +1 hour

    test_file = config_with_offset.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_with_offset, metadata=metadata)

    # Should be 13:00:00 after +1 hour offset
    assert "20240101-130000" in item.name_new


def test_file_item_party_mode(base_config):
    """Test party mode (day shift) logic."""
    config_party = dataclasses.replace(base_config, time_day_starts="04:00:00")

    test_file = config_party.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    # Photo taken at 02:00 AM (before 04:00) should belong to previous day
    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:02 02:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_party, metadata=metadata)

    # Should be in 20240101 folder, not 20240102
    assert item.subdir == "20240101"


def test_file_item_extension_normalization(base_config):
    """Test extension normalization to lowercase."""
    config_normalize = dataclasses.replace(base_config, normalize_ext=True)

    test_file = config_normalize.source_dir / "test.JPG"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_normalize, metadata=metadata)

    assert item.ext_new == "jpg"
    assert item.name_new.endswith(".jpg")


def test_file_item_extension_no_normalization(base_config):
    """Test that extension normalization can be disabled."""
    config_no_normalize = dataclasses.replace(base_config, normalize_ext=False)

    test_file = config_no_normalize.source_dir / "test.JPG"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_no_normalize, metadata=metadata)

    assert item.ext_new == "JPG"


def test_file_item_extension_change(base_config):
    """Test extension change mapping (jpeg -> jpg)."""
    test_file = base_config.source_dir / "test.jpeg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }

    # Add jpeg to extensions
    config = dataclasses.replace(base_config, extensions=("jpg", "jpeg"))
    item = FileItem(test_file, config, metadata=metadata)

    assert item.ext_new == "jpg"
    assert item.name_new.endswith(".jpg")


def test_file_item_no_prefix(base_config):
    """Test file naming without prefix."""
    config_no_prefix = dataclasses.replace(base_config, use_prefix=False)

    test_file = config_no_prefix.source_dir / "vacation.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_no_prefix, metadata=metadata)

    assert item.name_new == "vacation.jpg"
    assert not item.prefix


def test_file_item_with_interfix(base_config):
    """Test file naming with interfix."""
    config_interfix = dataclasses.replace(base_config, interfix="holiday")

    test_file = config_interfix.source_dir / "beach.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_interfix, metadata=metadata)

    assert "holiday" in item.name_new
    assert "20240101-120000-holiday-beach.jpg" == item.name_new


def test_file_item_prefix_with_dashes(base_config):
    """Test file prefix format with dashes (YYYY-MM-DD-HH-MM-SS)."""
    config_dashes = dataclasses.replace(base_config, file_template="YYYY-MM-DD-HH-MM-SS")

    test_file = config_dashes.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_dashes, metadata=metadata)

    assert item.prefix == "2024-01-15-14-30-45"
    assert "2024-01-15-14-30-45-test.jpg" == item.name_new


def test_file_item_prefix_with_dots(base_config):
    """Test file prefix format with dots (YYYY.MM.DD.HH.MM.SS)."""
    config_dots = dataclasses.replace(base_config, file_template="YYYY.MM.DD.HH.MM.SS")

    test_file = config_dots.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_dots, metadata=metadata)

    assert item.prefix == "2024.01.15.14.30.45"
    assert "2024.01.15.14.30.45-test.jpg" == item.name_new


def test_file_item_prefix_with_underscore(base_config):
    """Test file prefix format with underscore (YYYYMMDD_HHMMSS)."""
    config_underscore = dataclasses.replace(base_config, file_template="YYYYMMDD_HHMMSS")

    test_file = config_underscore.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_underscore, metadata=metadata)

    assert item.prefix == "20240115_143045"
    assert "20240115_143045-test.jpg" == item.name_new


def test_file_item_prefix_date_only(base_config):
    """Test file prefix with date only (YYYYMMDD)."""
    config_date_only = dataclasses.replace(base_config, file_template="YYYYMMDD")

    test_file = config_date_only.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_date_only, metadata=metadata)

    assert item.prefix == "20240115"
    assert "20240115-test.jpg" == item.name_new


def test_file_item_prefix_date_only_dashes(base_config):
    """Test file prefix with date only and dashes (YYYY-MM-DD)."""
    config_date_dashes = dataclasses.replace(base_config, file_template="YYYY-MM-DD")

    test_file = config_date_dashes.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_date_dashes, metadata=metadata)

    assert item.prefix == "2024-01-15"
    assert "2024-01-15-test.jpg" == item.name_new


def test_file_item_prefix_time_only(base_config):
    """Test file prefix with time only (HHMMSS)."""
    config_time_only = dataclasses.replace(base_config, file_template="HHMMSS")

    test_file = config_time_only.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_time_only, metadata=metadata)

    assert item.prefix == "143045"
    assert "143045-test.jpg" == item.name_new


def test_file_item_prefix_no_seconds(base_config):
    """Test file prefix without seconds (YYYYMMDDHHMM)."""
    config_no_seconds = dataclasses.replace(base_config, file_template="YYYYMMDDHHMM")

    test_file = config_no_seconds.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_no_seconds, metadata=metadata)

    assert item.prefix == "202401151430"
    assert "202401151430-test.jpg" == item.name_new


def test_file_item_prefix_mixed_separators(base_config):
    """Test file prefix with mixed separators (YYYY-MM-DD_HH-MM-SS)."""
    config_mixed = dataclasses.replace(base_config, file_template="YYYY-MM-DD_HH-MM-SS")

    test_file = config_mixed.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 14:30:45",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_mixed, metadata=metadata)

    assert item.prefix == "2024-01-15_14-30-45"
    assert "2024-01-15_14-30-45-test.jpg" == item.name_new


def test_file_item_directory_template_with_dashes(base_config):
    """Test directory template with dashes."""
    config_dashes = dataclasses.replace(base_config, directory_template="YYYY-MM-DD")

    test_file = config_dashes.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_dashes, metadata=metadata)

    assert item.subdir == "2024-01-15"


def test_file_item_directory_template_with_dots(base_config):
    """Test directory template with dots (YYYY.MM.DD)."""
    config_dots = dataclasses.replace(base_config, directory_template="YYYY.MM.DD")

    test_file = config_dots.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_dots, metadata=metadata)

    assert item.subdir == "2024.01.15"


def test_file_item_directory_template_with_underscores(base_config):
    """Test directory template with underscores (YYYY_MM_DD)."""
    config_underscores = dataclasses.replace(base_config, directory_template="YYYY_MM_DD")

    test_file = config_underscores.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_underscores, metadata=metadata)

    assert item.subdir == "2024_01_15"


def test_file_item_directory_template_month_only(base_config):
    """Test directory template with month only (YYYY-MM)."""
    config_month = dataclasses.replace(base_config, directory_template="YYYY-MM")

    test_file = config_month.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_month, metadata=metadata)

    assert item.subdir == "2024-01"


def test_file_item_directory_template_nested_year_month_day(base_config):
    """Test directory template with nested folders (YYYY/MM/DD)."""
    config_nested = dataclasses.replace(base_config, directory_template="YYYY/MM/DD")

    test_file = config_nested.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_nested, metadata=metadata)

    assert item.subdir == "2024/01/15"


def test_file_item_directory_template_nested_year_month(base_config):
    """Test directory template with nested folders (YYYY/MM)."""
    config_nested = dataclasses.replace(base_config, directory_template="YYYY/MM")

    test_file = config_nested.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:15 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_nested, metadata=metadata)

    assert item.subdir == "2024/01"


def test_file_item_no_subdirs(base_config):
    """Test file path when subdirectories are disabled."""
    config_no_subdirs = dataclasses.replace(base_config, use_subdirs=False)

    test_file = config_no_subdirs.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config_no_subdirs, metadata=metadata)

    assert item.subdir is None
    assert item.path_new.parent == config_no_subdirs.source_dir


def test_file_item_exif_type_extraction(base_config):
    """Test EXIF type extraction."""
    test_file = base_config.source_dir / "test.mp4"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "video/mp4"
    }
    item = FileItem(test_file, base_config, metadata=metadata)

    assert item.exif_type == "video/mp4"
    assert item.type == "video"


def test_file_item_invalid_date_format(base_config):
    """Test handling of invalid date format."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "invalid-date",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, base_config, metadata=metadata)

    # Invalid date format should result in no EXIF date being found
    # With fallback enabled (default), file should still be valid but go to fallback folder
    assert item.is_valid
    assert item.subdir == base_config.fallback_folder


def test_appconfig_print_config(base_config, capsys):
    """Test AppConfig print_config method."""
    base_config.print_config(show_all=False)
    captured = capsys.readouterr()

    assert "RAW Settings:" in captured.out
    assert "extensions" in captured.out


def test_colorize():
    """Test colorize function."""
    from exifsort.models import colorize, colors

    result = colorize("test", colors.red)
    assert "\033[31m" in result  # red color code
    assert "test" in result
    assert "\033[0m" in result  # reset code


def test_get_unique_path_no_conflict(base_config):
    """Test get_unique_path returns original path when no conflict."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"File:MIMEType": "image/jpeg"}
    item = FileItem(test_file, base_config, metadata=metadata)

    # File going to fallback folder
    assert item.subdir == base_config.fallback_folder

    original_path = item.path_new
    unique_path = item.get_unique_path(original_path)

    assert unique_path == original_path


def test_get_unique_path_with_conflict(base_config):
    """Test get_unique_path generates unique name when conflict exists."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"File:MIMEType": "image/jpeg"}
    item = FileItem(test_file, base_config, metadata=metadata)

    # Create the fallback folder and a conflicting file
    fallback_dir = base_config.source_dir / base_config.fallback_folder
    fallback_dir.mkdir()
    conflicting_file = fallback_dir / item.name_new
    conflicting_file.write_bytes(b"existing")

    original_path = item.path_new
    unique_path = item.get_unique_path(original_path)

    # Should generate name with _1 suffix
    assert unique_path != original_path
    assert "_1" in unique_path.name
    assert not unique_path.exists()
    assert item.name_new == unique_path.name


def test_get_unique_path_multiple_conflicts(base_config):
    """Test get_unique_path handles multiple conflicts."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"File:MIMEType": "image/jpeg"}
    item = FileItem(test_file, base_config, metadata=metadata)

    # Create fallback folder and multiple conflicting files
    fallback_dir = base_config.source_dir / base_config.fallback_folder
    fallback_dir.mkdir()

    # Create original and _1, _2 versions
    (fallback_dir / item.name_new).write_bytes(b"existing")
    (fallback_dir / item.name_new.replace(".jpg", "_1.jpg")).write_bytes(b"existing")
    (fallback_dir / item.name_new.replace(".jpg", "_2.jpg")).write_bytes(b"existing")

    original_path = item.path_new
    unique_path = item.get_unique_path(original_path)

    # Should generate name with _3 suffix
    assert "_3" in unique_path.name
    assert not unique_path.exists()


def test_get_unique_path_non_fallback_folder(base_config):
    """Test get_unique_path does nothing for non-fallback folders."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, base_config, metadata=metadata)

    # File going to dated folder, not fallback
    assert item.subdir != base_config.fallback_folder

    # Create the target directory and a conflicting file
    target_dir = base_config.source_dir / item.subdir
    target_dir.mkdir()
    conflicting_file = target_dir / item.name_new
    conflicting_file.write_bytes(b"existing")

    original_path = item.path_new
    unique_path = item.get_unique_path(original_path)

    # Should return original path unchanged (not in fallback folder)
    assert unique_path == original_path
