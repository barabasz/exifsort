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
