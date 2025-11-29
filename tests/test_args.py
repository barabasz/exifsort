"""
Tests for argument parsing in args.py
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from exifsort.args import get_config, get_default_info, get_default_value
from exifsort.models import AppConfig


def test_get_default_value():
    """Test extraction of default values from AppConfig dataclass."""
    assert get_default_value("normalize_ext") is True
    assert get_default_value("offset") == 0
    assert get_default_value("fallback_folder") == "_UNKNOWN"
    assert get_default_value("file_template") == "YYYYMMDD-HHMMSS"
    assert "jpg" in get_default_value("extensions")


def test_get_default_info():
    """Test generation of default info strings for help messages."""
    result = get_default_info("test_value")
    assert "default:" in result
    assert "test_value" in result


@patch("sys.argv", ["exifsort"])
def test_get_config_defaults(tmp_path):
    """Test that get_config returns AppConfig with defaults when no args provided."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert isinstance(cfg, AppConfig)
        assert cfg.source_dir == tmp_path
        assert cfg.normalize_ext is True
        assert cfg.use_prefix is True
        assert cfg.use_subdirs is True
        assert cfg.test is False
        assert cfg.verbose is False
        assert cfg.quiet is False


@patch("sys.argv", ["exifsort", "-e", "jpg", "png"])
def test_get_config_extensions(tmp_path):
    """Test parsing of file extensions argument."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert "jpg" in cfg.extensions
        assert "png" in cfg.extensions
        assert len(cfg.extensions) == 2


@patch("sys.argv", ["exifsort", "-e", ".JPG", ".PNG"])
def test_get_config_extensions_with_dots(tmp_path):
    """Test that dots are stripped and extensions are lowercased."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert "jpg" in cfg.extensions
        assert "png" in cfg.extensions
        assert ".jpg" not in cfg.extensions


@patch("sys.argv", ["exifsort", "-t"])
def test_get_config_test_mode(tmp_path):
    """Test that test mode flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.test is True


@patch("sys.argv", ["exifsort", "-v"])
def test_get_config_version_flag(tmp_path):
    """Test that version flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.show_version is True


@patch("sys.argv", ["exifsort", "-T"])
def test_get_config_templates_flag(tmp_path):
    """Test that templates flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.show_templates is True


@patch("sys.argv", ["exifsort", "--templates"])
def test_get_config_templates_flag_long(tmp_path):
    """Test that --templates flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.show_templates is True


@patch("sys.argv", ["exifsort", "-V"])
def test_get_config_verbose_mode(tmp_path):
    """Test that verbose mode flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.verbose is True


@patch("sys.argv", ["exifsort", "-q"])
def test_get_config_quiet_mode(tmp_path):
    """Test that quiet mode flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.quiet is True


@patch("sys.argv", ["exifsort", "-O"])
def test_get_config_overwrite_flag(tmp_path):
    """Test that overwrite flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.overwrite is True


@patch("sys.argv", ["exifsort", "-y"])
def test_get_config_yes_flag(tmp_path):
    """Test that yes flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.yes is True


@patch("sys.argv", ["exifsort", "-o", "3600"])
def test_get_config_offset(tmp_path):
    """Test that time offset is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.offset == 3600


@patch("sys.argv", ["exifsort", "-f", "YYYY-MM-DD"])
def test_get_config_file_template(tmp_path):
    """Test that file template is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.file_template == "YYYY-MM-DD"


@patch("sys.argv", ["exifsort", "-d", "YYYY/MM"])
def test_get_config_directory_template(tmp_path):
    """Test that directory template is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.directory_template == "YYYY/MM"


@patch("sys.argv", ["exifsort", "-F", "NO_DATE"])
def test_get_config_fallback_folder(tmp_path):
    """Test that fallback folder is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.fallback_folder == "NO_DATE"


@patch("sys.argv", ["exifsort", "-s"])
def test_get_config_skip_fallback(tmp_path):
    """Test that skip fallback flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.use_fallback_folder is False


@patch("sys.argv", ["exifsort", "-p"])
def test_get_config_no_prefix(tmp_path):
    """Test that no prefix flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.use_prefix is False


@patch("sys.argv", ["exifsort", "-r"])
def test_get_config_rename_in_place(tmp_path):
    """Test that rename in place flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.use_subdirs is False


@patch("sys.argv", ["exifsort", "-N"])
def test_get_config_no_normalize(tmp_path):
    """Test that no normalize flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.normalize_ext is False


@patch("sys.argv", ["exifsort", "-i", "vacation"])
def test_get_config_interfix(tmp_path):
    """Test that interfix is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.interfix == "vacation"


@patch("sys.argv", ["exifsort", "-n", "05:30:00"])
def test_get_config_new_day_time(tmp_path):
    """Test that new day start time is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.time_day_starts == "05:30:00"


@patch("sys.argv", ["exifsort", "-D"])
def test_get_config_show_files_details(tmp_path):
    """Test that show files details flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.show_files_details is True


@patch("sys.argv", ["exifsort", "-E"])
def test_get_config_show_errors(tmp_path):
    """Test that show errors flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.show_errors is True


@patch("sys.argv", ["exifsort", "-S"])
def test_get_config_show_settings(tmp_path):
    """Test that show settings flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.show_settings is True


@patch("sys.argv", ["exifsort", "/custom/path"])
def test_get_config_custom_directory(tmp_path):
    """Test that custom directory argument is parsed correctly."""
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()

    with patch("sys.argv", ["exifsort", str(custom_dir)]):
        cfg = get_config()
        assert cfg.source_dir == custom_dir


@patch("sys.argv", ["exifsort", "-t", "-V", "-O"])
def test_get_config_multiple_flags(tmp_path):
    """Test parsing multiple flags together."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.test is True
        assert cfg.verbose is True
        assert cfg.overwrite is True


@patch("sys.argv", ["exifsort", "-c"])
def test_get_config_check_mode(tmp_path):
    """Test that check mode flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.check_mode is True


@patch("sys.argv", ["exifsort", "--check"])
def test_get_config_check_mode_long(tmp_path):
    """Test that check mode long flag is parsed correctly."""
    with patch("exifsort.args.os.getcwd", return_value=str(tmp_path)):
        cfg = get_config()
        assert cfg.check_mode is True
