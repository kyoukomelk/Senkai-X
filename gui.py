import json
import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, 
    QPushButton, QSpinBox, QHBoxLayout, QGroupBox, QTextEdit,
    QFormLayout, QLineEdit, QSystemTrayIcon, QMenu, QAction, QStyle, QComboBox, QApplication,
    QStackedWidget, QFrame, QMessageBox, QTreeWidget, QTreeWidgetItem, QSizePolicy, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QPainter, QPen, QColor, QFont, QPixmap
from dial_osd import DialOSD
from hid_reader import HidReaderThread
from hid_scanner import HidScannerThread
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
        painter.drawLine(cw - r - 20, ch, 20, self.height() - 40)
        
        # Draw Right Line
        painter.drawLine(cw + r + 20, ch, self.width() - 20, self.height() - 40)

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
        self.osd.menu_aborted.connect(self.cancel_menu)
        self.dial_val = 0
        
        # Interactive Wheel Menu State
        self.menu_active = False
        self.menu_structure = [] # Will be populated by load_config
        self.menu_history = []
        self.menu_items = []
        
        # We need self.log_text for initial config migration printing
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #313244; color: #a6e3a1; font-family: monospace;")
        
        self.load_config()
        self.init_gui()
        self.setup_tray_icon()
        
        self.reader_thread = None
        self.scanner_thread = None
        self.calibration_msg = None
        
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
        logo_lbl = QLabel()
        logo_pixmap = QPixmap("Img/logo.png")
        if not logo_pixmap.isNull():
            logo_lbl.setPixmap(logo_pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("padding-top: 20px; border: none;")
        sidebar_layout.addWidget(logo_lbl)
        
        brand_lbl = QLabel("Senkai X")
        brand_lbl.setStyleSheet("font-size: 16px; font-weight: bold; padding-bottom: 20px; border: none;")
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
        self.find_btn = QPushButton("Find Dial (Setup)")
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.find_btn)
        
        self.start_btn.clicked.connect(self.start_reader)
        self.stop_btn.clicked.connect(self.stop_reader)
        self.find_btn.clicked.connect(self.start_calibration)
        
        self.start_btn.setStyleSheet("background-color: #a6e3a1; color: #11111b; padding: 6px;")
        self.stop_btn.setStyleSheet("background-color: #f38ba8; color: #11111b; padding: 6px;")
        self.find_btn.setStyleSheet("background-color: #89b4fa; color: #11111b; padding: 6px; font-weight: bold;")
        
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
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        
        self.diagram = DialDiagram()
        self.diagram.setMinimumSize(300, 300)
        self.diagram.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        cmb_style = "background-color: #ffffff; color: #11111b; border: 1px solid #cdd6f4; border-radius: 6px; padding: 4px; font-weight: bold;"
        
        self.left_input = QComboBox()
        self.left_input.setEditable(True)
        self.left_input.addItems(self.preset_actions)
        self.left_input.setStyleSheet(cmb_style)
        self.left_input.setMinimumWidth(150)
        self.left_input.currentTextChanged.connect(self.save_current_layer)
        
        self.right_input = QComboBox()
        self.right_input.setEditable(True)
        self.right_input.addItems(self.preset_actions)
        self.right_input.setStyleSheet(cmb_style)
        self.right_input.setMinimumWidth(150)
        self.right_input.currentTextChanged.connect(self.save_current_layer)
        
        # Assemble Grid: combo boxes in bottom corners
        grid.addWidget(self.diagram, 0, 1, 3, 1)
        grid.addWidget(self.left_input, 2, 0, Qt.AlignTop | Qt.AlignRight)
        grid.addWidget(self.right_input, 2, 2, Qt.AlignTop | Qt.AlignLeft)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 0)
        
        layout.addWidget(container)
        layout.addStretch()
        
        self.stack.addWidget(page)
        
        self.on_layer_changed("BASE")

    def build_wheel_menu_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        
        # Left Side: The Tree
        tree_layout = QVBoxLayout()
        header = QLabel("Wheel Menu Editor")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        tree_layout.addWidget(header)
        
        self.menu_tree = QTreeWidget()
        self.menu_tree.setHeaderHidden(True)
        self.menu_tree.setStyleSheet("""
            QTreeWidget { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; font-size: 14px; }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background-color: #45475a; }
        """)
        
        # Populate Tree recursively
        self._populate_tree(self.menu_structure, self.menu_tree.invisibleRootItem())
        self.menu_tree.expandAll()
        
        tree_layout.addWidget(self.menu_tree)
        
        # Tree Controls
        btn_layout = QHBoxLayout()
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_action_btn = QPushButton("Add Action")
        self.del_node_btn = QPushButton("Delete Selected")
        
        for btn in [self.add_folder_btn, self.add_action_btn, self.del_node_btn]:
            btn.setStyleSheet("background-color: #45475a; color: #cdd6f4; padding: 6px; border-radius: 4px;")
            btn_layout.addWidget(btn)
            
        tree_layout.addLayout(btn_layout)
        
        # Right Side: Node Editor Form
        form_frame = QFrame()
        form_frame.setFixedWidth(250)
        form_frame.setStyleSheet("background-color: #181825; border-left: 1px solid #313244; padding: 10px;")
        form_layout = QVBoxLayout(form_frame)
        
        form_lbl = QLabel("Node Editor")
        form_lbl.setStyleSheet("font-size: 18px; font-weight: bold; border: none; margin-bottom: 20px;")
        form_layout.addWidget(form_lbl)
        
        # Node Editor Inputs
        node_form = QFormLayout()
        
        self.node_label_edit = QLineEdit()
        self.node_label_edit.setStyleSheet("background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 3px; padding: 4px;")
        
        self.node_icon_combo = QComboBox()
        self.node_icon_combo.setStyleSheet("background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 3px; padding: 4px;")
        self._load_available_icons()
        
        self.node_action_combo = QComboBox()
        self.node_action_combo.setEditable(True)
        self.node_action_combo.addItems(self.preset_actions)
        self.node_action_combo.setStyleSheet("background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 3px; padding: 4px;")
        
        node_form.addRow("Label:", self.node_label_edit)
        node_form.addRow("Icon (.svg):", self.node_icon_combo)
        node_form.addRow("Action:", self.node_action_combo)
        
        form_layout.addLayout(node_form)
        form_layout.addStretch()
        
        # Save Tree Configuration Button
        self.save_tree_btn = QPushButton("Save Menu to Config")
        self.save_tree_btn.setStyleSheet("background-color: #a6e3a1; color: #11111b; padding: 8px; font-weight: bold; border-radius: 4px;")
        form_layout.addWidget(self.save_tree_btn)
        
        # Add to main horizontal layout
        layout.addLayout(tree_layout)
        layout.addWidget(form_frame)
        self.stack.addWidget(page)
        
        # Connect Signals
        self.menu_tree.itemSelectionChanged.connect(self._on_tree_selection)
        self.node_label_edit.textEdited.connect(self._on_node_edited)
        self.node_icon_combo.currentTextChanged.connect(self._on_node_edited)
        self.node_action_combo.currentTextChanged.connect(self._on_node_edited)
        
        self.add_folder_btn.clicked.connect(self._add_tree_folder)
        self.add_action_btn.clicked.connect(self._add_tree_action)
        self.del_node_btn.clicked.connect(self._delete_tree_node)
        self.save_tree_btn.clicked.connect(self._save_tree_config)

    def _add_tree_folder(self):
        parent = self.menu_tree.currentItem() or self.menu_tree.invisibleRootItem()
        new_data = {"label": "New Folder", "type": "folder", "icon": "settings.svg", "children": []}
        item = QTreeWidgetItem(parent)
        item.setText(0, new_data["label"])
        item.setData(0, Qt.UserRole, new_data)
        if parent != self.menu_tree.invisibleRootItem():
            parent.setExpanded(True)
            
    def _add_tree_action(self):
        parent = self.menu_tree.currentItem() or self.menu_tree.invisibleRootItem()
        new_data = {"label": "New Shortcut", "type": "action", "action": "NONE", "icon": "settings.svg"}
        item = QTreeWidgetItem(parent)
        item.setText(0, new_data["label"])
        item.setData(0, Qt.UserRole, new_data)
        if parent != self.menu_tree.invisibleRootItem():
            parent.setExpanded(True)
            
    def _delete_tree_node(self):
        items = self.menu_tree.selectedItems()
        if not items:
            return
        item = items[0]
        parent = item.parent() or self.menu_tree.invisibleRootItem()
        parent.removeChild(item)
        
    def _save_tree_config(self):
        def parse_item(item):
            node = item.data(0, Qt.UserRole).copy()
            if node.get("type") == "folder":
                node["children"] = []
                for i in range(item.childCount()):
                    node["children"].append(parse_item(item.child(i)))
            return node
            
        root = self.menu_tree.invisibleRootItem()
        new_layout = []
        for i in range(root.childCount()):
            new_layout.append(parse_item(root.child(i)))
            
        self.shortcuts["settings"]["menu_layout"] = new_layout
        self.menu_structure = new_layout
        self.menu_items = self._build_menu(self.menu_structure)
        self.save_config_file()

    def _load_available_icons(self):
        self.node_icon_combo.clear()
        if os.path.exists("icons"):
            for f in os.listdir("icons"):
                if f.endswith(".svg"):
                    self.node_icon_combo.addItem(f)
                    
    def _on_tree_selection(self):
        items = self.menu_tree.selectedItems()
        if not items:
            self.node_label_edit.clear()
            self.node_label_edit.setEnabled(False)
            self.node_icon_combo.setEnabled(False)
            self.node_action_combo.setEnabled(False)
            return
            
        item = items[0]
        node_data = item.data(0, Qt.UserRole)
        
        self.node_label_edit.setEnabled(True)
        self.node_icon_combo.setEnabled(True)
        
        # Block signals temporarily while updating UI from data
        self.node_label_edit.blockSignals(True)
        self.node_icon_combo.blockSignals(True)
        self.node_action_combo.blockSignals(True)
        
        self.node_label_edit.setText(node_data.get("label", ""))
        self.node_icon_combo.setCurrentText(node_data.get("icon", ""))
        
        if node_data.get("type") == "folder":
            self.node_action_combo.setEnabled(False)
            self.node_action_combo.setCurrentText("")
        else:
            self.node_action_combo.setEnabled(True)
            self.node_action_combo.setCurrentText(node_data.get("action", ""))
            
        self.node_label_edit.blockSignals(False)
        self.node_icon_combo.blockSignals(False)
        self.node_action_combo.blockSignals(False)
        
    def _on_node_edited(self):
        items = self.menu_tree.selectedItems()
        if not items:
            return
            
        item = items[0]
        node_data = item.data(0, Qt.UserRole)
        
        # Update raw dictionary
        node_data["label"] = self.node_label_edit.text()
        node_data["icon"] = self.node_icon_combo.currentText()
        
        if node_data.get("type") == "action":
            node_data["action"] = self.node_action_combo.currentText()
            
        # Update visual tree text
        item.setText(0, node_data["label"])
        item.setData(0, Qt.UserRole, node_data)

    def _populate_tree(self, nodes, parent_item):
        """Recursively convert nested dicts into QTreeWidgetItems."""
        for node in nodes:
            item = QTreeWidgetItem(parent_item)
            item.setText(0, node["label"])
            # Store the underlying data dict in a custom Role for easy retrieval
            item.setData(0, Qt.UserRole, node)
            
            if node.get("type") == "folder":
                # Ensure children exists
                if "children" not in node:
                    node["children"] = []
                self._populate_tree(node["children"], item)

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
                        self.shortcuts["settings"]["hid_path"] = data.get("hid_path", "/dev/hidraw4")
            except Exception as e:
                print(f"Failed to load config file bytes: {e}")
                        
        # Ensure menu_layout exists in settings (either loaded or new fallback initialization)
        if "menu_layout" not in self.shortcuts["settings"]:
            self.shortcuts["settings"]["menu_layout"] = [
                {
                    "label": "Music",
                    "type": "folder",
                    "icon": "musical-notes.svg",
                    "children": [
                        {"label": "PREV", "type": "action", "action": "PREVIOUSSONG", "icon": "play-skip-back.svg"},
                        {"label": "PLAY / PAUSE", "type": "action", "action": "PLAYPAUSE", "icon": "play.svg"},
                        {"label": "NEXT", "type": "action", "action": "NEXTSONG", "icon": "play-skip-forward.svg"}
                    ]
                },
                {
                    "label": "Apps",
                    "type": "folder",
                    "icon": "apps.svg",
                    "children": [
                        {"label": "Terminal", "type": "action", "action": "CTRL+ALT+T", "icon": "terminal.svg"},
                        {"label": "Browser", "type": "action", "action": "WWW", "icon": "globe.svg"}
                    ]
                },
                {
                    "label": "OS System",
                    "type": "folder",
                    "icon": "settings.svg",
                    "children": [
                        {"label": "Screenshot", "type": "action", "action": "SYSRQ", "icon": "camera.svg"},
                        {"label": "Undo", "type": "action", "action": "CTRL+Z", "icon": "arrow-undo.svg"},
                        {"label": "Redo", "type": "action", "action": "CTRL+Y", "icon": "arrow-redo.svg"}
                    ]
                }
            ]
            
        self.menu_structure = self.shortcuts["settings"]["menu_layout"]
        self.menu_items = self._build_menu(self.menu_structure)
        self.save_config_file(quiet=True)
                
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
        # Always make sure any scanners are dead
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.stop()
            
        if self.reader_thread is None or not self.reader_thread.isRunning():
            path = self.shortcuts["settings"].get("hid_path", "/dev/hidraw4")
            self.reader_thread = HidReaderThread(hid_path=path)
            self.reader_thread.raw_data_received.connect(self.log)
            self.reader_thread.wheel_event.connect(self.handle_wheel)
            self.reader_thread.click_event.connect(self.handle_click)
            self.reader_thread.error_occurred.connect(self.handle_error)
            self.reader_thread.start()
            self.value_label.setText(f"Device: Reading {path}...")
            self.log(f"Started reading on {path}.")
            
    def start_calibration(self):
        self.stop_reader()
        
        self.calibration_msg = QMessageBox(self)
        self.calibration_msg.setIcon(QMessageBox.Information)
        self.calibration_msg.setWindowTitle("Find Dial")
        self.calibration_msg.setText("Connecting scanner...")
        self.calibration_msg.setStandardButtons(QMessageBox.Cancel)
        self.calibration_msg.buttonClicked.connect(self.cancel_calibration)
        
        self.scanner_thread = HidScannerThread()
        self.scanner_thread.device_found.connect(self.on_dial_found)
        self.scanner_thread.scan_failed.connect(self.on_dial_failed)
        self.scanner_thread.progress_update.connect(self.on_calibration_progress)
        self.scanner_thread.start()
        
        self.calibration_msg.show()

    def on_calibration_progress(self, text):
        if self.calibration_msg:
            self.calibration_msg.setText(text)

    def on_dial_found(self, path):
        if self.calibration_msg:
            self.calibration_msg.accept()
            
        self.log(f"SUCCESS: Found dial at hardware path: {path}")
        self.shortcuts["settings"]["hid_path"] = path
        self.save_config_file(quiet=True)
        self.start_reader()
        
    def on_dial_failed(self, msg):
        if self.calibration_msg:
            self.calibration_msg.reject()
        self.handle_error(msg)
        
    def cancel_calibration(self, button):
        if self.scanner_thread:
            self.scanner_thread.stop()
        self.start_reader()
            
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
        if self.menu_active:
            # Menu Intercept Mode
            if direction > 0:
                self.menu_index = (self.menu_index - 1) % len(self.menu_items)
            elif direction < 0:
                self.menu_index = (self.menu_index + 1) % len(self.menu_items)
            self.osd.update_menu_selection(self.menu_index)
            return
            
        # Standard Macro Mode
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
            if self.menu_active:
                act_node = self.menu_items[self.menu_index]
                
                # Handle Back Button
                if act_node.get("action") == "__BACK__":
                    if self.menu_history:
                        self.menu_items = self.menu_history.pop()
                        self.menu_index = 0
                        self.osd.show_menu(self.menu_items, self.menu_index)
                    else:
                        # Should never be hit, but close safely if root
                        self.menu_active = False
                        self.osd.start_fade_out()
                    return

                # Handle Folder
                if act_node.get("type") == "folder":
                    self.log(f"--- ENTERING FOLDER: {act_node['label']} ---")
                    self.menu_history.append(self.menu_items)
                    self.menu_items = self._build_menu(act_node["children"])
                    self.menu_index = 0
                    self.osd.show_menu(self.menu_items, self.menu_index)
                    return

                # Handle Action (Confirm Selection)
                act = act_node.get("action", "")
                self.log(f"--- MENU CONFIRMED: {act} ---")
                
                if act:
                    self.executor.execute(act)
                
                self.menu_active = False
                
                # Reset view back to root upon exiting
                self.menu_history.clear()
                self.menu_items = self._build_menu(self.menu_structure)
                
                self.osd.start_fade_out()
            else:
                # Enter Menu Mode
                self.log(f"--- ENTERING WHEEL MENU ---")
                self.menu_active = True
                
                self.menu_index = 0
                self.osd.show_menu(self.menu_items, self.menu_index)
        else:
            self.log(f"--- DIAL RELEASED! ---")
            
    def _build_menu(self, source_list):
        items = list(source_list)
        # Deep enough that we need a back button
        if self.menu_history:
            items.append({"label": "Back", "type": "action", "action": "__BACK__", "icon": "return-up-back.svg"})
        return items

    def cancel_menu(self):
        self.log("--- MENU TIMED OUT ---")
        self.menu_active = False
