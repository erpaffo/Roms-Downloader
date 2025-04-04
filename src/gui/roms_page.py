from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QProgressBar, QListWidget, QGroupBox,
                               QScrollArea)
from PySide6.QtCore import Qt
from PySide6 import QtGui
from src.gui.download_queue_item import DownloadQueueItemWidget
import logging

class RomsPage(QWidget):
    """
    GUI page dedicated to displaying and managing the status of downloads
    (active, queued, completed).
    Corrected version maintaining the embellished structure but using
    the original (working) logic for adding/removing active widgets.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_widgets = {}
        self.init_ui()

    def init_ui(self):
        """Initializes the user interface of the page."""
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
        Creates and adds a widget for a new active download,
        if it doesn't already exist. Uses the original 'addWidget' logic.
        Returns the created or existing widget.
        """
        widget = self.active_widgets.get(game_name)
        if not widget:
            game_data = {"name": game_name}
            widget = DownloadQueueItemWidget(game_data)
            self.active_downloads_layout.addWidget(widget)
            self.active_widgets[game_name] = widget
            logging.debug(f"RomsPage: Added active widget for {game_name}")
            return widget

        logging.debug(f"RomsPage: Active widget for {game_name} already exists.")
        return widget


    def update_active_download(self, game_name, percent):
        """Updates the progress bar of the specified active widget."""
        widget = self.active_widgets.get(game_name)
        if widget:
            if hasattr(widget, 'update_progress'):
                widget.update_progress(percent)
            else:
                 logging.warning(f"Widget for {game_name} does not have 'update_progress' method.")


    def update_active_stats(self, game_name, speed_mb, peak_mb):
        """Updates the statistics (speed, peak) of the specified active widget."""
        widget = self.active_widgets.get(game_name)
        if widget:
             if hasattr(widget, 'update_stats'):
                try:
                    widget.update_stats(float(speed_mb), float(peak_mb))
                except (ValueError, TypeError):
                    logging.warning(f"Invalid stats values for {game_name}: speed={speed_mb}, peak={peak_mb}")
                    widget.update_stats(0.0, 0.0)
             else:
                 logging.warning(f"Widget for {game_name} does not have 'update_stats' method.")


    def remove_active_download(self, game_name):
        """
        Removes the widget for an active download from the interface.
        Uses the original logic.
        """
        widget = self.active_widgets.pop(game_name, None)
        if widget:
            logging.debug(f"RomsPage: Removing widget for {game_name}.")
            try:
                widget.setParent(None)
                widget.deleteLater()
                logging.debug(f"RomsPage: Widget for {game_name} removed and scheduled for deleteLater.")
            except Exception as e:
                logging.error(f"Error during removal/deletion of widget for {game_name}: {e}")


    def add_to_queue(self, game_name):
        """Adds a game name to the visual queue list."""
        self.queue_list.addItem(game_name)
        self.queue_list.scrollToBottom()

    def remove_from_queue(self, game_name):
        """Removes a game from the visual queue list."""
        items = self.queue_list.findItems(game_name, Qt.MatchFlag.MatchExactly)
        if items:
            row = self.queue_list.row(items[0])
            self.queue_list.takeItem(row)

    def add_completed_download(self, game_name_with_info):
        """Adds an entry to the completed downloads list."""
        self.completed_list.addItem(game_name_with_info)
        self.completed_list.scrollToBottom()

    def update_global_progress(self, downloaded, total, global_speed_mb, global_peak_mb):
        """
        Updates the global progress bar and global statistics labels.
        Speed and peak are expected in MB/s.
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