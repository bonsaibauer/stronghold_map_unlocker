[![Repository](https://img.shields.io/badge/Repository-stronghold__map__unlocker-blue?style=flat&logo=github)](https://github.com/bonsaibauer/stronghold_map_unlocker)
![License](https://img.shields.io/badge/License-MIT-blue)
![Visitors](https://visitor-badge.laobi.icu/badge?page_id=bonsaibauer.stronghold_map_unlocker)
![Windows 10](https://img.shields.io/badge/Windows-10-0078D6?style=flat&logo=windows&logoColor=white)
![Windows 11](https://img.shields.io/badge/Windows-11%20(tested)-0078D6?style=flat&logo=windows&logoColor=white)

[![Report Problem](https://img.shields.io/badge/Report-new_Problem_or_Issue-critical?style=flat&logo=github)](https://github.com/bonsaibauer/stronghold_map_unlocker/issues/new)
![GitHub Stars](https://img.shields.io/github/stars/bonsaibauer/stronghold_map_unlocker?style=social)
![GitHub Forks](https://img.shields.io/github/forks/bonsaibauer/stronghold_map_unlocker?style=social)

## Supported / Tested Games

> This tool is designed for **Stronghold Crusader – Definitive Edition** and can work with other titles if you adjust the paths. Only SC:DE is **proven** below; the rest are unverified by this project.

| Game Title | Year | Notes | Status |
|---|---:|---|---|
| Stronghold (Original) | 2001 | Use game-specific maps folder | Not verified |
| Stronghold HD | 2013 | Remaster of Stronghold (2001) | Not verified |
| Stronghold Crusader | 2002 | Use correct game/AppID folder | Not verified |
| Stronghold Crusader HD | 2013 | Remaster of Crusader (2002) | Not verified |
| Stronghold Crusader Extreme | 2008 | Expansion | Not verified |
| Stronghold 2 | 2005 | Different map format possible | Not verified |
| Stronghold Legends | 2006 | Different map format possible | Not verified |
| Stronghold 3 | 2011 | Different map system | Not verified |
| Stronghold Kingdoms | 2012 | MMO (Workshop maps not applicable) | N/A |
| Stronghold Crusader 2 | 2014 | Different map system | Not verified |
| Stronghold: Warlords | 2021 | Different map system | Not verified |
| Stronghold: Definitive Edition | 2023 | Original Stronghold DE | Not verified |
| **Stronghold Crusader: Definitive Edition** | 2024 | Steam AppID `3024040` | **Proven ✅** |

# Stronghold Map Unlocker

A lightweight GUI tool to **unlock Stronghold maps**.  
Built for **Stronghold Crusader – Definitive Edition**, but it also works with other Stronghold titles (just adjust the paths if needed).

- Finds **Steam Workshop maps** (both numbered subfolders **and** flat folders with `.map` files directly inside).
- Copies the selected maps to your **local Maps folder** and clears the lock flag.
- Renames output to `Name [unlocked].map` (the original file is untouched).
- **Multi-language** (English/German included) — add more via simple JSON files.
- Admin check & elevation option if permissions are required.

---

## 🚀 Quick Start

1) **Run the EXE.**  
2) In the app:
   - Check/select the **Workshop folder**  
   - Check the **Destination (Maps)** path (auto-suggested)
   - **Select maps** → **Unlock**  
   The tool copies and patches only the new file in your destination; originals remain unchanged.

---

## 📂 Paths & Steam AppID

**Workshop locations (defaults):**
- `C:\Program Files (x86)\Steam\steamapps\workshop\content\3024040\`
- `C:\Program Files\Steam\steamapps\workshop\content\3024040\`

> **Note:** `3024040` is the **Steam AppID** for *Stronghold Crusader – Definitive Edition*.  
> If Steam is installed elsewhere or you use a different Stronghold title (with a different AppID),
> simply **choose the correct folder manually** in the app.

**Destination (Maps) – DE version:**
```
C:\Users\<YourName>\AppData\LocalLow\Firefly Studios\Stronghold Crusader Definitive Edition\Maps
```

---

## 🧑‍💻 Development

**Run from source (Python 3.9+):**
```bash
pip install pillow   # optional, for nicer logo scaling
python stronghold_unlocker_gui.py
```

**Install PyInstaller (and Pillow if you want nicer logo scaling):**
```
python -m pip install --upgrade pip
python -m pip install pyinstaller pillow
```

**Build an EXE (PyInstaller):**
```
pyinstaller --noconsole --onefile --clean ^
  --name stronghold_map_unlocker ^
  --icon "images/app.ico" ^
  --add-data "lang;lang" ^
  --add-data "images/CrusaderDE_Logo.png;images" ^
  --add-data "images/app.ico;images" ^
  stronghold_unlocker_gui.py
```
> On Linux/macOS use `:` instead of `;` in `--add-data`.

---

## 🤝 Contributing

### Add a language (i18n)
The app loads **all** `lang/*.json` files on startup and lists them under **Language**.  
Each language file must include a **`language_name`** field (shown in the menu).

**Example (`lang/en.json`):**
```json
{
  "language_name": "English",
  "menu_file": "File",
  "menu_language": "Language",
  "menu_help": "Help"
  /* ...see full keys in de/en JSONs in the repo */
}
```

**How to add one**
1. Create `lang/<code>.json` (e.g., `lang/es.json`).
2. Copy the structure from `lang/en.json`, set `language_name`, and translate keys.
3. Start the app — the language appears automatically under **Language**.

### Dev tips
- Python 3.9+, tkinter (Pillow optional).
- Keep user-facing strings in `lang/*.json` (app title stays fixed).
- Windows paths & permissions in mind; the app can restart with elevation if needed.

---

## 🐞 Report an Issue

👉 https://github.com/bonsaibauer/stronghold_map_unlocker/issues/new

If possible, include **log excerpts**, **paths** (no private data), and **repro steps**.

---

## ⚠️ Disclaimer

This project (“Stronghold Map Unlocker”) is **not affiliated** with **Firefly Studios** or the official games such as **Stronghold**, **Stronghold Crusader**, etc.  
It is a **private, non-commercial fan project** developed independently.

---

## 📜 License & Credits

This project is released under the **MIT License**. See [`LICENSE`](LICENSE).  
© bonsaibauer 2025 — Repo: https://github.com/bonsaibauer/stronghold_map_unlocker

---

## Buy Me A Coffee
If this project has helped you in any way, do buy me a coffee so I can continue to build more of such projects in the future and share them with the community!

<a href="https://buymeacoffee.com/bonsaibauer" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
