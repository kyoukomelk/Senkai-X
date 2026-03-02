# Senkai X - Asus Dial Linux Control

## Overview
Senkai X is a Linux-compatible daemon and graphical interface built in Python and PyQt5. It restores and enhances the functionality of the physical Asus ProArt Studiobook dial on Linux distributions (such as Ubuntu, Arch, Fedora, etc.). By intercepting raw HID inputs via `evdev`, Senkai X translates physical dial interactions into rich, system-wide keyboard macros, media controls, and global mouse vertical scrolling events.

![Wireframe Match Application Architecture](./assets/screenshot.png) <!-- Update later -->

## Features
- **Global Hardware Support**: Reads raw device inputs from `/dev/hidraw` to map physical wheel turns and clicks into standard Linux UI events via `uinput`.
- **System Tray Integration**: Quietly runs as a background tray icon. Right-click to access debug settings, mapping panels, or exit the thread loop.
- **Modifier Layers**: Holding down keyboard modifiers (`SHIFT`, `CTRL`, `ALT`, `META`) automatically overlays completely different wheel profiles, allowing limitless keyboard shortcuts on a single physical dial. Out of the box, `SHIFT` converts the dial into a physical mouse scroll wheel.
- **Visual Feedback OSD**: Displays a sleek, translucent radial overlay (similar to macOS volume sliders) natively on your screen when you adjust the dial, indicating variables like system volume percentages or executing macros like "UNDO".
- **Dynamic Configuration**: Easily remap layers securely using a comprehensive PyQt5 configuration GUI. Automatically structures configurations to `~/.config/asus_dial.json` safely.

## Prerequisites
Asus Dial hardware intercepts require root permissions in Linux. To securely operate the UInput virtual keyboard and HID endpoints, you must execute the script as root (`sudo`).

### Dependencies
You need `python3` alongside a standard environment manager (such as `venv`).
The application leverages the following libraries:
- `evdev` (For HID event parsing and simulated keyboard/mouse input injection)
- `PyQt5` (For the modern tray menu and multi-page settings interfaces)

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kyoukomelk/senkai-x.git
   cd senkai-x
   ```

2. **Setup a isolated virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install evdev PyQt5
   ```

3. **Install the `wpctl` or `amixer` backends**:
   Volume control automatically defaults to PipeWire (`wpctl`). If you are running an older desktop standard, the app falls back to ALSA `amixer`. Ensure one of those packages is properly installed on your system.

4. **Launch the software execution loop**:
   ```bash
   sudo ./venv/bin/python main.py
   ```
   *Note: Superuser access is strictly required initially to attach the raw device listeners to the `/dev` folder and mount virtual input nodes.*

## Configuration Structure
Mappings are stored in `~/.config/asus_dial.json`. The software can seamlessly be extended by adjusting the internal JSON syntax arrays or leveraging the GUI.

```json
{
    "layers": {
        "BASE": {
            "wheel_left": "VOLDOWN",
            "wheel_right": "VOLUP",
            "wheel_press": "MUTE"
        },
        "SHIFT": {
            "wheel_left": "SCROLL_UP",
            "wheel_right": "SCROLL_DOWN",
            "wheel_press": ""
        }
    },
    "settings": {
        "osd_position": "Center",
        "osd_monitor": 0
    }
}
```

## Credits
This project was largely synthesized using the Asus ProArt dial topology patterns.
- Created By: Kyoukomelk
