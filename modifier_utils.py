import evdev
from evdev import ecodes as e

_kbd_devices = None

def get_kbd_devices():
    global _kbd_devices
    if _kbd_devices is None:
        _kbd_devices = []
        try:
            for path in evdev.list_devices():
                dev = evdev.InputDevice(path)
                if e.EV_KEY in dev.capabilities():
                    _kbd_devices.append(dev)
        except Exception:
            pass
    return _kbd_devices

def get_active_modifier():
    """
    Scans all EV_KEY capable input devices on the system.
    Returns the first matching macro layer: "SUPER", "CTRL", "ALT", "SHIFT"
    Returns "BASE" if no recognized modifier is depressed.
    """
    devices = get_kbd_devices()
    if not devices:
        return "BASE"
        
    for dev in devices:
        try:
            if e.EV_KEY in dev.capabilities():
                active_keys = dev.active_keys()
                if not active_keys:
                    continue
                
                if e.KEY_LEFTMETA in active_keys or e.KEY_RIGHTMETA in active_keys:
                    return "SUPER"
                if e.KEY_LEFTCTRL in active_keys or e.KEY_RIGHTCTRL in active_keys:
                    return "CTRL"
                if e.KEY_LEFTALT in active_keys or e.KEY_RIGHTALT in active_keys:
                    return "ALT"
                if e.KEY_LEFTSHIFT in active_keys or e.KEY_RIGHTSHIFT in active_keys:
                    return "SHIFT"
        except Exception:
            pass
            
    return "BASE"
