# ExifSort

**ExifSort** - sort media files into date-based folders by reading EXIF creation date.

## Key Features

✅ **Robust Metadata Support**: Powered by [ExifTool](https://exiftool.org/), ensuring reliable reading of EXIF/XMP creation dates from a wide variety of formats (JPG, DNG, MOV, MP4, ORF, RAW, and more).  
✅ **Flexible Organization**: Automatically moves files into date-based directory structures (e.g., `2023/20231224`) and renames them with timestamp prefixes (e.g., `20231224-180000-Image.jpg`).  
✅ **"Party Mode" (Day Shift)**: Define when a new day starts (default: 04:00 AM). Photos taken after midnight (e.g., at a party) will be sorted into the previous day's folder, keeping events together.  
✅ **Extension Normalization**: Automatically unifies file extensions to lowercase standard formats (e.g., converts `.JPEG` to `.jpg`, `.TIFF` to `.tif`).  
✅ **Time Correction**: Apply a time offset (in seconds) to fix timestamps if your camera's clock was set incorrectly.  
✅ **Safe & Secure**:
→ **Dry-run mode (`--test`)**: Preview changes without modifying any files.
→  **Conflict protection**: Skips files if the target destination already exists (unless overwrite is forced).
→  **Fallback handling**: Files without metadata are safely moved to a dedicated `_UNKNOWN` folder.
→  **Robust error handling**: Gracefully handles permission errors, corrupted metadata, invalid formats, and file system issues. Failed operations are reported with clear error messages while processing continues for remaining files.
✅ **CLI Friendly**: Includes a progress bar, colorful output, and verbose mode for detailed processing logs.  

## Installation

```bash
pip install exifsort
```

## Requirements

- Python 3.13+
- [ExifTool](https://exiftool.org/) command-line tool
- [PyExifTool](https://pypi.org/project/PyExifTool/) Python library

## License

MIT License - see [LICENSE](https://github.com/barabasz/exifsort/blob/main/LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Links

- **GitHub**: https://github.com/barabasz/exifsort
- **Issues**: https://github.com/barabasz/exifsort/issues
