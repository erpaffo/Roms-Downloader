from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar

class DownloadQueueItemWidget(QWidget):
    def __init__(self, game):
        super().__init__()
        self.game = game
        layout = QVBoxLayout()
        game_name = game.get('name', 'Download Sconosciuto')
        self.label = QLabel(game_name)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(f"%p% - {game_name}") 

        self.speed_label = QLabel("Velocità: 0.0 MB/s")
        self.peak_label = QLabel("Picco: 0.0 MB/s")

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.peak_label)
        layout.setContentsMargins(5, 5, 5, 5) # Margini interni
        layout.setSpacing(3) # Spaziatura ridotta tra elementi
        self.setLayout(layout)

    def update_progress(self, percent):
        try:
            self.progress_bar.setValue(int(percent))
        except ValueError:
             self.progress_bar.setValue(0)


    def update_stats(self, speed, peak):
        """Updates speed and peak labels. Speed and peak are in MB/s."""
        try:
            self.speed_label.setText(f"Velocità: {float(speed):.1f} MB/s")
            self.peak_label.setText(f"Picco: {float(peak):.1f} MB/s")
        except (ValueError, TypeError):
            self.speed_label.setText("Velocità: N/A")
            self.peak_label.setText("Picco: N/A")