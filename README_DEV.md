# Racing Telemetry - Developer Documentation

Technical documentation for developers and contributors.

## Project Architecture

### File Structure

```
game-telemetry/
├── overlay.py              # Main entry point with auto-update system
├── racing_overlay.py       # Main overlay interface (Qt/PySide)
├── updater.py              # Standalone updater executable
├── version.py              # Version configuration
├── requirements.txt        # Python dependencies
├── src/
│   └── updater.py          # Auto-update logic
└── dist/
    ├── KenjiOverlay.exe    # Main application executable
    └── updater.exe         # Update utility executable
```

### Core Components

1. **overlay.py** - Entry point that:
   - Checks for updates in background thread
   - Imports and launches racing_overlay.py
   - Handles Windows toast notifications for updates

2. **racing_overlay.py** - Main application featuring:
   - Qt/PySide overlay window with transparency
   - Real-time pedal telemetry display
   - Game auto-detection (Le Mans Ultimate, F1)
   - Hotkey handling (V, Ctrl+U, ESC)

3. **Auto-Update System**:
   - `src/updater.py` - GitHub API integration and update logic
   - `updater.py` - Standalone executable replacement utility
   - `version.py` - Centralized version management

### Technology Stack

- **Python 3.9+**
- **PySide6/Qt** - Cross-platform GUI framework
- **PyInstaller** - Executable compilation
- **win11toast** - Windows native notifications
- **GitHub API** - Release management and distribution

## Development Setup

### Prerequisites

1. Python 3.9 or higher
2. Git
3. Virtual environment (recommended)

### Installation

```bash
# Clone repository
git clone https://github.com/Kenjiisok/game-telemetry.git
cd game-telemetry

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install build dependencies
pip install pyinstaller win11toast
```

### Running from Source

```bash
# Run main application
python overlay.py

# Run without auto-update (development)
python racing_overlay.py
```

## Building Executables

### Main Application

```bash
# Build main overlay executable
pyinstaller --onefile --windowed --name "KenjiOverlay" --add-data "version.py;." --add-data "src;src" overlay.py

# Build debug version (with console)
pyinstaller --onefile --console --name "KenjiOverlay-Debug" --add-data "version.py;." --add-data "src;src" overlay.py
```

### Updater Utility

```bash
# Build updater executable
pyinstaller --onefile --windowed --name "updater" updater.py
```

### Output Location

Executables are created in `dist/`:
- `KenjiOverlay.exe` - Main application
- `updater.exe` - Update utility
- `KenjiOverlay-Debug.exe` - Debug version with console

## Release Process

### 1. Version Management

Update `version.py`:
```python
__version__ = "1.2.0"
__app_name__ = "Racing Telemetry Pedals"
__github_repo__ = "Kenjiisok/game-telemetry"
```

### 2. Build Executables

```bash
# Clean previous builds
rm -rf build/ dist/

# Build main application
pyinstaller --onefile --windowed --name "KenjiOverlay" --add-data "version.py;." --add-data "src;src" overlay.py

# Build updater
pyinstaller --onefile --windowed --name "updater" updater.py
```

### 3. Create GitHub Release

**REQUIRED FILES FOR GITHUB RELEASE:**

1. **Individual Executables** (for auto-update):
   - `KenjiOverlay.exe` - Main application
   - `updater.exe` - Update utility

2. **Source Code Archive**:
   - Create ZIP of source code
   - Name it `racing-telemetry-v{version}.zip`

3. **Release Notes**:
   - List new features
   - Bug fixes
   - Breaking changes

### 4. GitHub Release Steps

1. Go to GitHub repository
2. Click "Releases" → "Create a new release"
3. Tag version: `v1.2.0`
4. Release title: `Racing Telemetry v1.2.0`
5. **Upload these files**:
   - `KenjiOverlay.exe`
   - `updater.exe`
   - `racing-telemetry-v1.2.0.zip`
6. Write release notes
7. Publish release

### 5. Auto-Update Behavior

The auto-update system works as follows:
1. Checks GitHub API for latest release
2. Compares with current version in `version.py`
3. Downloads `KenjiOverlay.exe` from release assets
4. Uses `updater.exe` to replace running executable
5. Restarts application with new version

## Testing

### Manual Testing

1. **Basic Functionality**:
   - Application starts without errors
   - Overlay displays correctly
   - Hotkeys work (V, Ctrl+U, ESC)

2. **Auto-Update Testing**:
   - Set version.py to older version
   - Run application
   - Verify update notification appears
   - Test Ctrl+U update process

3. **Game Integration**:
   - Test with Le Mans Ultimate
   - Test with F1 2024/2023
   - Verify telemetry data display

### Debugging

Use debug executable for troubleshooting:
```bash
# Run debug version with console output
./dist/KenjiOverlay-Debug.exe
```

## Code Quality

### Standards

- Remove all emojis from Python files
- Use professional English comments
- Follow PEP 8 style guidelines
- Include docstrings for functions and classes

### Dependencies

Keep dependencies minimal and well-maintained:
- `PySide6` - GUI framework
- `pygame` - Joystick/controller input
- `numpy` - Data processing
- `win11toast` - Windows notifications

## Troubleshooting

### Common Build Issues

1. **PyInstaller ImportError**:
   - Add missing modules to `--hidden-import`
   - Check virtual environment activation

2. **Missing DLLs**:
   - Ensure all dependencies are in PATH
   - Use `--add-binary` for external libraries

3. **Version Embedding**:
   - Version is embedded at compile time
   - Recompile after changing `version.py`

### Runtime Issues

1. **Auto-Update Failures**:
   - Check internet connection
   - Verify GitHub API access
   - Ensure updater.exe exists

2. **Overlay Not Visible**:
   - Check window flags configuration
   - Verify game is in borderless mode
   - Test with different screen resolutions

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Update documentation if needed
5. Submit pull request with detailed description

## License

This project is proprietary software. See license agreement for details.

---

For technical questions, contact the development team or create an issue on GitHub.