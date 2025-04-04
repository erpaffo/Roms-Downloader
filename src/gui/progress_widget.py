from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar

class ProgressWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.single_file_label = QLabel("Download corrente:")
        self.single_file_progress = QProgressBar()
        self.single_file_label = QLabel("Nessun file in download.")

        self.global_label = QLabel("Progresso totale:")
        self.global_progress_bar = QProgressBar()
        
        layout.addStretch()

        self.setLayout(layout)

    def update_file_progress(self, file_name, percent):
        self.single_file_label.setText(f"{file_name}: {percent}%")
        self.global_progress_bar.setValue(percent)

    def update_global_progress(self, percent):
        self.global_progress_bar.setValue(percent)
