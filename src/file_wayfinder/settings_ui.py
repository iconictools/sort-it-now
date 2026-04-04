"""Settings dialog for File Wayfinder (tkinter-based).

Lets the user edit config settings without touching JSON directly.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from file_wayfinder.autostart import is_autostart_enabled, set_autostart
from file_wayfinder.themes import get_theme

if TYPE_CHECKING:
    from file_wayfinder.config import Config

logger = logging.getLogger(__name__)


class SettingsDialog:
    """Modal settings window."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._theme = get_theme(config.get_setting("theme", "dark"))

    def show(self) -> None:
        """Display the settings dialog (blocks until closed)."""
        t = self._theme
        root = tk.Tk()
        root.title("File Wayfinder -- Settings")
        root.configure(bg=t["bg"])
        root.resizable(False, False)

        w, h = 480, 700
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        tk.Label(
            root,
            text="Settings",
            bg=t["bg"],
            fg=t["accent"],
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(16, 12))

        frame = tk.Frame(root, bg=t["bg"])
        frame.pack(fill="both", expand=True, padx=24)

        row = 0

        # -- Theme --
        tk.Label(
            frame, text="Theme:", bg=t["bg"], fg=t["fg"], font=("Segoe UI", 10)
        ).grid(row=row, column=0, sticky="w", pady=4)
        theme_var = tk.StringVar(value=self._config.get_setting("theme", "dark"))
        theme_menu = tk.OptionMenu(frame, theme_var, "dark", "light")
        theme_menu.config(
            bg=t["btn_bg"], fg=t["btn_fg"], font=("Segoe UI", 10),
            activebackground=t["btn_active"], relief="flat",
        )
        theme_menu.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        row += 1

        # -- Auto-learn --
        tk.Label(
            frame, text="Auto-learn:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        auto_learn_var = tk.BooleanVar(
            value=self._config.get_setting("auto_learn", True)
        )
        tk.Checkbutton(
            frame,
            text="Enabled",
            variable=auto_learn_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=4, padx=(8, 0))
        row += 1

        # -- Auto-learn threshold --
        tk.Label(
            frame, text="Auto-learn threshold:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        threshold_var = tk.IntVar(
            value=self._config.get_setting("auto_learn_threshold", 3)
        )
        tk.Spinbox(
            frame, from_=1, to=20, textvariable=threshold_var, width=5,
            bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=4, padx=(8, 0))
        row += 1

        # -- Prompt delay --
        tk.Label(
            frame, text="Prompt delay (s):", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        delay_var = tk.DoubleVar(
            value=self._config.get_setting("prompt_delay_seconds", 3.0)
        )
        tk.Spinbox(
            frame, from_=0.5, to=30.0, increment=0.5,
            textvariable=delay_var, width=5,
            bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=4, padx=(8, 0))
        row += 1

        # -- Batch mode --
        tk.Label(
            frame, text="Batch processing:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        batch_var = tk.StringVar(
            value=self._config.get_setting("batch_mode_style", "one-by-one")
        )
        batch_menu = tk.OptionMenu(
            frame, batch_var, "one-by-one", "batch-list"
        )
        batch_menu.config(
            bg=t["btn_bg"], fg=t["btn_fg"], font=("Segoe UI", 10),
            activebackground=t["btn_active"], relief="flat",
        )
        batch_menu.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        row += 1

        # -- DND integration --
        tk.Label(
            frame, text="Pause when DND is on:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        dnd_var = tk.BooleanVar(
            value=self._config.get_setting("pause_on_dnd", False)
        )
        tk.Checkbutton(
            frame,
            text="Enabled",
            variable=dnd_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=4, padx=(8, 0))
        row += 1

        # -- Autostart --
        tk.Label(
            frame, text="Start on login:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        tk.Checkbutton(
            frame,
            text="Enabled",
            variable=autostart_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=4, padx=(8, 0))
        row += 1

        # -- Scan existing files --
        tk.Label(
            frame, text="Scan existing files:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        scan_var = tk.BooleanVar(
            value=self._config.get_setting("scan_existing_enabled", False)
        )
        tk.Checkbutton(
            frame,
            text="Enabled",
            variable=scan_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=4, padx=(8, 0))
        row += 1

        # -- Catch folders --
        tk.Label(
            frame, text="Catch folders:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=4)
        catch_folders_var = tk.BooleanVar(
            value=self._config.get_setting("catch_folders", False)
        )
        tk.Checkbutton(
            frame,
            text="Enabled",
            variable=catch_folders_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=4, padx=(8, 0))
        row += 1

        # ── Quick Add Folder ────────────────────────────────────────────
        tk.Label(
            frame, text="Quick Add Folder:", bg=t["bg"], fg=t["accent"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 2))
        row += 1

        # Inherit destinations
        tk.Label(
            frame, text="  Inherit parent destinations:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=2)
        qa_inherit_var = tk.BooleanVar(
            value=self._config.get_setting("quick_add_inherit_destinations", True)
        )
        tk.Checkbutton(
            frame,
            text="Enabled (skips destination picker)",
            variable=qa_inherit_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=2, padx=(8, 0))
        row += 1

        # Auto-whitelist after quick add
        tk.Label(
            frame, text="  Auto-whitelist folder:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=2)
        qa_whitelist_var = tk.BooleanVar(
            value=self._config.get_setting("quick_add_auto_whitelist", True)
        )
        tk.Checkbutton(
            frame,
            text="Ignore folder name in future scans",
            variable=qa_whitelist_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=2, padx=(8, 0))
        row += 1

        # Auto-start watch
        tk.Label(
            frame, text="  Auto-start watching:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=2)
        qa_watch_var = tk.BooleanVar(
            value=self._config.get_setting("quick_add_auto_start_watch", True)
        )
        tk.Checkbutton(
            frame,
            text="Monitor new folder immediately",
            variable=qa_watch_var,
            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="w", pady=2, padx=(8, 0))
        row += 1

        # -- Monitored folders section --
        tk.Label(
            frame, text="Monitored folders:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 4))
        row += 1

        folders_list = tk.Listbox(
            frame, bg=t["list_bg"], fg=t["list_fg"],
            selectbackground=t["list_select_bg"],
            selectforeground=t["list_select_fg"],
            font=("Segoe UI", 9), height=5, relief="flat",
        )
        folders_list.grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=4,
        )
        for folder in self._config.monitored_folders:
            folders_list.insert("end", folder)
        row += 1

        folder_btn_frame = tk.Frame(frame, bg=t["bg"])
        folder_btn_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=2,
        )

        def _add_folder() -> None:
            folder = filedialog.askdirectory(
                title="Select folder to monitor", parent=root
            )
            if folder:
                dests: list[str] = []
                while True:
                    dest = filedialog.askdirectory(
                        title=f"Add destination for {folder} (cancel to finish)",
                        parent=root,
                    )
                    if not dest:
                        break
                    dests.append(dest)
                if dests:
                    self._config.add_monitored_folder(folder, dests)
                    folders_list.insert("end", folder)

        def _remove_folder() -> None:
            sel = folders_list.curselection()
            if sel:
                folder = folders_list.get(sel[0])
                self._config.remove_monitored_folder(folder)
                folders_list.delete(sel[0])

        tk.Button(
            folder_btn_frame, text="+ Add", bg=t["accent"], fg=t["bg"],
            font=("Segoe UI", 9, "bold"), relief="flat", command=_add_folder,
        ).pack(side="left", padx=(0, 4))
        tk.Button(
            folder_btn_frame, text="- Remove", bg=t["danger"], fg="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat",
            command=_remove_folder,
        ).pack(side="left")
        row += 1

        # -- Whitelist patterns section --
        tk.Label(
            frame, text="Whitelist patterns:", bg=t["bg"], fg=t["fg"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 4))
        row += 1

        wl_list = tk.Listbox(
            frame, bg=t["list_bg"], fg=t["list_fg"],
            selectbackground=t["list_select_bg"],
            selectforeground=t["list_select_fg"],
            font=("Segoe UI", 9), height=3, relief="flat",
        )
        wl_list.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        for pat in self._config.get_whitelist():
            wl_list.insert("end", pat)
        row += 1

        wl_btn_frame = tk.Frame(frame, bg=t["bg"])
        wl_btn_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=2,
        )

        def _add_whitelist() -> None:
            dlg = tk.Toplevel(root)
            dlg.title("Add Whitelist Pattern")
            dlg.configure(bg=t["bg"])
            dlg.geometry("300x120")
            tk.Label(
                dlg, text="Pattern (e.g. *.log):", bg=t["bg"], fg=t["fg"],
                font=("Segoe UI", 10),
            ).pack(pady=(12, 2))
            entry = tk.Entry(
                dlg, bg=t["entry_bg"], fg=t["entry_fg"],
                font=("Segoe UI", 10),
            )
            entry.pack(padx=20, fill="x")

            def _save_wl() -> None:
                pat = entry.get().strip()
                if pat:
                    self._config.add_to_whitelist(pat)
                    wl_list.insert("end", pat)
                dlg.destroy()

            tk.Button(
                dlg, text="Add", bg=t["accent"], fg=t["bg"],
                font=("Segoe UI", 10, "bold"), relief="flat",
                command=_save_wl,
            ).pack(pady=8)

        def _remove_whitelist() -> None:
            sel = wl_list.curselection()
            if sel:
                pat = wl_list.get(sel[0])
                self._config.remove_from_whitelist(pat)
                wl_list.delete(sel[0])

        tk.Button(
            wl_btn_frame, text="+ Add", bg=t["accent"], fg=t["bg"],
            font=("Segoe UI", 9, "bold"), relief="flat",
            command=_add_whitelist,
        ).pack(side="left", padx=(0, 4))
        tk.Button(
            wl_btn_frame, text="- Remove", bg=t["danger"], fg="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat",
            command=_remove_whitelist,
        ).pack(side="left")
        row += 1

        frame.columnconfigure(1, weight=1)

        # -- Save / Cancel --
        def _save() -> None:
            self._config.save_many({
                "theme": theme_var.get(),
                "auto_learn": auto_learn_var.get(),
                "auto_learn_threshold": threshold_var.get(),
                "prompt_delay_seconds": delay_var.get(),
                "batch_mode_style": batch_var.get(),
                "pause_on_dnd": dnd_var.get(),
                "scan_existing_enabled": scan_var.get(),
                "catch_folders": catch_folders_var.get(),
            })
            set_autostart(autostart_var.get())
            logger.info("Settings saved.")
            root.destroy()

        btn_row = tk.Frame(root, bg=t["bg"])
        btn_row.pack(pady=8)
        tk.Button(
            btn_row, text="Save", bg=t["accent"], fg=t["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat", command=_save,
            width=10,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_row, text="Cancel", bg=t["btn_bg"], fg=t["btn_fg"],
            font=("Segoe UI", 10), relief="flat", command=root.destroy,
            width=10,
        ).pack(side="left", padx=4)

        # -- Export / Import --
        io_frame = tk.Frame(root, bg=t["bg"])
        io_frame.pack(pady=(0, 12))

        def _export_config() -> None:
            path = filedialog.asksaveasfilename(
                title="Export Config",
                defaultextension=".zip",
                filetypes=[("Zip files", "*.zip")],
                parent=root,
            )
            if path:
                self._config.export_config(path)
                messagebox.showinfo("Export", "Config exported.", parent=root)

        def _import_config() -> None:
            path = filedialog.askopenfilename(
                title="Import Config",
                filetypes=[("Zip files", "*.zip")],
                parent=root,
            )
            if path:
                self._config.import_config(path)
                messagebox.showinfo(
                    "Import", "Config imported. Restart to apply.",
                    parent=root,
                )

        tk.Button(
            io_frame, text="Export Config", bg=t["btn_bg"], fg=t["btn_fg"],
            font=("Segoe UI", 9), relief="flat", command=_export_config,
        ).pack(side="left", padx=4)
        tk.Button(
            io_frame, text="Import Config", bg=t["btn_bg"], fg=t["btn_fg"],
            font=("Segoe UI", 9), relief="flat", command=_import_config,
        ).pack(side="left", padx=4)

        root.mainloop()
