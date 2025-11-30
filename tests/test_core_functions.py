"""
Tests for core functionality in core.py
"""
import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from exifsort.core import (
    check_conditions,
    check_exiftool_availability,
    check_files,
    get_file_list,
    get_folder_info,
    get_media_objects,
    process_files,
    prompt_user,
)
from exifsort.models import AppConfig, FileItem


@pytest.fixture
def base_config(tmp_path: Path) -> AppConfig:
    """Provide base AppConfig for tests."""
    return AppConfig(source_dir=tmp_path, extensions=["jpg", "mp4"], quiet=True, source_dir_writable=True)


def test_check_exiftool_availability_success():
    """Test that check passes when exiftool is available."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Should not raise
        check_exiftool_availability()
        mock_run.assert_called_once()


def test_check_exiftool_availability_not_found():
    """Test that check exits when exiftool is not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit) as exc_info:
            check_exiftool_availability()
        assert exc_info.value.code == 1


def test_check_exiftool_availability_subprocess_error():
    """Test that check exits on subprocess error."""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError):
        with pytest.raises(SystemExit) as exc_info:
            check_exiftool_availability()
        assert exc_info.value.code == 1


def test_check_conditions_version_flag(base_config):
    """Test check_conditions shows version and exits."""
    import dataclasses

    config = dataclasses.replace(base_config, show_version=True)

    with patch("exifsort.core.check_exiftool_availability"):
        with pytest.raises(SystemExit) as exc_info:
            check_conditions(config)
        assert exc_info.value.code == 0


def test_check_conditions_directory_not_exist(tmp_path):
    """Test check_conditions exits when directory doesn't exist."""
    non_existent = tmp_path / "does_not_exist"
    config = AppConfig(source_dir=non_existent, extensions=["jpg"])

    with patch("exifsort.core.check_exiftool_availability"):
        with pytest.raises(SystemExit) as exc_info:
            check_conditions(config)
        assert exc_info.value.code == 1


def test_check_conditions_directory_not_writable(tmp_path):
    """Test check_conditions exits when directory is not writable."""
    config = AppConfig(source_dir=tmp_path, extensions=["jpg"], source_dir_writable=False)

    with patch("exifsort.core.check_exiftool_availability"):
        with pytest.raises(SystemExit) as exc_info:
            check_conditions(config)
        assert exc_info.value.code == 1


def test_check_conditions_no_extensions(tmp_path):
    """Test check_conditions exits when no extensions specified."""
    config = AppConfig(source_dir=tmp_path, extensions=[], source_dir_writable=True)

    with patch("exifsort.core.check_exiftool_availability"):
        with pytest.raises(SystemExit) as exc_info:
            check_conditions(config)
        assert exc_info.value.code == 1


def test_check_conditions_quiet_and_verbose(tmp_path):
    """Test check_conditions exits when both quiet and verbose are enabled."""
    config = AppConfig(source_dir=tmp_path, extensions=["jpg"], quiet=True, verbose=True, source_dir_writable=True)

    with patch("exifsort.core.check_exiftool_availability"):
        with pytest.raises(SystemExit) as exc_info:
            check_conditions(config)
        assert exc_info.value.code == 1


def test_check_conditions_success(base_config):
    """Test check_conditions passes with valid configuration."""
    with patch("exifsort.core.check_exiftool_availability"):
        # Should not raise
        check_conditions(base_config)


def test_prompt_user_yes_flag(base_config):
    """Test prompt_user returns True when yes flag is set."""
    import dataclasses

    config = dataclasses.replace(base_config, yes=True)
    folder_info = {"valid_files": 10}

    result = prompt_user(folder_info, config)
    assert result is True


def test_prompt_user_test_mode(base_config):
    """Test prompt_user returns True in test mode."""
    import dataclasses

    config = dataclasses.replace(base_config, test=True)
    folder_info = {"valid_files": 10}

    result = prompt_user(folder_info, config)
    assert result is True


def test_prompt_user_accepts_yes(base_config):
    """Test prompt_user returns True when user inputs 'yes'."""
    folder_info = {"valid_files": 10}

    with patch("builtins.input", return_value="yes"):
        result = prompt_user(folder_info, base_config)
        assert result is True


def test_prompt_user_accepts_y(base_config):
    """Test prompt_user returns True when user inputs 'y'."""
    folder_info = {"valid_files": 10}

    with patch("builtins.input", return_value="y"):
        result = prompt_user(folder_info, base_config)
        assert result is True


def test_prompt_user_rejects_no(base_config):
    """Test prompt_user returns False when user inputs 'no'."""
    folder_info = {"valid_files": 10}

    with patch("builtins.input", return_value="no"):
        result = prompt_user(folder_info, base_config)
        assert result is False


