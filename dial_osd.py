from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtProperty, QPropertyAnimation
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QRadialGradient, QFontMetrics
from volume_utils import get_system_volume

class DialOSD(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.X11BypassWindowManagerHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.resize(200, 200)

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
        self.update_position()
        self.current_text = action_text
        self.current_vol = get_system_volume()
        
        self.anim.stop()
        self.osd_alpha = 255
        self.show()
        self.timer.start()

    def start_fade_out(self):
        self.anim.setStartValue(255)
        self.anim.setEndValue(0)
        self.anim.start()
        
    def _on_fade_finished(self):
        if self._osd_alpha == 0:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.rect().width()
        height = self.rect().height()
        
        alpha_ratio = self._osd_alpha / 255.0
        
        # Draw background bubble
        painter.setPen(Qt.NoPen)
        grad = QRadialGradient(width/2, height/2, width/2)
        grad.setColorAt(0, QColor(30, 30, 46, int(230 * alpha_ratio)))
        grad.setColorAt(0.8, QColor(30, 30, 46, int(180 * alpha_ratio)))
        grad.setColorAt(1, QColor(30, 30, 46, 0))
        painter.setBrush(grad)
        painter.drawEllipse(self.rect())
        
        # Track ring
        pen = QPen(QColor(137, 180, 250, int(60 * alpha_ratio)))
        pen.setWidth(8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        m = 20
        painter.drawArc(m, m, width - 2*m, height - 2*m, 0, 360 * 16)
        
        # Fill ring
        start_angle = 225
        span_angle = - (self.current_vol / 100.0) * 270
        pen_vol = QPen(QColor(166, 227, 161, int(230 * alpha_ratio)))
        pen_vol.setWidth(8)
        pen_vol.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_vol)
        painter.drawArc(m, m, width - 2*m, height - 2*m, start_angle * 16, int(span_angle * 16))

        # Action label
        painter.setPen(QColor(205, 214, 244, int(255 * alpha_ratio)))
        font = QFont("Inter", 12, QFont.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_width = fm.width(self.current_text)
        painter.drawText(int((width - text_width) / 2), int(height / 2 - 5), self.current_text)
        
        # Vol label
        font_vol = QFont("Inter", 10)
        painter.setFont(font_vol)
        vol_str = f"{self.current_vol}%"
        fm_vol = QFontMetrics(font_vol)
        vol_width = fm_vol.width(vol_str)
        painter.drawText(int((width - vol_width) / 2), int(height / 2 + 25), vol_str)
