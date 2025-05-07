# Roms-Downloader

A cross-platform graphical application (Linux, Windows, macOS) built with Python and PySide6 to search, download, and manage ROMs, with integration for RetroArch.

## ✨ Features

* User-friendly graphical interface.
* Search and download ROMs (Specify consoles if possible).
* Manage your local ROM library.
* Integrated download queue.
* ROM information scraping (metadata, covers, etc.) (*Verify if implemented*).
* RetroArch integration configuration (cores, paths, etc.) (*Verify if implemented*).
* Cross-platform support: Linux, Windows, macOS.

## ✅ Prerequisites

To actually *play* the games downloaded using Roms-Downloader via its integration features, you need to have **RetroArch** installed on your system. Roms-Downloader helps manage and download ROMs, but relies on RetroArch for the emulation itself.

* **RetroArch Installation:** Please download and install RetroArch for your operating system from the official website:
    * Main Site: [https://www.retroarch.com/](https://www.retroarch.com/)

*(Note: On Arch Linux and derivatives, RetroArch is automatically installed as a dependency when using the provided `.pkg.tar.zst` package).*

On MacOs ensure to have Retroarch in the **Application Folder** 

## 🚀 Installation

You can download the latest release for your operating system from the [Releases]([link/to/releases]) page. ### Linux (Arch Linux / EndeavourOS / Derivatives)

1.  Ensure `python` is installed (RetroArch will be installed as a dependency):
    ```bash
    sudo pacman -S --needed python
    ```
2.  Download the latest `.pkg.tar.zst` file from the [Releases]([link/to/releases]) page.
3.  Install the package using pacman (replace `[...]` with the downloaded version):
    ```bash
    sudo pacman -U roms-downloader-[...].pkg.tar.zst
    ```

### Windows

1.  Download the latest `RomsDownloader_Setup_vX.X.exe` file from the [Releases]([link/to/releases]) page.
2.  Run the downloaded installer (`.exe`) and follow the on-screen instructions.
3.  *Remember to install RetroArch separately (see Prerequisites).*

### macOS

1.  Download the latest `RomsDownloader_Installer.dmg` file from the [Releases]([link/to/releases]) page.
2.  Open the `.dmg` file.
3.  Drag the `RomsDownloader.app` icon to your `Applications` folder (or preferred location).
4.  (Optional) Eject the disk image from Finder.
5.  *Remember to install RetroArch separately (see Prerequisites).*

## 🎮 Usage

After installation (and ensuring RetroArch is installed):

* **Linux:** Find and launch "Roms Downloader" from your desktop environment's application menu, or run `romsdownloader` in a terminal.
* **Windows:** Launch "Roms Downloader" from the Start Menu or the Desktop shortcut (if created during installation).
* **macOS:** Launch "RomsDownloader" from your Applications folder (or wherever you copied it).

Once the application is running, you can navigate the sections to search for new ROMs, manage your existing library, configure settings, and potentially launch games via RetroArch integration.

## 📋 Requirements (for building from source)

* Python 3.x
* PySide6
* Other Python dependencies (see `requirements.txt` - *Ensure this file exists and is up-to-date*)
* RetroArch (runtime dependency for some features, especially on Linux)

## 🛠️ Building from Source (Developer Instructions)

If you prefer to run or modify the application directly from the source code:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/erpaffo/Roms-Downloader.git](https://github.com/erpaffo/Roms-Downloader.git)
    cd Roms-Downloader
    ```
    *Note: Verify that `Roms-Downloader` is the correct repository name.*
2.  **Create and activate a Python virtual environment:**
    ```bash
    # Create environment (use python3 or python depending on your system)
    python3 -m venv venv
    # Activate environment
    # Linux/macOS:
    source venv/bin/activate
    # Windows (Git Bash):
    # source venv/Scripts/activate
    # Windows (Command Prompt):
    # .\venv\Scripts\activate.bat
    # Windows (PowerShell):
    # .\venv\Scripts\Activate.ps1
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Ensure `requirements.txt` exists and lists all needed libraries.*
4.  **Run the application:**
    ```bash
    python run.py
    ```

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for full details. ## ❤️ Contributing

Contributions are welcome! If you find bugs or have ideas for new features, please feel free to open an issue or submit a pull request on the [GitHub repository](https://github.com/erpaffo/Roms-Downloader). ```

I've added the "Prerequisites" section and also slightly modified the Windows/macOS installation instructions to remind users there about installing RetroArch separately. I also clarified the Linux dependency installation step.