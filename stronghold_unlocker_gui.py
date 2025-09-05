#!/usr/bin/env python3
# stronghold_unlocker_gui.py
# GUI unlocker for Stronghold Crusader DE maps.

import os
import sys
import threading
import webbrowser
from pathlib import Path
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import json  # i18n + config

# Optional: Pillow for high-quality image scaling
try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

# ----------------------------
# Constants / Links
# ----------------------------
WORKSHOP_CANDIDATES = [
    r"C:\Program Files (x86)\Steam\steamapps\workshop\content\3024040",
    r"C:\Program Files\Steam\steamapps\workshop\content\3024040",
]

def _default_dest():
    # Zielordner relativ zum aktuellen Benutzer (Windows LocalLow)
    return str(Path.home() / r"AppData\LocalLow\Firefly Studios\Stronghold Crusader Definitive Edition\Maps")

GH_USER    = "bonsaibauer"
GH_REPO    = "stronghold_map_unlocker"
URL_REPO   = f"https://github.com/{GH_USER}/{GH_REPO}"
URL_README = URL_REPO + "#readme"
URL_ISSUE  = URL_REPO + "/issues/new"
URL_USER   = f"https://github.com/{GH_USER}"

APP_TITLE   = "Stronghold Map Unlocker"
APP_VERSION = "1.0.0"
COPYRIGHT   = "© bonsaibauer 2025"

# Asset relative paths (we resolve them via resource_path)
LOGO_FILE = "images/CrusaderDE_Logo.png"
ICON_FILE = "images/app.ico"

# ----------------------------
# Resource helpers (work for script & PyInstaller EXE)
# ----------------------------
def resource_path(rel: str) -> Path:
    """
    Find a resource file both when running from source and when frozen by PyInstaller.
    Search order:
    1) MEIPASS/<rel>
    2) <exe_dir>/<rel>
    3) <script_dir>/<rel>
    """
    rel_path = Path(rel)
    base_candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_candidates.append(Path(sys._MEIPASS))
    if getattr(sys, "frozen", False):
        base_candidates.append(Path(sys.executable).parent)
    base_candidates.append(Path(__file__).parent)

    for base in base_candidates:
        p = (base / rel_path).resolve()
        if p.exists():
            return p
    return (base_candidates[-1] / rel_path).resolve()

def language_dirs() -> list[Path]:
    """Return possible language directories to search (MEIPASS/lang, exe_dir/lang, script_dir/lang)."""
    dirs = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        dirs.append(Path(sys._MEIPASS) / "lang")
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).parent / "lang")
    dirs.append(Path(__file__).parent / "lang")
    out, seen = [], set()
    for d in dirs:
        rp = d.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out

def images_path(rel: str) -> Path:
    return resource_path(f"images/{rel}")

# ----------------------------
# Config helpers
# ----------------------------
def config_dir() -> Path:
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA")
        if base:
            return Path(base) / "bonsaibauer" / "stronghold_map_unlocker"
    return Path.home() / ".stronghold_map_unlocker"

def load_config() -> dict:
    try:
        p = config_dir() / "config.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_config(cfg: dict):
    try:
        d = config_dir()
        d.mkdir(parents=True, exist_ok=True)
        p = d / "config.json"
        p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

