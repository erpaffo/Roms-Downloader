from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QProgressBar, QListWidget, QGroupBox,
                               QScrollArea)
from PySide6.QtCore import Qt
from PySide6 import QtGui
from src.gui.download_queue_item import DownloadQueueItemWidget
import logging

class RomsPage(QWidget):
    """
    Pagina della GUI dedicata alla visualizzazione e gestione
    dello stato dei download (attivi, in coda, completati).
    Versione corretta che mantiene la struttura abbellita ma usa la logica
    originale (funzionante) per add/remove dei widget attivi.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_widgets = {}
        self.init_ui()

    def init_ui(self):
        """Inizializza l'interfaccia utente della pagina."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        global_group = QGroupBox("Progresso Globale")
        global_group.setObjectName("DownloadGroup")
        global_layout = QVBoxLayout(global_group)
        global_layout.setSpacing(5)

        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setObjectName("GlobalProgressBar")
        self.global_progress_bar.setMinimum(0)
        self.global_progress_bar.setMaximum(100)
        self.global_progress_bar.setValue(0)
        self.global_progress_bar.setTextVisible(True)
        global_layout.addWidget(self.global_progress_bar)

        self.global_stats_label = QLabel("Velocità: 0.0 MB/s, Picco: 0.0 MB/s")
        self.global_stats_label.setObjectName("GlobalStatsLabel")
        global_layout.addWidget(self.global_stats_label)
        main_layout.addWidget(global_group)

        active_group = QGroupBox("Download Attivi")
        active_group.setObjectName("DownloadGroup")
        active_group_layout = QVBoxLayout(active_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("ActiveDownloadsScroll")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.active_downloads_container = QWidget()
        self.active_downloads_container.setObjectName("ActiveDownloadsContainer")
        self.active_downloads_layout = QVBoxLayout(self.active_downloads_container)
        self.active_downloads_layout.setContentsMargins(5, 5, 5, 5)
        self.active_downloads_layout.setSpacing(5)

        scroll_area.setWidget(self.active_downloads_container)
        active_group_layout.addWidget(scroll_area)
        main_layout.addWidget(active_group, 1)

        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(15)

        queue_group = QGroupBox("Coda Download")
        queue_group.setObjectName("DownloadGroup")
        queue_layout = QVBoxLayout(queue_group)
        self.queue_list = QListWidget()
        self.queue_list.setObjectName("QueueList")
        self.queue_list.setMaximumHeight(150)
        queue_layout.addWidget(self.queue_list)
        lists_layout.addWidget(queue_group)

        completed_group = QGroupBox("Download Completati")
        completed_group.setObjectName("DownloadGroup")
        completed_layout = QVBoxLayout(completed_group)
        self.completed_list = QListWidget()
        self.completed_list.setObjectName("CompletedList")
        self.completed_list.setMaximumHeight(150)
        completed_layout.addWidget(self.completed_list)
        lists_layout.addWidget(completed_group)

        main_layout.addLayout(lists_layout)


    def add_active_download(self, game_name):
        """
        Crea e aggiunge un widget per un nuovo download attivo,
        se non esiste già. Usa la logica originale 'addWidget'.
        Restituisce il widget creato o esistente.
        """
        widget = self.active_widgets.get(game_name)
        if not widget:
            game_data = {"name": game_name}
            widget = DownloadQueueItemWidget(game_data)
            self.active_downloads_layout.addWidget(widget)
            self.active_widgets[game_name] = widget
            logging.debug(f"RomsPage: Aggiunto widget attivo per {game_name}")
            return widget

        logging.debug(f"RomsPage: Widget attivo per {game_name} già esistente.")
        return widget


    def update_active_download(self, game_name, percent):
        """Aggiorna la barra di progresso del widget attivo specificato."""
        widget = self.active_widgets.get(game_name)
        if widget:
            if hasattr(widget, 'update_progress'):
                widget.update_progress(percent)
            else:
                 logging.warning(f"Widget per {game_name} non ha il metodo 'update_progress'.")


    def update_active_stats(self, game_name, speed_mb, peak_mb):
        """Aggiorna le statistiche (velocità, picco) del widget attivo specificato."""
        widget = self.active_widgets.get(game_name)
        if widget:
             if hasattr(widget, 'update_stats'):
                try:
                    widget.update_stats(float(speed_mb), float(peak_mb))
                except (ValueError, TypeError):
                    logging.warning(f"Valori stats non validi per {game_name}: speed={speed_mb}, peak={peak_mb}")
                    widget.update_stats(0.0, 0.0)
             else:
                 logging.warning(f"Widget per {game_name} non ha il metodo 'update_stats'.")


    def remove_active_download(self, game_name):
        """
        Rimuove il widget per un download attivo dall'interfaccia.
        Usa la logica originale.
        """
        widget = self.active_widgets.pop(game_name, None)
        if widget:
            logging.debug(f"RomsPage: Rimuovendo widget per {game_name}.")
            try:
                widget.setParent(None)
                widget.deleteLater()
                logging.debug(f"RomsPage: Widget per {game_name} rimosso e schedulato per deleteLater.")
            except Exception as e:
                logging.error(f"Errore durante la rimozione/eliminazione del widget per {game_name}: {e}")


    def add_to_queue(self, game_name):
        """Aggiunge un nome di gioco alla lista della coda visiva."""
        self.queue_list.addItem(game_name)
        self.queue_list.scrollToBottom()

    def remove_from_queue(self, game_name):
        """Rimuove un gioco dalla lista della coda visiva."""
        items = self.queue_list.findItems(game_name, Qt.MatchFlag.MatchExactly)
        if items:
            row = self.queue_list.row(items[0])
            self.queue_list.takeItem(row)

    def add_completed_download(self, game_name_with_info):
        """Aggiunge una voce alla lista dei download completati."""
        self.completed_list.addItem(game_name_with_info)
        self.completed_list.scrollToBottom()

    def update_global_progress(self, downloaded, total, global_speed_mb, global_peak_mb):
        """
        Aggiorna la barra di progresso globale e le statistiche globali.
        Velocità e picco sono attesi in MB/s.
        """
        percent = int(downloaded / total * 100) if total > 0 else 0
        percent = min(percent, 100)
        self.global_progress_bar.setValue(percent)

        try:
             speed_str = f"{float(global_speed_mb):.1f} MB/s"
             peak_str = f"{float(global_peak_mb):.1f} MB/s"
        except (ValueError, TypeError):
             speed_str = "N/A"
             peak_str = "N/A"
        self.global_stats_label.setText(f"Velocità Globale: {speed_str}, Picco Globale: {peak_str}")