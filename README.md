# Racing Telemetry Pedals

Professional real-time pedal telemetry overlay for Le Mans Ultimate and F1 games.

## Features

- **Le Mans Ultimate** - Native UDP support
- **F1 2023/2024** - Complete pedal telemetry
- **Modern interface** - Real-time bars and graphs
- **Visual history** - Last 10 seconds of data
- **Auto-detection** - Automatically detects your game
- **Optimized performance** - Smooth 60 FPS
- **Auto-updates** - Automatic update system

## Installation

### Quick Start (Recommended)

1. Download the latest `KenjiOverlay.exe` from [Releases](https://github.com/Kenjiisok/game-telemetry/releases)
2. Run the executable
3. Configure your game (see below)
4. Start racing!

### From Source

1. Install Python 3.9 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the overlay:
   ```bash
   python overlay.py
   ```

## Game Configuration

### Le Mans Ultimate

**IMPORTANT: Requires plugin installation**

1. Download `rFactor2SharedMemoryMapPlugin64.dll` from the rFactor2 SDK
2. Copy it to `Le Mans Ultimate\Plugins\`
3. Edit `CustomPluginVariables.JSON` to enable the plugin
4. **Set game to BORDERLESS mode** (not fullscreen)
5. Restart the game

### F1 2023/2024

1. Go to Settings > Telemetry Settings
2. Set UDP Telemetry: ON
3. IP Address: 127.0.0.1
4. Port: 20777
5. Send Rate: 60Hz

## Usage

### Controls

- **Mouse drag**: Move overlay window
- **V**: Toggle visibility
- **Ctrl+U**: Check for updates
- **ESC**: Exit application

### Interface

- **Pedal bars**: Show current throttle/brake percentage
- **History graph**: Last 10 seconds of telemetry data
- **Connection status**: Shows if receiving data
- **Packet counter**: Performance monitoring

## Updates

The application includes automatic update checking:

- **Automatic check**: On startup
- **Manual check**: Press Ctrl+U
- **Notifications**: Windows toast notifications when updates are available
- **One-click install**: Automated download and installation

## Troubleshooting

### No data appearing

1. Check telemetry is enabled in game settings
2. Verify correct port and IP configuration
3. **For LMU**: Ensure game is in BORDERLESS mode
4. **For LMU**: Verify plugin is installed correctly
5. Temporarily disable firewall
6. Restart game after configuration

### Performance issues

- Reduce game telemetry send rate to 30Hz
- Close other resource-intensive programs
- Ensure game is running in borderless mode

## Supported Games

| Game             | Method                 | Status    |
| ---------------- | ---------------------- | --------- |
| Le Mans Ultimate | Shared Memory + Plugin | Supported |
| F1 2024          | UDP (port 20777)       | Supported |
| F1 2023          | UDP (port 20777)       | Supported |

## System Requirements

- Windows 10/11
- .NET Framework 4.8 or higher
- 50MB free disk space
- Active internet connection for updates

## Support

For issues and feature requests, please visit the [GitHub Issues](https://github.com/Kenjiisok/game-telemetry/issues) page.

---

Created for the sim racing community