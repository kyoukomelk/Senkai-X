try:
    import evdev
    from evdev import ecodes as e
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

class ActionExecutor:
    def __init__(self):
        self.ui = None
        if EVDEV_AVAILABLE:
            try:
                cap = {
                    e.EV_KEY: [
                        e.KEY_LEFTCTRL, e.KEY_LEFTSHIFT, e.KEY_LEFTALT, e.KEY_LEFTMETA,
                        e.KEY_ENTER, e.KEY_SPACE, e.KEY_TAB, e.KEY_ESC,
                        e.KEY_UP, e.KEY_DOWN, e.KEY_LEFT, e.KEY_RIGHT,
                        e.KEY_BACKSPACE, e.KEY_DELETE,
                        e.KEY_VOLUMEUP, e.KEY_VOLUMEDOWN, e.KEY_MUTE,
                        e.KEY_PAGEUP, e.KEY_PAGEDOWN,
                        e.KEY_Z, e.KEY_Y, e.KEY_C, e.KEY_V, e.KEY_X
                    ],
                    e.EV_REL: [e.REL_WHEEL]
                }
                self.ui = evdev.UInput(cap, name="Asus Dial Virtual Input")
            except Exception as ex:
                print(f"Failed to create UInput: {ex}")

    def execute(self, shortcut_str):
        if not self.ui or not shortcut_str:
            return
            
        if shortcut_str == 'SCROLL_UP':
            self.ui.write(e.EV_REL, e.REL_WHEEL, 1)
            self.ui.syn()
            return
            
        if shortcut_str == 'SCROLL_DOWN':
            self.ui.write(e.EV_REL, e.REL_WHEEL, -1)
            self.ui.syn()
            return
            
        keys = shortcut_str.upper().replace(' ', '').split('+')
        active_keys = []
        
        # Simple string to ecode mapping
        key_map = {
            'CTRL': e.KEY_LEFTCTRL,
            'SHIFT': e.KEY_LEFTSHIFT,
            'ALT': e.KEY_LEFTALT,
            'META': e.KEY_LEFTMETA,
            'SUPER': e.KEY_LEFTMETA,
            'ENTER': e.KEY_ENTER,
            'SPACE': e.KEY_SPACE,
            'TAB': e.KEY_TAB,
            'ESC': e.KEY_ESC,
            'UP': e.KEY_UP,
            'DOWN': e.KEY_DOWN,
            'LEFT': e.KEY_LEFT,
            'RIGHT': e.KEY_RIGHT,
            'BACKSPACE': e.KEY_BACKSPACE,
            'DELETE': e.KEY_DELETE,
            'VOLUP': e.KEY_VOLUMEUP,
            'VOLDOWN': e.KEY_VOLUMEDOWN,
            'MUTE': e.KEY_MUTE
        }
        
        try:
            for k in keys:
                if k in key_map:
                    active_keys.append(key_map[k])
                elif hasattr(e, f"KEY_{k}"):
                    active_keys.append(getattr(e, f"KEY_{k}"))
                else:
                    print(f"Unknown key: {k}")
                    return

            # Press all
            for k in active_keys:
                self.ui.write(e.EV_KEY, k, 1)
            self.ui.syn()
            
            # Release all in reverse
            for k in reversed(active_keys):
                self.ui.write(e.EV_KEY, k, 0)
            self.ui.syn()
            
        except Exception as ex:
            print(f"Execution failed: {ex}")
