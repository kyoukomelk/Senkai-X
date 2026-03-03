import fcntl
import math
import re
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtProperty, QPropertyAnimation, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QRadialGradient, QLinearGradient, QFontMetrics, QBrush
from PyQt5.QtSvg import QSvgRenderer
from volume_utils import get_system_volume

class DialOSD(QWidget):
    menu_aborted = pyqtSignal()
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.X11BypassWindowManagerHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.resize(300, 300) # Increased size to accommodate menu ring

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(800) # Wait 800ms before fading
        self.timer.timeout.connect(self.start_fade_out)
        
        self._osd_alpha = 255
        self.anim = QPropertyAnimation(self, b"osd_alpha")
        self.anim.setDuration(400)
        self.anim.finished.connect(self._on_fade_finished)
        
        self.current_text = ""
        self.current_vol = 50
        
        # Menu State
        self.in_menu_mode = False
        self.menu_options = []
        self.menu_index = 0

    @pyqtProperty(int)
    def osd_alpha(self):
        return self._osd_alpha
        
    @osd_alpha.setter
    def osd_alpha(self, val):
        self._osd_alpha = val
        self.update()

    def update_position(self):
        desktop = QApplication.desktop()
        mon = self.main_window.shortcuts["settings"].get("osd_monitor", 0)
        pos = self.main_window.shortcuts["settings"].get("osd_position", "Center")
        
        if mon >= desktop.screenCount():
            mon = desktop.primaryScreen()
            
        rect = desktop.screenGeometry(mon)
        
        m = 50 # margin
        if pos == "Top-Left":
            x = rect.x() + m
            y = rect.y() + m
        elif pos == "Top-Right":
            x = rect.x() + rect.width() - self.width() - m
            y = rect.y() + m
        elif pos == "Bottom-Left":
            x = rect.x() + m
            y = rect.y() + rect.height() - self.height() - m
        elif pos == "Bottom-Right":
            x = rect.x() + rect.width() - self.width() - m
            y = rect.y() + rect.height() - self.height() - m
        else: # Center
            x = rect.x() + (rect.width() - self.width()) // 2
            y = rect.y() + (rect.height() - self.height()) // 2 + 100
            
        self.move(x, y)

    def show_osd(self, action_text):
        self.in_menu_mode = False
        self.update_position()
        self.current_text = action_text
        self.current_vol = get_system_volume()
        
        self.anim.stop()
        self.osd_alpha = 255
        self.show()
        self.timer.start()

    def show_menu(self, options, index):
        self.in_menu_mode = True
        self.menu_options = options
        self.menu_index = index
        self.update_position()
        
        self.anim.stop()
        self.osd_alpha = 255
        self.show()
        self.timer.stop()
        
    def update_menu_selection(self, index):
        if not self.in_menu_mode: return
        self.menu_index = index
        self.update()

    def start_fade_out(self):
        self.anim.setStartValue(255)
        self.anim.setEndValue(0)
        self.anim.start()
        
    def _on_fade_finished(self):
        if self._osd_alpha == 0:
            self.hide()

    def _render_svg(self, painter, svg_name, x, y, size, colorHex):
        # Read the SVG from the local icons/ directory
        try:
            with open(f"icons/{svg_name}", 'r') as f:
                svg_data = f.read()
                
            # Strip all existing fills out
            svg_data = re.sub(r'fill="[^"]+"', '', svg_data)
            
            # Inject our target color directly into the primitive vectors because QSvgRenderer
            # struggles with CSS inheritance from the root node
            for tag in ['path', 'circle', 'rect', 'polygon']:
                svg_data = svg_data.replace(f'<{tag} ', f'<{tag} fill="{colorHex}" ')
                
            renderer = QSvgRenderer(bytearray(svg_data, encoding='utf-8'))
            renderer.render(painter, QRectF(x, y, size, size))
        except Exception as e:
            print(f"SVG Render Error for {svg_name}: {e}")
            # Fallback block if icon is missing
            painter.setBrush(QColor(colorHex))
            painter.drawRect(int(x), int(y), int(size), int(size))
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        alpha_ratio = self.osd_alpha / 255.0
        
        painter.setPen(Qt.NoPen)
        cx = width / 2
        cy = height / 2
        r_inner = 100  # Size of standard dial body
        
        padding = int((width - r_inner*2) / 2)
        
        if self.in_menu_mode and self.menu_options:
            # --- 1. Draw Outer Mockup Track (Dark Grey Solid) ---
            # Dial background track shadow
            track_r = 150
            shadow_r = track_r * 1.05
            grad = QRadialGradient(cx + 4, cy + 4, shadow_r)
            grad.setColorAt(0, QColor(0, 0, 0, int(150 * alpha_ratio)))
            grad.setColorAt(0.7, QColor(0, 0, 0, int(60 * alpha_ratio)))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(grad)
            painter.drawEllipse(int(cx + 4 - shadow_r), int(cy + 4 - shadow_r), int(shadow_r*2), int(shadow_r*2))
            
            # The thick outer circular pad
            outer_grad = QLinearGradient(0, cy - track_r, 0, cy + track_r)
            outer_grad.setColorAt(0, QColor(31, 31, 31, int(255 * alpha_ratio))) # #1f1f1f top
            outer_grad.setColorAt(1, QColor(63, 63, 63, int(255 * alpha_ratio))) # #3f3f3f bottom
            painter.setBrush(outer_grad)
            painter.drawEllipse(int(cx - track_r), int(cy - track_r), track_r*2, track_r*2)
            
            # --- 2. Center Dial Body (Slightly lighter inner circle) ---
            painter.setPen(Qt.NoPen)
            inner_grad = QLinearGradient(0, cy - r_inner, 0, cy + r_inner)
            inner_grad.setColorAt(0, QColor(47, 47, 47, int(255 * alpha_ratio))) # #2f2f2f top
            inner_grad.setColorAt(1, QColor(79, 79, 79, int(255 * alpha_ratio))) # #4f4f4f bottom
            painter.setBrush(inner_grad)
            painter.drawEllipse(int(padding), int(padding), int(r_inner*2), int(r_inner*2))
        
            # --- 3. Draw Outer Nodes (Background Track Layered) ---
            r_icons = 122 # Tucked slightly closer to the inner ring
            num_opts = len(self.menu_options)
            
            for i in range(num_opts):
                angle_offset = -90 # Start north
                angle = angle_offset + (360 / num_opts) * i
                rad = math.radians(angle)
                
                nx = cx + r_icons * math.cos(rad)
                ny = cy + r_icons * math.sin(rad)
                
                is_selected = (i == self.menu_index)
                icon_name = self.menu_options[i].get("icon", "settings.svg")
                
                if is_selected:
                    # Draw pink bounding circle for selection indicator
                    node_r = 24
                    painter.setBrush(QColor(244, 98, 244, int(255 * alpha_ratio))) # Neon pink 
                    painter.drawEllipse(int(nx - node_r), int(ny - node_r), node_r*2, node_r*2)
                
                # Draw the SVG Icon in the node slot
                svg_size = 30
                self._render_svg(painter, icon_name, nx - svg_size/2, ny - svg_size/2, svg_size, "#ffffff")

            # --- 4. Draw Center Label & Blown Up Icon ---
            sel_node = self.menu_options[self.menu_index]
            sel_text = sel_node["label"]
            sel_icon = sel_node.get("icon", "settings.svg")
            
            # Draw Large SVG
            huge_svg = 90
            self._render_svg(painter, sel_icon, cx - huge_svg/2, cy - huge_svg/2 - 15, huge_svg, "#ffffff")
            
            # Draw Text
            painter.setPen(QColor(255, 255, 255, int(255 * alpha_ratio)))
            font = QFont("Inter", 11)
            painter.setFont(font)
            fm = QFontMetrics(font)
            text_width = fm.width(sel_text)
            painter.drawText(int(cx - text_width/2), int(cy + 55), sel_text)
                
        else:
            # Standard Dial Mode (Original View)
            
            # --- 1. Draw Outer Mockup Track (Dark Grey Solid) ---
            track_r = 150
            # Dial background track shadow
            shadow_r = track_r * 1.05
            grad = QRadialGradient(cx + 4, cy + 4, shadow_r)
            grad.setColorAt(0, QColor(0, 0, 0, int(150 * alpha_ratio)))
            grad.setColorAt(0.7, QColor(0, 0, 0, int(60 * alpha_ratio)))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(grad)
            painter.drawEllipse(int(cx + 4 - shadow_r), int(cy + 4 - shadow_r), int(shadow_r*2), int(shadow_r*2))
            
            # The thick outer circular pad
            outer_grad = QLinearGradient(0, cy - track_r, 0, cy + track_r)
            outer_grad.setColorAt(0, QColor(31, 31, 31, int(255 * alpha_ratio))) # #1f1f1f top
            outer_grad.setColorAt(1, QColor(63, 63, 63, int(255 * alpha_ratio))) # #3f3f3f bottom
            painter.setBrush(outer_grad)
            painter.drawEllipse(int(cx - track_r), int(cy - track_r), track_r*2, track_r*2)
            
            # --- 2. Center Dial Body ---
            painter.setPen(Qt.NoPen)
            inner_grad = QLinearGradient(0, cy - r_inner, 0, cy + r_inner)
            inner_grad.setColorAt(0, QColor(47, 47, 47, int(255 * alpha_ratio))) # #2f2f2f top
            inner_grad.setColorAt(1, QColor(79, 79, 79, int(255 * alpha_ratio))) # #4f4f4f bottom
            painter.setBrush(inner_grad)
            painter.drawEllipse(int(padding), int(padding), int(r_inner*2), int(r_inner*2))
            
            m = padding + 20
            r_arc = r_inner*2 - 40
            
            # Track ring
            pen = QPen(QColor(137, 180, 250, int(60 * alpha_ratio)))
            pen.setWidth(8)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(m, m, r_arc, r_arc, 0, 360 * 16)
            
            # Fill ring
            start_angle = 225
            span_angle = - (self.current_vol / 100.0) * 270
            pen_vol = QPen(QColor(166, 227, 161, int(230 * alpha_ratio)))
            pen_vol.setWidth(8)
            pen_vol.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_vol)
            painter.drawArc(m, m, r_arc, r_arc, start_angle * 16, int(span_angle * 16))

            # Action label
            painter.setPen(QColor(255, 255, 255, int(255 * alpha_ratio)))
            font = QFont("Inter", 12, QFont.Bold)
            painter.setFont(font)
            fm = QFontMetrics(font)
            text_width = fm.width(self.current_text)
            painter.drawText(int(cx - text_width/2), int(cy - 5), self.current_text)
            
            # Vol label
            font_vol = QFont("Inter", 10)
            painter.setFont(font_vol)
            vol_str = f"{self.current_vol}%"
            fm_vol = QFontMetrics(font_vol)
            vol_width = fm_vol.width(vol_str)
            painter.drawText(int(cx - vol_width/2), int(cy + 25), vol_str)
