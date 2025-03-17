from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class DownloadQueueItemWidget(QWidget):
    def __init__(self, game):
        super().__init__()
        self.game = game
        layout = QVBoxLayout()
        self.label = QLabel(game['name'])
        layout.addWidget(self.label)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
    
    def update_progress(self, percent):
        # TODO implementare le barre di caricamento per i singoli giochi della coda da scaricare
        pass
