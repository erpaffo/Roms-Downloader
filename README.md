# 🎮 ROMs Downloader - GUI Application

**ROMs Downloader** è un'applicazione desktop realizzata in Python che permette di scaricare, gestire e avviare giochi per diverse console Nintendo direttamente dal desktop. Include funzionalità di scraping automatico, download concorrenti, gestione della coda di download, avvio rapido dei giochi con emulatori e gestione della libreria personale di giochi scaricati.

---

## ⚙️ Caratteristiche principali

- **Scraping automatico** dei giochi Nintendo (3DS, DS, Game Boy Advance, Game Boy) da [myrient.erista.me](https://myrient.erista.me/files/).
- **Download multipli e concorrenti** con statistiche avanzate: velocità di download, picco massimo, progresso globale e singolo file.
- **Gestione della coda di download** con funzionalità di aggiunta/rimozione e annullamento singolo o completo dei download in corso.
- **Libreria integrata** per gestire, ordinare, filtrare e avviare rapidamente i giochi già scaricati.
- **Supporto integrato per emulatori** (RetroArch e altri emulatori come Citra, DraStic, mGBA, Sameboy, ecc.).
- **Interfaccia Grafica (GUI)** moderna e intuitiva sviluppata con PySide6.

---

## 🚀 Installazione

### 📌 1. Clona il Repository

```bash
git clone <url_del_tuo_repo>
cd nome_cartella_progetto
```

### 📌 2. Installa le dipendenze

Si consiglia l'uso di un ambiente virtuale Python (venv):

```bash
python -m venv venv
venv\Scripts\activate (Windows)
source venv/bin/activate (Linux/Mac)
pip install -r requirements.txt
```

Assicurati che `requirements.txt` includa almeno:

```
PySide6
requests
beautifulsoup4
```

### 📌 3. Configurazione degli Emulatori

Modifica il file di configurazione `src/config.py` impostando i percorsi o i nomi degli emulatori presenti sul tuo sistema:

```python
# src/config.py
EMULATOR_3DS_NAME = "citra"
EMULATOR_NDS_NAME = "drastic"
EMULATOR_GBA_NAME = "mgba"
EMULATOR_GB_NAME = "mgba"
```

Puoi usare RetroArch definendo un percorso assoluto, ad esempio:

```python
RETROARCH_NAME = r"C:\RetroArch-Win64\retroarch.exe"
```

### 📌 4. Avvio dell'applicazione

```bash
python run.py
```

---

## 🎯 Utilizzo

### 🔹 Navigazione tra le sezioni:

- **Download Manager**: Cerca e scarica ROM dai vari sistemi supportati. Puoi filtrare per nazione, ordinare per nome o peso e avviare più download contemporaneamente.
- **Library**: Visualizza, ordina, filtra e avvia rapidamente i giochi scaricati direttamente con l'emulatore selezionato.
- **ROMS Page**: Controlla e gestisci la coda download, i download in corso e quelli completati.

### 🔹 Funzionalità della tabella:

- Clicca sulle colonne "Nome" o "Peso" per ordinare i risultati.
- Usa la barra di ricerca avanzata per cercare parole o frammenti nei titoli dei giochi.
- Usa il filtro per nazione per restringere rapidamente la ricerca a una regione specifica.

### 🔹 Libreria integrata:

- Doppio clic su un gioco nella libreria per avviarlo con l'emulatore associato. (TODO)
- Usa il pulsante "Refresh" per aggiornare la lista dei giochi nella libreria.

---

## 📂 Struttura del Progetto

```plaintext
Scraper/
├── cache/                     # Cache per risultati dello scraping
├── downloads/                 # Giochi scaricati suddivisi per console
├── src/
│   ├── config.py              # Configurazione globale del progetto
│   ├── gui/                   # Componenti dell'interfaccia utente
│   │   ├── download_queue_item.py
│   │   ├── library_page.py
│   │   ├── main_window.py
│   │   ├── progress_widget.py
│   │   └── roms_page.py
│   ├── utils.py               # Funzioni di utilità generali
│   └── workers/               # Gestori per scraping e download
│       ├── download_manager.py
│       ├── download_worker.py
│       └── scrape_worker.py
├── requirements.txt           # Dipendenze Python del progetto
└── run.py                     # File principale per avviare l'applicazione
```

---

## 📌 Librerie Usate

- **PySide6**: framework per la GUI.
- **requests**: per eseguire chiamate HTTP.
- **beautifulsoup4**: per scraping dei dati.
- **logging**: per loggare eventi significativi.

---

## 📜 Licenza

Distribuito sotto licenza **MIT**. Usa e modifica liberamente questo software secondo i termini della licenza.

---

