#!/usr/bin/env python
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# Carica .env dalla directory corrente o dalla directory dell'applicazione
env_path = Path('.env')
if not env_path.exists():
    env_path = Path(__file__).parent / '.env'

load_dotenv(env_path)
logging.info(f"Variabili d'ambiente caricate da {env_path} (se trovato).")

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
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
