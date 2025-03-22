from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QListWidget
from PySide6.QtCore import Qt
from src.gui.download_queue_item import DownloadQueueItemWidget

class RomsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.active_widgets = {}  # game_name -> widget
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Sezione: Download Globale
        global_label = QLabel("Download Globale:")
        main_layout.addWidget(global_label)
        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setMinimum(0)
        self.global_progress_bar.setMaximum(100)
        self.global_progress_bar.setValue(0)
        main_layout.addWidget(self.global_progress_bar)
        self.global_stats_label = QLabel("Velocità Globale: 0.0 MB/s, Picco Globale: 0.0 MB/s")
        main_layout.addWidget(self.global_stats_label)
        
        # Sezione: Download Attivi
        active_label = QLabel("Download Attivi:")
        main_layout.addWidget(active_label)
        self.active_downloads_container = QWidget()
        self.active_downloads_layout = QVBoxLayout()
        self.active_downloads_container.setLayout(self.active_downloads_layout)
        main_layout.addWidget(self.active_downloads_container)
        
        # Sezione: Coda Download
        queue_label = QLabel("Coda Download:")
        main_layout.addWidget(queue_label)
        self.queue_list = QListWidget()
        main_layout.addWidget(self.queue_list)
        
        # Sezione: Download Completati
        completed_label = QLabel("Download Completati:")
        main_layout.addWidget(completed_label)
        self.completed_list = QListWidget()
        main_layout.addWidget(self.completed_list)
        
        self.setLayout(main_layout)
    
    def add_active_download(self, game_name):
        """Crea un widget per il download attivo se non esiste e lo restituisce."""
        if game_name not in self.active_widgets:
            widget = DownloadQueueItemWidget({"name": game_name})
            self.active_downloads_layout.addWidget(widget)
            self.active_widgets[game_name] = widget
            return widget
        return self.active_widgets[game_name]
    
    def update_active_download(self, game_name, percent):
        if game_name in self.active_widgets:
            self.active_widgets[game_name].update_progress(percent)
    
    def update_active_stats(self, game_name, speed, peak):
        if game_name in self.active_widgets:
            self.active_widgets[game_name].update_stats(speed, peak)
    
    def remove_active_download(self, game_name):
        if game_name in self.active_widgets:
            widget = self.active_widgets.pop(game_name)
            widget.setParent(None)
            widget.deleteLater()
    
    def add_to_queue(self, game_name):
        self.queue_list.addItem(game_name)
    
    def remove_from_queue(self, game_name):
        items = self.queue_list.findItems(game_name, Qt.MatchExactly)
        for item in items:
            row = self.queue_list.row(item)
            self.queue_list.takeItem(row)
    
    def add_completed_download(self, game_name):
        self.completed_list.addItem(game_name)
    
    def update_global_progress(self, downloaded, total, global_speed, global_peak):
        """Aggiorna la barra globale e le statistiche globali.
           downloaded e total sono in byte, global_speed e global_peak in MB/s."""
        percent = int(downloaded / total * 100) if total > 0 else 0
        self.global_progress_bar.setValue(percent)
        self.global_stats_label.setText(f"Velocità Globale: {global_speed:.1f} MB/s, Picco Globale: {global_peak:.1f} MB/s")
