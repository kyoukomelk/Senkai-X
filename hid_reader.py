import os
import fcntl
import select
from PyQt5.QtCore import QThread, pyqtSignal

class HidReaderThread(QThread):
    raw_data_received = pyqtSignal(bytes)
    wheel_event = pyqtSignal(int)      # +1 for right, -1 for left
    click_event = pyqtSignal(bool)     # True for pressed
    error_occurred = pyqtSignal(str)

    def __init__(self, hid_node_id=4, parent=None):
        super().__init__(parent)
        self.hid_path = f"/dev/hidraw{hid_node_id}"
        self.running = False
        self.fd = None

    def run(self):
        self.running = True

        try:
            self.fd = os.open(self.hid_path, os.O_RDONLY | os.O_NONBLOCK)
        except Exception as e:
            self.error_occurred.emit(f"Failed to open {self.hid_path}: {str(e)}\nHint: Run with sudo")
            return

        # Initialize the Asus Dial feature report to wake it up if needed.
        HIDIOCSFEATURE_9 = 0xC0094806
        init_data = bytes([0x5a, 0x05, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        try:
            fcntl.ioctl(self.fd, HIDIOCSFEATURE_9, init_data)
        except Exception:
            pass # Usually fails if already initialized or not supported, ignore.

        poll = select.poll()
        poll.register(self.fd, select.POLLIN)

        while self.running:
            try:
                events = poll.poll(100) # 100ms timeout
                if events:
                    # Asus HID reports are usually small
                    data = os.read(self.fd, 16)
                    if data:
                        self.raw_data_received.emit(data)
                        self._parse_and_emit(data)
            except Exception as e:
                # EWOULDBLOCK / EAGAIN handled by select, this is a real error
                if getattr(e, "errno", None) != 11:
                    self.error_occurred.emit(f"Read error: {e}")
                    break

        if self.fd is not None:
            os.close(self.fd)

    def _parse_and_emit(self, data):
        if len(data) < 4:
            return
            
        hex_str = " ".join([f"{b:02x}" for b in data[:4]])
        
        # Exact byte matches for Asus Dial
        if hex_str == "01 00 01 00":
            self.wheel_event.emit(-1)
        elif hex_str == "01 00 ff ff":
            self.wheel_event.emit(1)
        elif hex_str == "01 01 00 00":
            self.click_event.emit(True)
        elif hex_str == "01 00 00 00":
            self.click_event.emit(False)

    def stop(self):
        self.running = False
        self.wait()
