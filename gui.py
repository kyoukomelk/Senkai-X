import json
import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, 
    QPushButton, QSpinBox, QHBoxLayout, QGroupBox, QTextEdit,
    QFormLayout, QLineEdit, QSystemTrayIcon, QMenu, QAction, QStyle, QComboBox, QApplication,
    QStackedWidget, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QPainter, QPen, QColor, QFont
from dial_osd import DialOSD
from hid_reader import HidReaderThread
from action_executor import ActionExecutor
import modifier_utils

class DialDiagram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor("#cdd6f4"))
        pen.setWidth(8)
        painter.setPen(pen)
        
        # Center coordinates
        cw = self.width() // 2
        ch = self.height() // 2
        r = 60 # Radius of dial
        
        # Draw Dial Circle
        painter.drawEllipse(cw - r, ch - r, r*2, r*2)
        
        # Draw Left Line
        painter.drawLine(cw - r - 20, ch, cw - 150, ch + 80)
        painter.drawLine(cw - 150, ch + 80, cw - 150, ch + 150)
        
        # Draw Right Line
        painter.drawLine(cw + r + 20, ch, cw + 150, ch + 80)
        painter.drawLine(cw + 150, ch + 80, cw + 150, ch + 150)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asus Dial Linux Control - Senkai X")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        
        self.config_path = os.path.expanduser("~/.config/asus_dial.json")
        self.shortcuts = {
            "layers": {
                "BASE": {"wheel_left": "VOLDOWN", "wheel_right": "VOLUP", "wheel_press": "MUTE"},
                "SHIFT": {"wheel_left": "SCROLL_UP", "wheel_right": "SCROLL_DOWN", "wheel_press": ""},
                "CTRL": {"wheel_left": "CTRL+Z", "wheel_right": "CTRL+Y", "wheel_press": ""},
                "ALT": {"wheel_left": "", "wheel_right": "", "wheel_press": ""},
                "SUPER": {"wheel_left": "", "wheel_right": "", "wheel_press": ""}
            },
            "settings": {
                "osd_position": "Center",
                "osd_monitor": 0
            }
        }
        self.current_layer = "BASE"
        self.executor = ActionExecutor()
        self.osd = DialOSD(self)
        self.dial_val = 0
        
        # We need self.log_text for initial config migration printing
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #313244; color: #a6e3a1; font-family: monospace;")
        
        self.load_config()
        self.init_gui()
        self.setup_tray_icon()
        
        self.reader_thread = None
        self.start_reader()

    def init_gui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        master_layout = QHBoxLayout(main_widget)
        master_layout.setContentsMargins(0,0,0,0)
        master_layout.setSpacing(0)
        
        # ----- SIDEBAR DIRECTORY -----
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("QFrame { background-color: #181825; border-right: 1px solid #313244; }")
        sidebar_layout = QVBoxLayout(sidebar)
        
        # Brand Heading
        brand_lbl = QLabel("Senkai X\nBy: Kyoukomelk")
        brand_lbl.setStyleSheet("font-size: 16px; font-weight: bold; padding: 20px 0px; border: none;")
        brand_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(brand_lbl)
        
        # Navigation Buttons
        btn_style = """
            QPushButton {
                background-color: #1e1e2e; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 6px;
                padding: 10px; margin: 2px 10px; font-size: 14px;
            }
            QPushButton:hover { background-color: #313244; }
            QPushButton:checked { background-color: #45475a; color: #89b4fa; }
        """
        self.nav_btns = []
        pages = ["Connect / Debug", "Wheel Mapping", "Wheel Menu", "Settings"]
        for idx, p in enumerate(pages):
            btn = QPushButton(p)
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            self.nav_btns.append(btn)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        master_layout.addWidget(sidebar)
        
        # ----- CONTENT STACK -----
        self.stack = QStackedWidget()
        master_layout.addWidget(self.stack)
        
        self.preset_actions = [
            "", "VOLUP", "VOLDOWN", "MUTE", "SCROLL_UP", "SCROLL_DOWN",
            "PAGEUP", "PAGEDOWN", "CTRL+Z", "CTRL+Y", "CTRL+C", "CTRL+V",
            "UP", "DOWN", "LEFT", "RIGHT", "ENTER", "SPACE", "ESC", "TAB"
        ]
        
        self.build_debug_page()
        self.build_mapping_page()
        self.build_wheel_menu_page()
        self.build_settings_page()
        
        self.switch_page(1) # Default to Mapping

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)

    def build_debug_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        header = QLabel("Connect / Debug")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)
        
        self.value_label = QLabel("Device: Not Connected")
        self.dial_value_label = QLabel("0")
        self.dial_value_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #89b4fa;")
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.value_label)
        h_layout.addWidget(self.dial_value_label)
        layout.addLayout(h_layout)
        
        layout.addWidget(self.log_text)
        
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Reader")
        self.stop_btn = QPushButton("Stop Reader")
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        
        self.start_btn.clicked.connect(self.start_reader)
        self.stop_btn.clicked.connect(self.stop_reader)
        self.start_btn.setStyleSheet("background-color: #a6e3a1; color: #11111b; padding: 6px;")
        self.stop_btn.setStyleSheet("background-color: #f38ba8; color: #11111b; padding: 6px;")
        
        layout.addLayout(btn_layout)
        self.stack.addWidget(page)

    def build_mapping_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        header = QLabel("Mapping")
        header.setStyleSheet("font-size: 32px; font-weight: normal; margin-bottom: 20px;")
        layout.addWidget(header)
        
        # Layer Nav bar
        layer_nav_layout = QHBoxLayout()
        layer_nav_layout.setAlignment(Qt.AlignCenter)
        
        self.layer_btns = {}
        for layer in ["BASE", "SHIFT", "CTRL", "ALT", "SUPER"]:
            btn = QPushButton(layer if layer != "BASE" else "Default")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #a6adc8; font-size: 16px; border: none; padding: 0px 8px; }
                QPushButton:checked { color: #cdd6f4; font-weight: bold; text-decoration: underline; }
                QPushButton:hover { color: #cdd6f4; }
            """)
            btn.clicked.connect(lambda checked, l=layer: self.on_layer_changed(l))
            layer_nav_layout.addWidget(QLabel("|") if layer == "BASE" else QLabel(""))
            layer_nav_layout.addWidget(btn)
            layer_nav_layout.addWidget(QLabel("|"))
            self.layer_btns[layer] = btn
            
        layout.addLayout(layer_nav_layout)
        layout.addSpacing(40)
        
        # Diagram Map
        diagram_layout = QVBoxLayout()
        diagram_layout.setAlignment(Qt.AlignCenter)
        
        container = QWidget()
        container.setFixedSize(600, 300)
        
        # Center the diagram painting behind absolute combo boxes
        self.diagram = DialDiagram(container)
        self.diagram.setGeometry(100, 0, 400, 300)
        
        cmb_style = "background-color: #ffffff; color: #11111b; border: 1px solid #cdd6f4; border-radius: 6px; padding: 4px; font-weight: bold;"
        
        self.left_input = QComboBox(container)
        self.left_input.setEditable(True)
        self.left_input.addItems(self.preset_actions)
        self.left_input.setStyleSheet(cmb_style)
        self.left_input.setGeometry(20, 245, 120, 30)
        self.left_input.currentTextChanged.connect(self.save_current_layer)
        
        self.right_input = QComboBox(container)
        self.right_input.setEditable(True)
        self.right_input.addItems(self.preset_actions)
        self.right_input.setStyleSheet(cmb_style)
        self.right_input.setGeometry(460, 245, 120, 30)
        self.right_input.currentTextChanged.connect(self.save_current_layer)
        
        diagram_layout.addWidget(container)
        layout.addLayout(diagram_layout)
        layout.addStretch()
        
        self.stack.addWidget(page)
        
        self.on_layer_changed("BASE")

    def build_wheel_menu_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("Wheel Menu (WIP)")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)
        layout.addStretch()
        self.stack.addWidget(page)

    def build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)
        
        osd_group = QGroupBox("OSD Overlay Settings")
        osd_layout = QFormLayout()
        
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Center", "Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"])
        self.pos_combo.setCurrentText(self.shortcuts["settings"].get("osd_position", "Center"))
        self.pos_combo.setStyleSheet("background-color: #313244; color: #cdd6f4; border-radius: 3px; padding: 4px;")
        self.pos_combo.currentTextChanged.connect(self.save_config)
        osd_layout.addRow("Position:", self.pos_combo)
        
        self.mon_combo = QComboBox()
        desktop = QApplication.desktop()
        for i in range(desktop.screenCount()):
            geo = desktop.screenGeometry(i)
            self.mon_combo.addItem(f"Monitor {i} ({geo.width()}x{geo.height()})")
        
        mon_idx = self.shortcuts["settings"].get("osd_monitor", 0)
        self.mon_combo.setCurrentIndex(mon_idx if mon_idx < self.mon_combo.count() else 0)
        self.mon_combo.setStyleSheet("background-color: #313244; color: #cdd6f4; border-radius: 3px; padding: 4px;")
        self.mon_combo.currentIndexChanged.connect(self.save_config)
        osd_layout.addRow("Screen:", self.mon_combo)
        
        osd_group.setLayout(osd_layout)
        layout.addWidget(osd_group)
        layout.addStretch()
        
        self.stack.addWidget(page)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("""
            QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; }
            QMenu::item { padding: 8px 24px; margin: 4px; border-radius: 4px; }
            QMenu::item:selected { background-color: #45475a; color: #89b4fa; }
        """)
        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Context:
            self.tray_menu.exec_(QCursor.pos())
        elif reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            self.show()
            
    def quit_application(self):
        self.stop_reader()
        self.tray_icon.hide()
        QApplication.instance().quit()
        sys.exit(0)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    
                    if "layers" in data:
                        self.shortcuts["layers"].update(data.get("layers", {}))
                        self.shortcuts["settings"].update(data.get("settings", {}))
                    else:
                        self.shortcuts["layers"]["BASE"]["wheel_left"] = data.get("wheel_left", "VOLDOWN")
                        self.shortcuts["layers"]["BASE"]["wheel_right"] = data.get("wheel_right", "VOLUP")
                        self.shortcuts["layers"]["BASE"]["wheel_press"] = data.get("wheel_press", "MUTE")
                        self.shortcuts["settings"]["osd_position"] = data.get("osd_position", "Center")
                        self.shortcuts["settings"]["osd_monitor"] = data.get("osd_monitor", 0)
                        self.save_config_file(quiet=True)
            except Exception as e:
                print(f"Failed to load config: {e}")
                
    def save_config_file(self, quiet=False):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self.shortcuts, f, indent=4)
            if not quiet:
                self.log("Shortcuts saved successfully.")
        except Exception as e:
            if not quiet:
                self.log(f"Failed to save shortcuts: {e}")
                
    def on_layer_changed(self, layer_name):
        self.current_layer = layer_name
        for nm, btn in self.layer_btns.items():
            btn.setChecked(nm == layer_name)
        self.populate_layer_inputs()
        
    def populate_layer_inputs(self):
        # Disconnect signals to avoid recursive saving triggering while switching
        try:
            self.left_input.currentTextChanged.disconnect()
            self.right_input.currentTextChanged.disconnect()
        except:
            pass
            
        layer_data = self.shortcuts["layers"][self.current_layer]
        self.left_input.setCurrentText(layer_data.get("wheel_left", ""))
        self.right_input.setCurrentText(layer_data.get("wheel_right", ""))
        
        self.left_input.currentTextChanged.connect(self.save_current_layer)
        self.right_input.currentTextChanged.connect(self.save_current_layer)

    def save_current_layer(self):
        self.shortcuts["layers"][self.current_layer]["wheel_left"] = self.left_input.currentText().strip()
        self.shortcuts["layers"][self.current_layer]["wheel_right"] = self.right_input.currentText().strip()
        self.save_config_file(quiet=True)

    def save_config(self):
        self.shortcuts["settings"]["osd_position"] = self.pos_combo.currentText()
        self.shortcuts["settings"]["osd_monitor"] = self.mon_combo.currentIndex()
        self.save_config_file(quiet=True)

    def log(self, text):
        if isinstance(text, bytes):
            text = text.hex()
        self.log_text.append(str(text))
        
    def start_reader(self):
        if self.reader_thread is None or not self.reader_thread.isRunning():
            self.reader_thread = HidReaderThread()
            self.reader_thread.raw_data_received.connect(self.log)
            self.reader_thread.wheel_event.connect(self.handle_wheel)
            self.reader_thread.click_event.connect(self.handle_click)
            self.reader_thread.error_occurred.connect(self.handle_error)
            self.reader_thread.start()
            self.value_label.setText("Device: Reading...")
            self.log("Started reading.")
            
    def stop_reader(self):
        if self.reader_thread and self.reader_thread.isRunning():
            self.reader_thread.stop()
            self.reader_thread.wait()
            self.value_label.setText("Device: Stopped")
            self.log("Stopped reading.")
            
    def handle_error(self, err_msg):
        self.value_label.setText("Device: Error")
        self.log(f"ERROR: {err_msg}")

    def handle_wheel(self, direction):
        self.dial_val += direction
        self.dial_value_label.setText(str(self.dial_val))
        
        mod = modifier_utils.get_active_modifier()
        layer = self.shortcuts["layers"].get(mod, self.shortcuts["layers"]["BASE"])
        
        # Fallback to BASE if the layer is completely empty
        if not layer.get("wheel_left") and not layer.get("wheel_right"):
            layer = self.shortcuts["layers"]["BASE"]
            
        friendly_names = {
            "VOLUP": "VOLUME",
            "VOLDOWN": "VOLUME",
            "SCROLL_UP": "SCROLL",
            "SCROLL_DOWN": "SCROLL",
            "PAGEUP": "PAGE",
            "PAGEDOWN": "PAGE",
            "MUTE": "MUTE",
            "CTRL+Z": "UNDO",
            "CTRL+Y": "REDO",
            "CTRL+C": "COPY",
            "CTRL+V": "PASTE"
        }
        
        if direction < 0:
            act = layer.get("wheel_left", "")
            if act: 
                self.executor.execute(act)
                friendly = friendly_names.get(act, act)
                self.osd.show_osd(friendly)
        elif direction > 0:
            act = layer.get("wheel_right", "")
            if act: 
                self.executor.execute(act)
                friendly = friendly_names.get(act, act)
                self.osd.show_osd(friendly)
        
    def handle_click(self, pressed):
        if pressed:
            self.log(f"--- DIAL PRESSED! ---")
            self.dial_val = 0
            self.dial_value_label.setText("0")
            
            mod = modifier_utils.get_active_modifier()
            layer = self.shortcuts["layers"].get(mod, self.shortcuts["layers"]["BASE"])
            if not layer.get("wheel_press"):
                layer = self.shortcuts["layers"]["BASE"]
                
            act = layer.get("wheel_press", "")
            if act: self.executor.execute(act)
            if act: self.osd.show_osd("MUTE" if act == "MUTE" else act)
        else:
            self.log(f"--- DIAL RELEASED! ---")
