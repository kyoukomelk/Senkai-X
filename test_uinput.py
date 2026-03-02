import evdev
from evdev import UInput, ecodes as e
import time

try:
    with UInput() as ui:
        print("UInput created successfully")
        ui.write(e.EV_KEY, e.KEY_A, 1)  # key down
        ui.write(e.EV_KEY, e.KEY_A, 0)  # key up
        ui.syn()
except Exception as ex:
    print(f"Failed to create UInput: {ex}")
