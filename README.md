# Racing Telemetry Overlay

Professional real-time telemetry overlay for Le Mans Ultimate and F1 games with advanced G-force visualization.

## Features

- **G-Force Visualization** - Real-time lateral and longitudinal force display
- **Friction Circle** - Professional racing-style G-force circle
- **Le Mans Ultimate** - Native shared memory support
- **F1 2023/2024** - Complete UDP telemetry
- **Pedal Telemetry** - Real-time throttle/brake visualization
- **Professional Interface** - Clean, racing-focused design
- **Always on Top** - Overlay stays visible over any application
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
   python racing_overlay.py
   ```

## Game Configuration

### Le Mans Ultimate

**IMPORTANT: Requires rF2 Shared Memory Plugin**

1. **Download and install** the [rF2 Shared Memory Map Plugin](https://github.com/TheIronWolfModding/rF2SharedMemoryMapPlugin)
   - Follow the installation instructions in the plugin repository
   - This plugin is **essential** for telemetry data access
2. Ensure the plugin is properly configured and active in Le Mans Ultimate
3. **Set game to BORDERLESS mode** (not fullscreen)
4. Start a session (practice, qualifying, or race)

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

- **G-Force Circle**: Real-time lateral and longitudinal G-force visualization
- **Pedal Bars**: Vertical throttle and brake percentage display
- **G-Force Values**: Numerical display of current forces
- **Connection Status**: Shows game connection state
- **Professional Layout**: Clean racing-focused design

## Updates

The application includes automatic update checking:

- **Automatic check**: On startup
- **Manual check**: Press Ctrl+U
- **Notifications**: Windows toast notifications when updates are available
- **One-click install**: Automated download and installation

## Troubleshooting

### No data appearing

1. **For LMU**: Ensure rF2 Shared Memory Plugin is installed and active
2. **For LMU**: Set game to BORDERLESS mode (not fullscreen)
3. **For F1**: Check telemetry is enabled with correct port settings
4. Start a racing session (practice, qualifying, or race)
5. Temporarily disable firewall if needed
6. Restart game after configuration changes

### Performance issues

- Reduce game telemetry send rate to 30Hz
- Close other resource-intensive programs
- Ensure game is running in borderless mode

## Supported Games

| Game             | Method           | G-Force Support | Status    |
| ---------------- | ---------------- | --------------- | --------- |
| Le Mans Ultimate | Shared Memory    | Full            | Supported |
| F1 2024          | UDP (port 20777) | Limited         | Supported |
| F1 2023          | UDP (port 20777) | Limited         | Supported |

## System Requirements

- Windows 10/11
- .NET Framework 4.8 or higher
- 50MB free disk space
- Active internet connection for updates

## Support

For issues and feature requests, please visit the [GitHub Issues](https://github.com/Kenjiisok/game-telemetry/issues) page.

---

Created for the sim racing community