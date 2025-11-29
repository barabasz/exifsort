# Changelog

All notable changes to [ExifSort](https://github.com/barabasz/exifsort) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.5] - 2025-11-29

### Added
- Check mode (`-c`/`--check`) to validate files and report issues without moving them
- Automatic unique filename generation for conflicting files in fallback folder
- Templates display (`-T`/`--templates`) to show all available directory and file templates
- New directory template formats: `YYYY.MM.DD`, `YYYY_MM_DD`, `YYYY-MM`, `YYYY/MM/DD`, `YYYY/MM`
- New file prefix formats including `YYYY-MM-DD-HH-MM-SS`, `YYYYMMDD_HHMMSS`, `YYYYMMDD`
- Graceful ExifTool error handling with fallback for missing metadata

### Changed
- Internal tests (pytest with fixtures) to cover all application modules
- Improved error handling for individual file metadata read failures

### Fixed
- Race condition in directory creation (removed exists check before mkdir)
- ExifTool crash handling - application continues with degraded functionality
- Attribute initialization in FileItem when metadata is None

## [0.2.4] - 2025-11-24

### Changed
- Script optimization and bug fixes

## [0.2.3] - 2025-11-24

### Changed
- New project organization (models.py and print.py modules)
- Setting project metadata directly from pyproject.toml

## [0.2.2] - 2025-11-23

### Added
- Some basic tests for pytest

### Changed
- Project organization (models.py for classes Colors and FileItem)

## [0.2.0] - 2025-11-22

### Added
- Colors datalass and `colorize()` method

## [0.1.5] - 2025-10-20

### Added
- `get_media_objects()` converts list of Paths to list of FileItem objects

### Changed
- arguments and options handling with ArgParse
- Internal configuration with TyConf package

## [0.1.0] - 2025-10-05

### Added
- Initial development version

---

## Version History Summary

- **0.2.4** (2025-11-24) - Script optimization and bug fixes
- **0.2.3** (2025-11-24) - New project organization
- **0.2.2** (2025-11-23) - New project organization and basic tests
- **0.2.0** (2025-11-22) - Output colorization for better UX
- **0.1.5** (2025-10-20) - Configuration via TyConf and ArgParse
- **0.1.0** (2025-10-05) - Initial development version