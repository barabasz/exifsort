"""
Tests for the core functionality of ExifSort.
"""
import datetime
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tyconf import TyConf

from exifsort.core import init_config
from exifsort.models import FileItem

# --- Fixtures ---

@pytest.fixture
def base_config(tmp_path: Path) -> TyConf:
    """
    Returns a TyConf instance with default settings,
    pointed at a temporary directory.
    """
    cfg = init_config()
    # Override source directory to use the pytest temporary path
    cfg.source_dir = tmp_path
    # Ensure extensions match what we create in tests
    cfg.extensions = ["jpg", "mp4"]
    # Disable console output for cleaner test runs
    cfg.quiet = True
    return cfg


@pytest.fixture
def mock_exiftool():
    """
    Mocks the ExifToolHelper to avoid needing the external binary
    and real image files during unit tests.
    """
    with patch("exifsort.models.exiftool.ExifToolHelper") as MockHelper:
        # Mock context manager (__enter__ and __exit__)
        instance = MockHelper.return_value
        instance.__enter__.return_value = instance
        instance.__exit__.return_value = None
        yield instance


# --- Tests ---

def test_config_initialization():
    """Ensure configuration initializes with expected default values."""
    cfg = init_config()
    assert cfg.script_name == "exifsort"
    assert "jpg" in cfg.extensions
    assert cfg.file_template == "YYYYMMDD-HHMMSS"


def test_file_item_validation_non_existent(base_config):
    """FileItem should be invalid if the file does not exist."""
    non_existent_file = base_config.source_dir / "ghost.jpg"
    
    item = FileItem(non_existent_file, base_config)
    
    assert not item.is_valid
    assert "exist" in item.error


def test_file_item_validation_empty_file(base_config):
    """FileItem should be invalid if the file is empty."""
    empty_file = base_config.source_dir / "empty.jpg"
    empty_file.touch()  # Create empty file
    
    item = FileItem(empty_file, base_config)
    
    assert not item.is_valid
    assert "empty" in item.error


@pytest.mark.parametrize("date_str, expected_prefix", [
    ("2023:12:24 18:00:00", "20231224-180000"),
    ("2020:01:01 09:30:15", "20200101-093015"),
])
def test_file_item_naming_logic(
    base_config, 
    mock_exiftool, 
    date_str, 
    expected_prefix
):
    """
    Test if the new filename is generated correctly based on EXIF date.
    Uses mocking to simulate EXIF data.
    """
    # 1. Setup: Create a dummy file
    dummy_file = base_config.source_dir / "test_photo.jpg"
    # Write some bytes so it's not empty (validation passes)
    dummy_file.write_bytes(b"fake_image_content")
    
    # 2. Mock: Configure ExifTool to return specific metadata
    # The list is because get_metadata returns a list of dicts (one per file)
    mock_exiftool.get_metadata.return_value = [{
        "EXIF:DateTimeOriginal": date_str,
        "File:MIMEType": "image/jpeg"
    }]
    
    # 3. Execution: Create FileItem
    item = FileItem(dummy_file, base_config)
    
    # 4. Assertions
    assert item.is_valid, f"File should be valid. Error: {item.error}"
    assert item.exif_date is not None
    
    # Check if the generated name matches the pattern: PREFIK-nazwa.ext
    # Default template is YYYYMMDD-HHMMSS
    expected_name = f"{expected_prefix}-test_photo.jpg"
    assert item.name_new == expected_name


def test_fallback_folder_logic(base_config, mock_exiftool):
    """
    Test behavior when NO EXIF date is found.
    Should be invalid unless use_fallback_folder is True.
    """
    dummy_file = base_config.source_dir / "nodate.jpg"
    dummy_file.write_bytes(b"content")
    
    # Mock returning metadata WITHOUT date tags
    mock_exiftool.get_metadata.return_value = [{
        "File:MIMEType": "image/jpeg"
        # No DateTimeOriginal here
    }]
    
    # Case A: Default behavior (invalid if no date)
    base_config.use_fallback_folder = False
    item = FileItem(dummy_file, base_config)
    assert not item.is_valid
    assert "No EXIF date" in item.error
    
    # Case B: Fallback enabled
    base_config.use_fallback_folder = True
    # Re-create item logic
    item_fallback = FileItem(dummy_file, base_config)
    
    # Now it should be valid but point to fallback folder
    assert item_fallback.is_valid
    assert item_fallback.subdir == base_config.fallback_folder