def test_prompt_user_rejects_empty(base_config):
    """Test prompt_user returns False when user inputs empty string."""
    folder_info = {"valid_files": 10}

    with patch("builtins.input", return_value=""):
        result = prompt_user(folder_info, base_config)
        assert result is False


def test_get_file_list(tmp_path):
    """Test get_file_list returns sorted list of files."""
    # Create test files
    (tmp_path / "c.jpg").touch()
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.jpg").touch()
    (tmp_path / "subdir").mkdir()

    files = get_file_list(tmp_path)

    assert len(files) == 3
    assert files[0].name == "a.jpg"
    assert files[1].name == "b.jpg"
    assert files[2].name == "c.jpg"


def test_get_file_list_empty_directory(tmp_path):
    """Test get_file_list returns empty list for empty directory."""
    files = get_file_list(tmp_path)
    assert files == []


def test_get_folder_info(base_config):
    """Test get_folder_info returns correct info dict."""
    # Create test files
    (base_config.source_dir / "test1.jpg").touch()
    (base_config.source_dir / "test2.jpg").touch()
    (base_config.source_dir / "test3.mp4").touch()
    (base_config.source_dir / "test4.txt").touch()

    files = get_file_list(base_config.source_dir)
    info = get_folder_info(files, base_config)

    assert info["file_count"] == 4
    assert info["media_count"] == 3
    assert info["media_types"]["jpg"] == 2
    assert info["media_types"]["mp4"] == 1
    assert "created" in info
    assert "modified" in info


