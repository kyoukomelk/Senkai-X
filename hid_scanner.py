import os
import fcntl
import select
from PyQt5.QtCore import QThread, pyqtSignal

class HidScannerThread(QThread):
    # Emits the dynamic path string (e.g. "/dev/hidraw4") when a match is found
    device_found = pyqtSignal(str)
    scan_failed = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.fds = {}  # Map of fd -> path
        self.fd_states = {}

    def run(self):
        self.running = True
        self.fds = {}
        self.fd_states = {}
        poll = select.poll()

        # Try to open every possible hidraw node
        for i in range(30):
            path = f"/dev/hidraw{i}"
            if os.path.exists(path):
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                    self.fds[fd] = path
                    self.fd_states[fd] = {'step': 0, 'count': 0}
                    poll.register(fd, select.POLLIN)
                    
                    # Wake up routine (just in case this is the dial and it's asleep)
                    HIDIOCSFEATURE_9 = 0xC0094806
                    init_data = bytes([0x5a, 0x05, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                    try:
                        fcntl.ioctl(fd, HIDIOCSFEATURE_9, init_data)
                    except Exception:
                        pass
                except Exception:
                    pass

        if not self.fds:
            self.scan_failed.emit("Could not open any /dev/hidraw endpoints. (Are you running with sudo?)")
            self.running = False
            return

        self.progress_update.emit("Step 1/3: Rotate the Dial LEFT 3 times (0/3)")

        while self.running:
            try:
                events = poll.poll(100) # 100ms
                for fd, event in events:
                    if event & select.POLLIN:
                        try:
                            data = os.read(fd, 16)
                            if data and len(data) >= 4:
                                hex_str = " ".join([f"{b:02x}" for b in data[:4]])
                                st = self.fd_states.get(fd)
                                if not st: continue
                                
                                if st['step'] == 0 and hex_str == "01 00 01 00":
                                    st['count'] += 1
                                    if st['count'] >= 3:
                                        st['step'] = 1
                                        st['count'] = 0
                                        self.progress_update.emit("Step 2/3: Rotate the Dial RIGHT 3 times (0/3)")
                                    else:
                                        self.progress_update.emit(f"Step 1/3: Rotate the Dial LEFT 3 times ({st['count']}/3)")
                                        
                                elif st['step'] == 1 and hex_str == "01 00 ff ff":
                                    st['count'] += 1
                                    if st['count'] >= 3:
                                        st['step'] = 2
                                        st['count'] = 0
                                        self.progress_update.emit("Step 3/3: PRESS the Dial 2 times (0/2)")
                                    else:
                                        self.progress_update.emit(f"Step 2/3: Rotate the Dial RIGHT 3 times ({st['count']}/3)")
                                        
                                elif st['step'] == 2 and hex_str == "01 01 00 00":
                                    st['count'] += 1
                                    if st['count'] >= 2:
                                        winning_path = self.fds[fd]
                                        self._cleanup()
                                        self.device_found.emit(winning_path)
                                        return
                                    else:
                                        self.progress_update.emit(f"Step 3/3: PRESS the Dial 2 times ({st['count']}/2)")
                        except Exception:
                            continue
            except Exception as e:
                # EWOULDBLOCK / EAGAIN are expected nonblock behavior
                if getattr(e, "errno", None) != 11:
                    self.scan_failed.emit(f"Scanner read error: {e}")
                    break

        self._cleanup()

    def _cleanup(self):
        self.running = False
        for fd in self.fds:
            try:
                os.close(fd)
            except Exception:
                pass
        self.fds.clear()

    def stop(self):
        self.running = False
        self.wait()