# ----------------------------
# Core unlocking logic
# ----------------------------
class MapUnlocker:
    @staticmethod
    def read_u16_le_at(f, off: int) -> int:
        f.seek(off)
        b = f.read(2)
        if len(b) != 2:
            raise ValueError(f"Unexpected EOF at 0x{off:X}")
        return int.from_bytes(b, "little")

    @staticmethod
    def compute_base(path: Path) -> int:
        with open(path, "rb") as f:
            A = MapUnlocker.read_u16_le_at(f, 0x04)
            B = MapUnlocker.read_u16_le_at(f, A + 0x08)
            return A + 0x3C + B

    @staticmethod
    def read_byte_at(path: Path, off: int) -> int:
        with open(path, "rb") as f:
            f.seek(off)
            b = f.read(1)
            if len(b) != 1:
                raise ValueError(f"Unexpected EOF at 0x{off:X}")
            return b[0]

    @staticmethod
    def write_byte_at(path: Path, off: int, value: int):
        with open(path, "r+b") as f:
            f.seek(off)
            f.write(bytes([value & 0xFF]))

    @staticmethod
    def build_unlocked_name(src: Path, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        stem = src.stem
        ext = src.suffix or ".map"
        out = dest_dir / f"{stem} [unlocked]{ext}"
        i = 2
        while out.exists():
            out = dest_dir / f"{stem} [unlocked] ({i}){ext}"
            i += 1
        return out

    @staticmethod
    def copy_and_unlock(src: Path, dest_dir: Path):
        """Copy src to dest_dir with [unlocked].map suffix and patch BASE+0x08 = 0x00."""
        import shutil
        out = MapUnlocker.build_unlocked_name(src, dest_dir)
        shutil.copy2(src, out)

        base = MapUnlocker.compute_base(out)
        target = base + 0x08
        before = MapUnlocker.read_byte_at(out, target)
        MapUnlocker.write_byte_at(out, target, 0x00)
        after = MapUnlocker.read_byte_at(out, target)
        status = "OK" if after == 0x00 else "MISMATCH"

        log = []
        log.append(f"Copied -> {out}")
        log.append(f"BASE=0x{base:X}  TARGET=0x{target:X}")
        log.append(f"Byte before: {before:02X}  after: {after:02X}  [{status}]")
        return out, "\n".join(log)

# ----------------------------
# Workshop scanner
# ----------------------------
@dataclass
class MapEntry:
    display: str
    fullpath: Path

class WorkshopScanner:
    @staticmethod
    def scan(workshop_root: Path):
        """
        Supports two layouts:
        1) Steam Workshop root with numbered subfolders containing .map files
        2) Any folder where .map files lie directly in the root (no subfolders)
        We scan RECURSIVELY and also include maps directly in the root.
        """
        entries = []
        if not workshop_root.exists():
            return entries

        # Collect all *.map recursively, including the root itself.
        try:
            maps = sorted(
                workshop_root.rglob("*.map"),
                key=lambda p: (p.name.lower(), str(p.parent).lower())
            )
        except Exception:
            maps = []

        # If rglob failed (rare), try non-recursive as fallback
        if not maps:
            maps = sorted(workshop_root.glob("*.map"), key=lambda p: p.name.lower())

        for p in maps:
            # Show only file name (as requested)
            entries.append(MapEntry(display=p.name, fullpath=p))

        return entries

# ----------------------------
# i18n (dynamic discovery)
# ----------------------------
class I18n:
    def __init__(self):
        self.cache = {}
        self.roots = language_dirs()

    def load(self, code: str) -> dict:
        for root in self.roots:
            path = root / f"{code}.json"
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self.cache[code] = data
                    return data
                except Exception:
                    pass
        return {}

    def list_languages(self):
        """Return unique (code, name) from all lang roots. name is 'language_name' or the code."""
        found = {}
        for root in self.roots:
            if not root.exists():
                continue
            for file in sorted(root.glob("*.json")):
                code = file.stem
                try:
                    data = json.loads(file.read_text(encoding="utf-8"))
                    name = data.get("language_name", code)
                except Exception:
                    name = code
                if code not in found:
                    found[code] = name
        return [(c, n) for c, n in sorted(found.items(), key=lambda x: x[0])]

# ----------------------------
# GUI Application
# ----------------------------
class UnlockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # App title is fixed (not localized)
        self.title(f"{APP_TITLE} – v{APP_VERSION}")
        self._set_window_icon()
        self.geometry("1020x720")
        self.minsize(920, 560)

        # Load config (language + last paths)
        self.config_data = load_config()

        # Path variables
        default_workshop = self.config_data.get("workshop") or WORKSHOP_CANDIDATES[0]
        default_dest     = self.config_data.get("dest") or _default_dest()
        self.workshop_var = tk.StringVar(value=default_workshop)
        self.dest_var     = tk.StringVar(value=default_dest)

        self._entries = []  # type: list[MapEntry]
        self._logo_img = None
        self._icon_img = None
        self._did_auto_prompt = False

        # i18n
        self.i18n = I18n()
        discovered = self.i18n.list_languages()
        codes = [c for c,_ in discovered]
        cfg_lang = self.config_data.get("language")
        default_lang = cfg_lang if cfg_lang in codes else ("en" if "en" in codes else ("de" if "de" in codes else (codes[0] if codes else "en")))
        self.lang = default_lang
        self.t = {}
        self._load_language(self.lang)
        self.lang_var = tk.StringVar(value=self.lang)  # radio state

        # Build UI
        self._build_menu()
        self._build_body()

        # Admin info
        self._log(self.T("logs_admin_rights", yesno=("Yes" if self._is_admin() else "No")))

        # Auto resolve workshop path & refresh
        self._auto_select_workshop()
        self._refresh_list()

        # Ensure footer visible after dynamic wraps
        self.after(0, self._ensure_statusbar_visible)

        # Save config on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- Language helpers -----
    def _load_language(self, code: str):
        data = self.i18n.load(code) or self.i18n.load('de') or {}
        self.lang = code if data else 'de'
        self.t = data

    def T(self, key: str, **kwargs) -> str:
        s = self.t.get(key, key)
        try:
            return s.format(**kwargs)
        except Exception:
            return s

    def _set_language(self, code: str):
        if code == self.lang:
            return
        self._load_language(code)
        self.lang_var.set(self.lang)
        self._rebuild_ui()

    def _rebuild_ui(self):
        # reset title (fixed)
        self.title(f"{APP_TITLE} – v{APP_VERSION}")
        # clear all children and rebuild
        for child in self.winfo_children():
            child.destroy()
        self._build_menu()
        self._build_body()
        self._refresh_list()
        self.after(0, self._ensure_statusbar_visible)

    # ----- Privilege helpers -----
    def _is_admin(self) -> bool:
        if os.name != "nt":
            return True
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _restart_as_admin(self):
        if os.name != "nt":
            messagebox.showinfo(self.T("menu_help"), self.T("dialogs_admin_restart_only_windows"))
            return
        try:
            import ctypes
            params = ""
            if getattr(sys, "frozen", False):
                exe = sys.executable
            else:
                exe = sys.executable
                params = f"\"{Path(__file__).resolve()}\""
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
            if int(ret) <= 32:
                messagebox.showerror(self.T("menu_help"), self.T("dialogs_admin_restart_failed", error=""))
            else:
                self._save_config()
                self.destroy()
        except Exception as e:
            messagebox.showerror(self.T("menu_help"), self.T("dialogs_admin_restart_failed", error=e))

    # ----- Workshop auto select -----
    def _auto_select_workshop(self):
        cur_val = self.workshop_var.get()
        cur_path = Path(cur_val)
        if cur_path.exists():
            entries = WorkshopScanner.scan(cur_path)
            if entries:
                self._log(self.T("logs_workshop_chosen_with_maps", path=cur_val))
                return
            else:
                self._log(self.T("logs_workshop_chosen_no_maps", path=cur_val))

        chosen = None
        chosen_with_maps = None
        for cand in WORKSHOP_CANDIDATES:
            p = Path(cand)
            if p.exists():
                if chosen is None:
                    chosen = cand
                entries = WorkshopScanner.scan(p)
                if entries:
                    chosen_with_maps = cand
                    break
        if chosen_with_maps:
            self.workshop_var.set(chosen_with_maps)
            self._log(self.T("logs_workshop_chosen_with_maps", path=chosen_with_maps))
        elif chosen:
            self.workshop_var.set(chosen)
            self._log(self.T("logs_workshop_chosen_no_maps", path=chosen))
        else:
            self._log(self.T("logs_workshop_prompt"))
            self._browse_workshop()

    # ----- Icon / Logo -----
    def _set_window_icon(self):
        try:
            ico = resource_path(ICON_FILE)
            if os.name == 'nt' and ico.exists():
                self.iconbitmap(default=str(ico))
                return
            logo_path = resource_path(LOGO_FILE)
            if logo_path.exists():
                if _HAS_PIL:
                    img = Image.open(logo_path).resize((64, 64))
                    self._icon_img = ImageTk.PhotoImage(img)
                else:
                    from tkinter import PhotoImage
                    self._icon_img = PhotoImage(file=str(logo_path))
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _load_logo(self, max_width=280, max_height=100):
        try:
            logo_path = resource_path(LOGO_FILE)
            if not logo_path.exists():
                self._logo_img = None
                return False
            if _HAS_PIL:
                img = Image.open(logo_path)
                w, h = img.size
                scale = min(max_width / w, max_height / h)
                nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
                img = img.resize((nw, nh), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
            else:
                from tkinter import PhotoImage
                img = PhotoImage(file=str(logo_path))
                while img.width() > max_width or img.height() > max_height:
                    img = img.subsample(2, 2)
                self._logo_img = img
            return True
        except Exception:
            self._logo_img = None
            return False

    # ----- Menu -----
    def _build_menu(self):
        menubar = tk.Menu(self)

        # Datei / File
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label=self.T("file_refresh"), command=self._refresh_list)
        m_file.add_separator()
        m_file.add_command(label=self.T("file_unlock_selected"), command=self._unlock_selected)
        m_file.add_command(label=self.T("file_unlock_all"), command=self._unlock_all)
        m_file.add_separator()
        m_file.add_command(label=self.T("file_runas_admin"), command=self._restart_as_admin)
        m_file.add_separator()
        m_file.add_command(label=self.T("file_exit"), command=self._on_close)
        menubar.add_cascade(label=self.T("menu_file"), menu=m_file)

        # Sprache / Language (dynamic from lang/*.json)
        m_lang = tk.Menu(menubar, tearoff=0)
        for code, name in self.i18n.list_languages():
            m_lang.add_radiobutton(
                label=name,
                value=code,
                variable=self.lang_var,
                command=lambda c=code: self._set_language(c)
            )
        menubar.add_cascade(label=self.T("menu_language"), menu=m_lang)

        # Hilfe / Help
        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label=self.T("help_readme"), command=lambda: webbrowser.open(URL_README))
        m_help.add_command(label=self.T("help_repository"), command=lambda: webbrowser.open(URL_REPO))
        m_help.add_command(label=self.T("help_report_issue"), command=self._open_issue_link)
        m_help.add_separator()
        m_help.add_command(label=self.T("help_profile", user=GH_USER), command=lambda: webbrowser.open(URL_USER))
        m_help.add_separator()
        m_help.add_command(label=self.T("help_about"), command=self._show_about)
        menubar.add_cascade(label=self.T("menu_help"), menu=m_help)

        self.config(menu=menubar)
        self.bind("<F5>", lambda e: self._refresh_list())

    # ----- Body (single page) -----
    def _build_body(self):
        pad = 8

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        # Header with logo
        header = ttk.Frame(container)
        header.pack(fill="x", padx=pad, pady=(pad, 0))
        if self._load_logo() and self._logo_img is not None:
            self.logo_label = ttk.Label(header, image=self._logo_img)
            self.logo_label.pack(side="left", anchor="w")

        # Disclaimer (localized) under the logo
        disclaimer_frame = ttk.LabelFrame(container, text=self.T("header_disclaimer_title"))
        disclaimer_frame.pack(fill="x", padx=pad, pady=(8, 0))
        self.disclaimer = tk.Label(
            disclaimer_frame,
            text=self.T("disclaimer_text"),
            justify="left",
            anchor="w",
            font=("Segoe UI", 9),
            fg="#444"
        )
        self.disclaimer.pack(fill="x", padx=pad, pady=(6, 8), anchor="w")

        def _fit_disclaimer(event):
            try:
                self.disclaimer.configure(wraplength=max(240, event.width - pad*2))
            except Exception:
                pass
        disclaimer_frame.bind("<Configure>", _fit_disclaimer)

        # Paths frame
        frame_paths = ttk.LabelFrame(container, text=self.T("paths_title"))
        frame_paths.pack(fill="x", padx=pad, pady=(pad, 0))

        ttk.Label(frame_paths, text=self.T("paths_workshop")).grid(row=0, column=0, sticky="w", padx=pad, pady=4)
        e1 = ttk.Entry(frame_paths, textvariable=self.workshop_var)
        e1.grid(row=0, column=1, sticky="we", padx=(0, pad), pady=4)
        ttk.Button(frame_paths, text=self.T("paths_browse"), command=self._browse_workshop).grid(row=0, column=2, sticky="w", padx=(0, pad), pady=4)

        ttk.Label(frame_paths, text=self.T("paths_dest")).grid(row=1, column=0, sticky="w", padx=pad, pady=4)
        e2 = ttk.Entry(frame_paths, textvariable=self.dest_var)
        e2.grid(row=1, column=1, sticky="we", padx=(0, pad), pady=4)
        ttk.Button(frame_paths, text=self.T("paths_browse"), command=self._browse_dest).grid(row=1, column=2, sticky="w", padx=(0, pad), pady=4)
        frame_paths.columnconfigure(1, weight=1)

        # Middle split
        frame_mid = ttk.Frame(container)
        frame_mid.pack(fill="both", expand=True, padx=pad, pady=pad)

        # Left: listbox
        left = ttk.Frame(frame_mid)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text=self.T("list_found_title")).pack(anchor="w")
        self.listbox = tk.Listbox(left, selectmode="extended")
        self.listbox.pack(fill="both", expand=True, padx=(0, pad), pady=(4, 0))

        btns = ttk.Frame(left)
        btns.pack(anchor="w", pady=4)
        ttk.Button(btns, text=self.T("select_all"), command=lambda: self.listbox.select_set(0, tk.END)).pack(side="left", padx=2)
        ttk.Button(btns, text=self.T("clear_selection"), command=lambda: self.listbox.select_clear(0, tk.END)).pack(side="left", padx=2)

        # Right: actions + log
        right = ttk.Frame(frame_mid)
        right.pack(side="right", fill="both")

        ttk.Label(right, text=self.T("actions_title")).pack(anchor="w")
        ttk.Button(right, text=self.T("action_refresh"), command=self._refresh_list).pack(fill="x", pady=2)
        ttk.Button(right, text=self.T("action_unlock_selected"), command=self._unlock_selected).pack(fill="x", pady=2)
        ttk.Button(right, text=self.T("action_unlock_all"), command=self._unlock_all).pack(fill="x", pady=2)

        ttk.Label(right, text=self.T("log_title")).pack(anchor="w", pady=(8, 0))
        self.log = ScrolledText(right, height=16, wrap="word")
        self.log.pack(fill="both", expand=True, pady=(4, 0))

        # Status bar
        self.status_var = tk.StringVar(value=self.T("status_ready"))
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x")
        status = ttk.Label(status_frame, textvariable=self.status_var, anchor="w", relief="sunken")
        status.pack(side="left", fill="x", expand=True)
        ver = ttk.Label(status_frame, text=f"v{APP_VERSION}", foreground="#666")
        ver.pack(side="right", padx=6)
        ver.bind("<Button-1>", lambda e: webbrowser.open(URL_REPO))
        cp = ttk.Label(status_frame, text=COPYRIGHT, foreground="#666")
        cp.pack(side="right", padx=6)
        cp.bind("<Button-1>", lambda e: webbrowser.open(URL_USER))

    # ----- Actions -----
    def _browse_workshop(self):
        d = filedialog.askdirectory(initialdir=self.workshop_var.get() or "/")
        if d:
            self.workshop_var.set(d)
            self._refresh_list()

    def _browse_dest(self):
        d = filedialog.askdirectory(initialdir=self.dest_var.get() or "/")
        if d:
            self.dest_var.set(d)

    def _show_about(self):
        messagebox.showinfo(
            self.T("dialogs_about_title"),
            f"{APP_TITLE} v{APP_VERSION}\n\n"
            f"{self.T('dialogs_about_body')}\n\n"
            f"Repository:\n{URL_REPO}\n\n"
            f"{COPYRIGHT}"
        )

    def _refresh_list(self):
        cur = Path(self.workshop_var.get())
        entries = WorkshopScanner.scan(cur)
        if not entries:
            if str(cur).strip("\\/").lower() == WORKSHOP_CANDIDATES[0].lower():
                alt = Path(WORKSHOP_CANDIDATES[1])
                if alt.exists():
                    alt_entries = WorkshopScanner.scan(alt)
                    if alt_entries:
                        self.workshop_var.set(WORKSHOP_CANDIDATES[1])
                        entries = alt_entries
                        self._log(self.T("logs_workshop_chosen_with_maps", path=WORKSHOP_CANDIDATES[1]))
            if not entries and not self._did_auto_prompt:
                self._did_auto_prompt = True
                messagebox.showinfo(self.T("paths_title"), self.T("dialogs_workshop_pick"))
                self._browse_workshop()
                cur = Path(self.workshop_var.get())
                entries = WorkshopScanner.scan(cur)

        self.listbox.delete(0, tk.END)
        self._entries = entries
        for e in entries:
            self.listbox.insert(tk.END, e.display)
        self.status_var.set(self.T("status_found_maps", count=len(entries), path=str(self.workshop_var.get())))
        self._log(self.T("status_scan_done", count=len(entries), path=str(self.workshop_var.get())))

    def _unlock_selected(self):
        idxs = list(self.listbox.curselection())
        if not idxs:
            messagebox.showwarning(self.T("menu_help"), self.T("dialogs_select_at_least_one"))
            return
        items = [self._entries[i] for i in idxs]
        self._run_unlock(items)

    def _unlock_all(self):
        items = list(self._entries)
        if not items:
            messagebox.showwarning(self.T("menu_help"), self.T("dialogs_no_maps"))
            return
        if not messagebox.askyesno(self.T("menu_file"), self.T("dialogs_confirm_unlock_all", count=len(items))):
            return
        self._run_unlock(items)

    def _run_unlock(self, items):
        dest = Path(self.dest_var.get())
        if not dest.exists():
            if not messagebox.askyesno(self.T("dialogs_dest_missing_title"), self.T("dialogs_dest_missing_body", dest=dest)):
                return
            try:
                dest.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                self._handle_permission_error(e)
                return
            except Exception as e:
                messagebox.showerror(self.T("menu_help"), self.T("dialogs_dest_mkdir_error", error=e))
                return

        def job():
            ok = 0
            for entry in items:
                try:
                    out, log = MapUnlocker.copy_and_unlock(entry.fullpath, dest)
                    ok += 1
                    self._log(log + "\n")
                except PermissionError as e:
                    self._handle_permission_error(e)
                except Exception as e:
                    self._log(self.T("logs_error_prefix", name=entry.display, error=e) + "\n")
            self._log(self.T("status_finished", ok=ok, total=len(items)))
            self.status_var.set(self.T("status_finished", ok=ok, total=len(items)))
        threading.Thread(target=job, daemon=True).start()
        self.status_var.set("...")

    def _handle_permission_error(self, e: Exception):
        self._log(self.T("logs_permission_error_prefix", error=e))
        if os.name == "nt" and not self._is_admin():
            messagebox.showwarning(self.T("dialogs_permission_title"), self.T("dialogs_permission_admin_hint"))
        else:
            messagebox.showwarning(self.T("dialogs_permission_title"), self.T("dialogs_permission_generic_hint"))

    def _log(self, text: str):
        self.log.insert("end", text + ("\n" if not text.endswith("\n") else ""))
        self.log.see("end")

    # ----- Layout & lifecycle -----
    def _ensure_statusbar_visible(self):
        try:
            self.update_idletasks()
            cur_w = self.winfo_width()
            cur_h = self.winfo_height()
            req_h = self.winfo_reqheight()
            if cur_h < req_h:
                self.geometry(f"{cur_w}x{req_h}")
        except Exception:
            pass

    def _open_issue_link(self):
        webbrowser.open(URL_ISSUE)

    def _on_close(self):
        self._save_config()
        self.destroy()

    def _save_config(self):
        cfg = {
            "language": self.lang,
            "workshop": self.workshop_var.get(),
            "dest": self.dest_var.get(),
        }
        save_config(cfg)

def main():
    app = UnlockApp()
    app.mainloop()

if __name__ == "__main__":
    main()
