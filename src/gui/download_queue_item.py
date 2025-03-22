from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar

class DownloadQueueItemWidget(QWidget):
    def __init__(self, game):
        super().__init__()
        self.game = game
        layout = QVBoxLayout()
        self.label = QLabel(game['name'])
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        # Nuove etichette per le statistiche
        self.speed_label = QLabel("Velocità: 0.0 MB/s")
        self.peak_label = QLabel("Picco: 0.0 MB/s")
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.peak_label)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
    
    def update_progress(self, percent):
        self.progress_bar.setValue(percent)
    
    def update_stats(self, speed, peak):
        """speed e peak sono in MB/s"""
        self.speed_label.setText(f"Velocità: {speed:.1f} MB/s")
        self.peak_label.setText(f"Picco: {peak:.1f} MB/s")