def test_get_media_objects(base_config):
    """Test get_media_objects creates FileItem objects."""
    # Create test files
    test_file1 = base_config.source_dir / "test1.jpg"
    test_file2 = base_config.source_dir / "test2.jpg"
    test_file1.write_bytes(b"content1")
    test_file2.write_bytes(b"content2")

    files = [test_file1, test_file2]
    folder_info = {"media_count": 2}

    with patch("exiftool.ExifToolHelper") as mock_et:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.get_metadata.return_value = [
            {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
        ]
        mock_et.return_value = mock_instance

        media_objects = get_media_objects(files, folder_info, base_config)

        assert len(media_objects) == 2
        assert all(isinstance(obj, FileItem) for obj in media_objects)


def test_get_media_objects_filters_by_extension(base_config):
    """Test get_media_objects only processes files with matching extensions."""
    jpg_file = base_config.source_dir / "test.jpg"
    txt_file = base_config.source_dir / "test.txt"
    jpg_file.write_bytes(b"content")
    txt_file.write_bytes(b"content")

    files = [jpg_file, txt_file]
    folder_info = {"media_count": 1}

    with patch("exiftool.ExifToolHelper") as mock_et:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.get_metadata.return_value = [
            {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
        ]
        mock_et.return_value = mock_instance

        media_objects = get_media_objects(files, folder_info, base_config)

        assert len(media_objects) == 1
        assert media_objects[0].name_old == "test.jpg"


def test_process_files_creates_subdirectory(base_config):
    """Test process_files creates subdirectories when needed."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, base_config, metadata)

    folder_info = {"valid_files": 1}

    process_files([file_item], folder_info, base_config)

    # Check that subdirectory was created
    assert (base_config.source_dir / "20240101").exists()
    assert folder_info["processed_files"] == ["test.jpg"]
    assert "20240101" in folder_info["created_dirs"]


def test_process_files_test_mode(base_config):
    """Test process_files doesn't modify files in test mode."""
    import dataclasses

    config = dataclasses.replace(base_config, test=True)

    test_file = config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, config, metadata)

    folder_info = {"valid_files": 1}

    process_files([file_item], folder_info, config)

    # Original file should still exist in same location
    assert test_file.exists()
    # Subdirectory should not be created in test mode
    assert not (config.source_dir / "20240101").exists()


def test_process_files_skips_existing_without_overwrite(base_config):
    """Test process_files skips files when target exists and overwrite is False."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, base_config, metadata)

    # Pre-create the target
    target_dir = base_config.source_dir / "20240101"
    target_dir.mkdir()
    target_file = target_dir / file_item.name_new
    target_file.write_bytes(b"existing")

    folder_info = {"valid_files": 1}

    process_files([file_item], folder_info, base_config)

    assert folder_info["skipped_files"] == ["test.jpg"]
    assert folder_info["processed_files"] == []


def test_process_files_overwrites_with_flag(base_config):
    """Test process_files overwrites when overwrite flag is True."""
    import dataclasses

    config = dataclasses.replace(base_config, overwrite=True)

    test_file = config.source_dir / "test.jpg"
    test_file.write_bytes(b"new_content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, config, metadata)

    # Pre-create the target
    target_dir = config.source_dir / "20240101"
    target_dir.mkdir()
    target_file = target_dir / file_item.name_new
    target_file.write_bytes(b"old_content")

    folder_info = {"valid_files": 1}

    process_files([file_item], folder_info, config)

    assert folder_info["processed_files"] == ["test.jpg"]
    assert target_file.read_bytes() == b"new_content"


def test_process_files_handles_rename_error(base_config):
    """Test process_files handles file rename errors gracefully."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, base_config, metadata)

    folder_info = {"valid_files": 1}

    with patch.object(Path, "rename", side_effect=OSError("Permission denied")):
        process_files([file_item], folder_info, base_config)

        assert folder_info["skipped_files"] == ["test.jpg"]
        assert "File system error" in file_item.error or "Permission denied" in file_item.error


def test_process_files_rename_in_place(base_config):
    """Test process_files renames files in place when use_subdirs is False."""
    import dataclasses

    config = dataclasses.replace(base_config, use_subdirs=False)

    test_file = config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    file_item = FileItem(test_file, config, metadata)

    folder_info = {"valid_files": 1}

    process_files([file_item], folder_info, config)

    # File should be renamed in same directory
    assert not test_file.exists()
    assert (config.source_dir / file_item.name_new).exists()
    assert folder_info["processed_files"] == ["test.jpg"]


def test_process_files_only_processes_valid_files(base_config):
    """Test process_files only processes valid files."""
    # Create one valid and one invalid file
    valid_file = base_config.source_dir / "valid.jpg"
    valid_file.write_bytes(b"content")

    invalid_file = base_config.source_dir / "invalid.jpg"
    # Don't create the file

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    valid_item = FileItem(valid_file, base_config, metadata)
    invalid_item = FileItem(invalid_file, base_config, metadata=None)

    folder_info = {"valid_files": 1}

    process_files([valid_item, invalid_item], folder_info, base_config)

    # Only valid file should be processed
    assert len(folder_info["processed_files"]) == 1
    assert folder_info["processed_files"][0] == "valid.jpg"


def test_process_files_unique_names_in_fallback(base_config):
    """Test that process_files generates unique names for conflicting files in fallback folder."""
    # Create two files without EXIF dates (will go to fallback folder)
    file1 = base_config.source_dir / "nodate.jpg"
    file2 = base_config.source_dir / "nodate.jpg"  # Same name!
    file1.write_bytes(b"content1")

    # Create items without EXIF date metadata
    metadata = {"File:MIMEType": "image/jpeg"}
    item1 = FileItem(file1, base_config, metadata)

    # Process first file
    folder_info = {"valid_files": 1}
    process_files([item1], folder_info, base_config)

    # First file should be processed successfully
    assert len(folder_info["processed_files"]) == 1
    fallback_dir = base_config.source_dir / base_config.fallback_folder
    assert (fallback_dir / "nodate.jpg").exists()

    # Now create second file with same name
    file2.write_bytes(b"content2")
    item2 = FileItem(file2, base_config, metadata)

    # Process second file - should get unique name
    folder_info2 = {"valid_files": 1}
    process_files([item2], folder_info2, base_config)

    # Second file should be processed with unique name
    assert len(folder_info2["processed_files"]) == 1
    assert (fallback_dir / "nodate_1.jpg").exists()
    # Original should still exist
    assert (fallback_dir / "nodate.jpg").exists()


def test_process_files_no_unique_names_outside_fallback(base_config):
    """Test that process_files does NOT generate unique names outside fallback folder."""
    # Create two files with same EXIF date (will go to same dated folder)
    file1 = base_config.source_dir / "photo.jpg"
    file2 = base_config.source_dir / "photo.jpg"  # Same name!
    file1.write_bytes(b"content1")

    metadata = {"EXIF:DateTimeOriginal": "2024:01:01 12:00:00", "File:MIMEType": "image/jpeg"}
    item1 = FileItem(file1, base_config, metadata)

    # Process first file
    folder_info = {"valid_files": 1}
    process_files([item1], folder_info, base_config)

    # First file should be processed successfully
    assert len(folder_info["processed_files"]) == 1
    dated_dir = base_config.source_dir / "20240101"
    target_name = item1.name_new
    assert (dated_dir / target_name).exists()

    # Now create second file with same name and date
    file2.write_bytes(b"content2")
    item2 = FileItem(file2, base_config, metadata)

    # Process second file - should be skipped (not in fallback)
    folder_info2 = {"valid_files": 1}
    process_files([item2], folder_info2, base_config)

    # Second file should be skipped
    assert len(folder_info2["skipped_files"]) == 1
    assert "Target file already exists" in item2.error


def test_check_files_finds_empty_files(base_config):
    """Test check_files identifies empty files."""
    import dataclasses

    config = dataclasses.replace(base_config, check_mode=True, quiet=True)

    # Create an empty file
    empty_file = config.source_dir / "empty.jpg"
    empty_file.touch()

    metadata = {"File:MIMEType": "image/jpeg"}
    item = FileItem(empty_file, config, metadata)

    folder_info = {}
    issues = check_files([item], folder_info, config)

    assert len(issues["empty"]) == 1
    assert issues["empty"][0][0] == "empty.jpg"
    assert "empty" in issues["empty"][0][1].lower()


def test_check_files_finds_no_exif(base_config):
    """Test check_files identifies files without EXIF dates."""
    import dataclasses

    config = dataclasses.replace(base_config, check_mode=True, quiet=True)

    # Create a file with content but no EXIF date
    test_file = config.source_dir / "noexif.jpg"
    test_file.write_bytes(b"fake content")

    metadata = {"File:MIMEType": "image/jpeg"}
    item = FileItem(test_file, config, metadata)

    folder_info = {}
    issues = check_files([item], folder_info, config)

    assert len(issues["no_exif"]) == 1
    assert issues["no_exif"][0][0] == "noexif.jpg"


def test_check_files_no_issues(base_config):
    """Test check_files returns empty dict when all files are valid."""
    import dataclasses

    config = dataclasses.replace(base_config, check_mode=True, quiet=True)

    # Create a valid file with EXIF date
    test_file = config.source_dir / "valid.jpg"
    test_file.write_bytes(b"fake content")

    metadata = {
        "EXIF:DateTimeOriginal": "2024:01:01 12:00:00",
        "File:MIMEType": "image/jpeg"
    }
    item = FileItem(test_file, config, metadata)

    folder_info = {}
    issues = check_files([item], folder_info, config)

    # All issue categories should be empty
    assert len(issues["empty"]) == 0
    assert len(issues["no_exif"]) == 0
    assert len(issues["non_media"]) == 0
    assert len(issues["not_readable"]) == 0
    assert len(issues["not_writable"]) == 0


def test_check_files_multiple_issues(base_config):
    """Test check_files identifies multiple types of issues."""
    import dataclasses

    config = dataclasses.replace(base_config, check_mode=True, quiet=True)

    # Create various problematic files
    empty_file = config.source_dir / "empty.jpg"
    empty_file.touch()

    noexif_file = config.source_dir / "noexif.jpg"
    noexif_file.write_bytes(b"content")

    # Create FileItems
    empty_item = FileItem(empty_file, config, metadata={"File:MIMEType": "image/jpeg"})
    noexif_item = FileItem(noexif_file, config, metadata={"File:MIMEType": "image/jpeg"})

    folder_info = {}
    issues = check_files([empty_item, noexif_item], folder_info, config)

    # Should have both empty and no_exif issues
    assert len(issues["empty"]) == 1
    assert len(issues["no_exif"]) == 1


def test_get_media_objects_exiftool_crash(base_config):
    """Test get_media_objects handles complete ExifTool failure gracefully."""
    test_file = base_config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    files = [test_file]
    folder_info = {"media_count": 1}

    # Mock ExifToolHelper to raise exception on context manager entry
    with patch("exiftool.ExifToolHelper") as mock_et:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(side_effect=RuntimeError("ExifTool crashed"))
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_et.return_value = mock_instance

        # Should not crash, but return FileItems without metadata
        media_objects = get_media_objects(files, folder_info, base_config)

        assert len(media_objects) == 1
        assert not media_objects[0].is_valid  # No metadata means invalid


def test_get_media_objects_individual_file_error_verbose(base_config):
    """Test get_media_objects logs individual file errors in verbose mode."""
    import dataclasses
    import io
    import sys

    config = dataclasses.replace(base_config, verbose=True)

    test_file = config.source_dir / "test.jpg"
    test_file.write_bytes(b"content")

    files = [test_file]
    folder_info = {"media_count": 1}

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    try:
        with patch("exiftool.ExifToolHelper") as mock_et:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_metadata.side_effect = ValueError("Corrupt metadata")
            mock_et.return_value = mock_instance

            media_objects = get_media_objects(files, folder_info, config)

            output = buffer.getvalue()
            assert "Warning:" in output
            assert "Could not read metadata" in output
            assert "test.jpg" in output

            # Should still create FileItem without metadata
            assert len(media_objects) == 1
    finally:
        sys.stdout = old_stdout
