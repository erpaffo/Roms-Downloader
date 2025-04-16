#!/usr/bin/env python
import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import signal
from dotenv import load_dotenv

load_dotenv()
logging.info("Variabili d'ambiente caricate da .env (se trovato).")

from src.gui.main_window import MainWindow

def handle_sigint(*args):
    logging.warning("Ricevuto segnale SIGINT (Ctrl+C), chiusura applicazione...")
    QApplication.quit()

def main():
    signal.signal(signal.SIGINT, handle_sigint)

    app = QApplication(sys.argv)

    # Questo timer è importante per la gestione di SIGINT con Qt
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(100)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()