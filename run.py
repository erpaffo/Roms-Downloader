#!/usr/bin/env python
from PySide6.QtWidgets import QApplication
import sys
from src.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()