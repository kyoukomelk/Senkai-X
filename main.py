import sys
from PyQt5.QtWidgets import QApplication
from gui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Do not quit when the window is closed if the tray icon is active
    app.setQuitOnLastWindowClosed(False)
    
    window = MainWindow()
    
    # Just run in background by default, user can open from tray
    sys.exit(app.exec_())
