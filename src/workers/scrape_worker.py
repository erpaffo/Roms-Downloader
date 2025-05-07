from PySide6.QtCore import QObject, Signal
from src import scraping


class ScrapeWorker(QObject):
    finished = Signal(list)
    progress = Signal(str)

    def __init__(self, console_name):
        super().__init__()
        self.console_name = console_name

    def run(self):
        self.progress.emit(f"Inizio scraping per '{self.console_name}'...")
        try:
            games = scraping.get_games_for_console_cached(self.console_name)
            self.progress.emit(f"Scraping completato: trovati {len(games)} giochi.")
        except Exception as e:
            self.progress.emit(f"Errore durante lo scraping: {e}")
            games = []
        self.finished.emit(games)
