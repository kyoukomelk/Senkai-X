# Senkai X - Universal Dial Linux Control

<div align="center">
  <img src="./Img/logo.png" alt="Senkai X Logo" width="300" />
</div>

## Overview
Senkai X is a Linux-compatible daemon and graphical interface built in Python and PyQt5. It restores and enhances the functionality of the physical Asus ProArt Studiobook dial on Linux distributions (such as Ubuntu, Arch, Fedora, etc.). By intercepting raw HID inputs via `evdev`, Senkai X translates physical dial interactions into rich, system-wide keyboard macros, media controls, and global mouse vertical scrolling events.

## Features
- **Global Hardware Support**: Reads raw device inputs from `/dev/hidraw` to map physical wheel turns and clicks into standard Linux UI events via `uinput`.
- **Auto-Device Calibration Wizard**: Includes a built-in HID scanner to automatically detect and bind your specific Asus Dial node without manual `/dev/` hunting.
- **System Tray Integration**: Quietly runs as a background tray icon. Right-click to access debug settings, mapping panels, or exit the thread loop.
- **Modifier Layers**: Holding down keyboard modifiers (`SHIFT`, `CTRL`, `ALT`, `SUPER`) automatically overlays completely different wheel profiles, allowing limitless keyboard shortcuts on a single physical dial. Out of the box, `SHIFT` converts the dial into a physical mouse scroll wheel.
- **Interactive Wheel OSD Menu**: Provides an immersive, graphical on-screen radial menu for complex macro navigation. Supports hierarchical sub-folders, dynamic SVG back-navigation, and continuous rotation selection before confirmation.
- **Polished Visual OSD**: Custom PyQT5 `paintEvent` rendering engine drawing dark, translucent rings with color-tinted Ionicon SVGs, magnified center displays, and seamless gradients natively onto your monitor.
- **Editable Tree Menu UI**: A robust PyQt5 `QTreeWidget` GUI lets you dynamically add folders, edit node labels, and select `.svg` icons for menus without touching internal JSON.

## Prerequisites
Asus Dial hardware intercepts require root permissions in Linux. To securely operate the UInput virtual keyboard and HID endpoints, you must execute the script as root (`sudo`).

### Dependencies
You need `python3` alongside a standard environment manager (such as `venv`).
The application leverages the following libraries:
- `evdev` (For HID event parsing and virtual input injection)
- `PyQt5` (For the modern tray menu and multi-page settings interfaces)

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kyoukomelk/senkai-x.git
   cd senkai-x
   ```

2. **Setup an isolated virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install evdev PyQt5
   ```

3. **Install the `wpctl` or `amixer` backends (Optional)**:
   Volume controls rely on PipeWire (`wpctl`) or ALSA `amixer`. Ensure one of those packages is properly installed if you bind media keys.

4. **Launch the software execution loop**:
   ```bash
   sudo ./venv/bin/python main.py
   ```
   *Note: Superuser access is strictly required to attach the raw device listeners to the `/dev` folder and mount virtual input nodes.*

## Configuration Structure
Mappings and interface settings are automatically stored in `~/.config/asus_dial.json`. The software can be customized using the provided GUI, or manually edited if preferred.

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
        "osd_monitor": 0,
        "menu_layout": [
            {
                "label": "Music",
                "type": "folder",
                "icon": "musical-notes.svg",
                "children": [
                    {"label": "PLAY / PAUSE", "type": "action", "action": "PLAYPAUSE", "icon": "play.svg"}
                ]
            }
        ]
    }
}
```

## FAQ
**Why is this project created?**
- Because Asus doesn't provide native Linux support for the ProArt Studiobook dial. and the other projects didn't satisfy my needs.

**Why is the project named Senkai X?**
- Senkai (旋回) in japanese means "revolve" or "turn around" which is what the dial does. and the X just sounds cool.

**I have an issue with xyz**
- step one: have you tried turning it off and on again?
- step two: look if you're running the script as root
- step three: Does your wheel work in the debug page?
- step four: submit an issue (I only have the ProArt Studiobook 16 OLED H5600QA so I can't test on other devices)

**can you add xyz feature?**
- maybe, submit an issue and I'll see what I can do

## Credits
This project was largely synthesized using the Asus ProArt dial topology patterns.
- Created By: Kyoukomelk
- Icons: Ionicon
- Code: Antigravity + Google Gemini
- UI/UX: Kyoukomelk