"""Settings dialog for File Wayfinder (tkinter-based).

Lets the user edit config settings without touching JSON directly.

Layout (tabbed):
  Tab 1 — General     : theme, notifications, undo restore-name, multi-instance
  Tab 2 — Monitoring  : prompt delay, scan existing, catch folders, DND, pattern rules, duplicate detection
  Tab 3 — Folders     : watched folders ↔ per-folder destinations (full CRUD)
  Tab 4 — Rules       : whitelist patterns, ignore patterns, rename patterns
  Tab 5 — System      : autostart, batch mode, export/import config
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING

from file_wayfinder.autostart import is_autostart_enabled, set_autostart
from file_wayfinder.themes import get_theme

if TYPE_CHECKING:
    from file_wayfinder.config import Config

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────

def _label(parent: tk.Widget, text: str, t: dict, bold: bool = False) -> tk.Label:
    font = ("Segoe UI", 10, "bold") if bold else ("Segoe UI", 10)
    return tk.Label(parent, text=text, bg=t["bg"], fg=t["fg"], font=font)


def _check(parent: tk.Widget, text: str, var: tk.BooleanVar, t: dict) -> tk.Checkbutton:
    return tk.Checkbutton(
        parent, text=text, variable=var,
        bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"],
        activebackground=t["bg"], activeforeground=t["fg"],
        font=("Segoe UI", 10),
    )


def _section(parent: tk.Widget, text: str, t: dict) -> tk.Label:
    return tk.Label(
        parent, text=text, bg=t["bg"], fg=t["accent"],
        font=("Segoe UI", 11, "bold"),
    )


# ── Tab builders ──────────────────────────────────────────────────────

def _build_general_tab(nb: ttk.Notebook, cfg: "Config", t: dict) -> dict:
    """Return a dict of tk variables for settings on the General tab."""
    f = tk.Frame(nb, bg=t["bg"])
    nb.add(f, text="General")

    pad = {"padx": (0, 8), "pady": 4}

    # Theme
    _section(f, "Appearance", t).grid(row=0, column=0, columnspan=2, sticky="w", pady=(12, 4))
    _label(f, "Theme:", t).grid(row=1, column=0, sticky="w", **pad)
    theme_var = tk.StringVar(value=cfg.get_setting("theme", "dark"))
    tk.OptionMenu(f, theme_var, "dark", "light").grid(row=1, column=1, sticky="ew", **pad)

    # Notifications
    _section(f, "Notifications", t).grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 4))
    _label(f, "Native notifications:", t).grid(row=3, column=0, sticky="w", **pad)
    notif_var = tk.BooleanVar(value=cfg.get_setting("native_notifications", True))
    _check(f, "Enabled", notif_var, t).grid(row=3, column=1, sticky="w", **pad)

    _label(f, "Fallback when native fails:", t).grid(row=4, column=0, sticky="w", **pad)
    fallback_var = tk.StringVar(value=cfg.get_setting("notification_fallback", "toast-fallback"))
    fb_menu = tk.OptionMenu(f, fallback_var, "toast-fallback", "log-only", "plyer-only")
    fb_menu.grid(row=4, column=1, sticky="ew", **pad)
    _label(f, "  toast-fallback = small overlay, log-only = silent, plyer-only = drop", t).grid(
        row=5, column=0, columnspan=2, sticky="w", padx=(0, 8), pady=(0, 4)
    )

    # Undo
    _section(f, "Undo Behaviour", t).grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 4))
    _label(f, "When undoing a renamed move:", t).grid(row=7, column=0, sticky="w", **pad)
    undo_name_var = tk.StringVar(value=cfg.get_setting("undo_restore_name", "ask"))
    tk.OptionMenu(f, undo_name_var, "ask", "always", "never").grid(
        row=7, column=1, sticky="ew", **pad
    )
    _label(f, "  ask = prompt each time, always = restore name, never = keep new name", t).grid(
        row=8, column=0, columnspan=2, sticky="w", padx=(0, 8), pady=(0, 4)
    )

    # Multi-instance
    _section(f, "Multi-Instance", t).grid(row=9, column=0, columnspan=2, sticky="w", pady=(12, 4))
    _label(f, "Second launch behaviour:", t).grid(row=10, column=0, sticky="w", **pad)
    multi_var = tk.StringVar(value=cfg.get_setting("multi_instance_behavior", "prompt"))
    tk.OptionMenu(f, multi_var, "prompt", "always-merge", "ignore").grid(
        row=10, column=1, sticky="ew", **pad
    )
    _label(f, "  prompt = ask, always-merge = silently add folder, ignore = open fresh", t).grid(
        row=11, column=0, columnspan=2, sticky="w", padx=(0, 8), pady=(0, 4)
    )

    f.columnconfigure(1, weight=1)
    return {
        "theme": theme_var,
        "native_notifications": notif_var,
        "notification_fallback": fallback_var,
        "undo_restore_name": undo_name_var,
        "multi_instance_behavior": multi_var,
    }


def _build_monitoring_tab(nb: ttk.Notebook, cfg: "Config", t: dict) -> dict:
    """Return a dict of tk variables for settings on the Monitoring tab."""
    f = tk.Frame(nb, bg=t["bg"])
    nb.add(f, text="Monitoring")

    pad = {"padx": (0, 8), "pady": 4}

    _section(f, "File Detection", t).grid(row=0, column=0, columnspan=2, sticky="w", pady=(12, 4))

    _label(f, "Prompt delay (s):", t).grid(row=1, column=0, sticky="w", **pad)
    delay_var = tk.DoubleVar(value=cfg.get_setting("prompt_delay_seconds", 3.0))
    tk.Spinbox(f, from_=0.5, to=30.0, increment=0.5, textvariable=delay_var, width=6,
               bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10)).grid(
        row=1, column=1, sticky="w", **pad)

    _label(f, "Scan existing files at startup:", t).grid(row=2, column=0, sticky="w", **pad)
    scan_var = tk.BooleanVar(value=cfg.get_setting("scan_existing_enabled", False))
    _check(f, "Enabled", scan_var, t).grid(row=2, column=1, sticky="w", **pad)

    _label(f, "Watch folders too (catch folders):", t).grid(row=3, column=0, sticky="w", **pad)
    catch_var = tk.BooleanVar(value=cfg.get_setting("catch_folders", False))
    _check(f, "Enabled", catch_var, t).grid(row=3, column=1, sticky="w", **pad)

    _label(f, "Pause when DND / Focus Assist active:", t).grid(row=4, column=0, sticky="w", **pad)
    dnd_var = tk.BooleanVar(value=cfg.get_setting("pause_on_dnd", False))
    _check(f, "Enabled", dnd_var, t).grid(row=4, column=1, sticky="w", **pad)

    _section(f, "Rules & Detection", t).grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 4))

    _label(f, "Pattern rules (glob/regex):", t).grid(row=6, column=0, sticky="w", **pad)
    pattern_var = tk.BooleanVar(value=cfg.get_setting("pattern_rules_enabled", True))
    _check(f, "Enabled", pattern_var, t).grid(row=6, column=1, sticky="w", **pad)

    _label(f, "Duplicate detection (SHA-256):", t).grid(row=7, column=0, sticky="w", **pad)
    dup_var = tk.BooleanVar(value=cfg.get_setting("duplicate_detection", False))
    _check(f, "Enabled", dup_var, t).grid(row=7, column=1, sticky="w", **pad)

    _section(f, "Cleanup Reminders", t).grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 4))
    _label(
        f,
        "Cleanup reminder (0=off, N=alert when folder has ≥N unsorted files):",
        t,
    ).grid(row=9, column=0, sticky="w", **pad)
    cleanup_var = tk.IntVar(value=cfg.get_setting("cleanup_reminder_threshold", 0))
    tk.Spinbox(f, from_=0, to=9999, increment=1, textvariable=cleanup_var, width=6,
               bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10)).grid(
        row=9, column=1, sticky="w", **pad)

    f.columnconfigure(1, weight=1)
    return {
        "prompt_delay_seconds": delay_var,
        "scan_existing_enabled": scan_var,
        "catch_folders": catch_var,
        "pause_on_dnd": dnd_var,
        "pattern_rules_enabled": pattern_var,
        "duplicate_detection": dup_var,
        "cleanup_reminder_threshold": cleanup_var,
    }


def _build_folders_tab(nb: ttk.Notebook, cfg: "Config", t: dict, root: tk.Tk) -> None:
    """Build the Folders tab with full per-folder destination CRUD.

    Changes are written immediately to config on every action — no
    "Save" button needed for folder/destination changes.
    """
    f = tk.Frame(nb, bg=t["bg"])
    nb.add(f, text="Folders")

    # ── Top: Watched Folders (left) + Destinations (right) ─────────────
    _section(f, "Watched Folders & Destinations", t).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(10, 4), padx=8
    )
    tk.Label(
        f, text="Select a watched folder to manage its destination folders.",
        bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9, "italic"),
    ).grid(row=1, column=0, columnspan=3, sticky="w", padx=8)

    # Left pane: watched folders
    left = tk.Frame(f, bg=t["bg"])
    left.grid(row=2, column=0, sticky="nsew", padx=(8, 4), pady=4)
    tk.Label(left, text="Watched folders:", bg=t["bg"], fg=t["fg"],
             font=("Segoe UI", 10, "bold")).pack(anchor="w")

    watch_list = tk.Listbox(
        left, bg=t["list_bg"], fg=t["list_fg"],
        selectbackground=t["list_select_bg"], selectforeground=t["list_select_fg"],
        font=("Segoe UI", 9), relief="flat", width=30, height=12,
    )
    watch_list.pack(fill="both", expand=True)

    for folder in cfg.monitored_folders:
        watch_list.insert("end", folder)

    wbtn = tk.Frame(left, bg=t["bg"])
    wbtn.pack(fill="x", pady=(4, 0))

    # Right pane: destinations for selected folder
    right = tk.Frame(f, bg=t["bg"])
    right.grid(row=2, column=1, sticky="nsew", padx=(4, 8), pady=4)
    tk.Label(right, text="Destinations:", bg=t["bg"], fg=t["fg"],
             font=("Segoe UI", 10, "bold")).pack(anchor="w")

    dest_list = tk.Listbox(
        right, bg=t["list_bg"], fg=t["list_fg"],
        selectbackground=t["list_select_bg"], selectforeground=t["list_select_fg"],
        font=("Segoe UI", 9), relief="flat", width=34, height=12,
    )
    dest_list.pack(fill="both", expand=True)

    dbtn = tk.Frame(right, bg=t["bg"])
    dbtn.pack(fill="x", pady=(4, 0))

    f.columnconfigure(0, weight=1)
    f.columnconfigure(1, weight=1)
    f.rowconfigure(2, weight=1)

    _selected_folder: list[str] = []  # mutable container to share across closures

    def _refresh_dests() -> None:
        dest_list.delete(0, "end")
        if not _selected_folder:
            return
        for d in cfg.get_folder_destinations(_selected_folder[0]):
            dest_list.insert("end", d)

    def _on_watch_select(event: object = None) -> None:  # noqa: ARG001
        sel = watch_list.curselection()
        if not sel:
            return
        _selected_folder.clear()
        _selected_folder.append(watch_list.get(sel[0]))
        _refresh_dests()

    watch_list.bind("<<ListboxSelect>>", _on_watch_select)

    # Watched folder buttons
    def _add_watch() -> None:
        folder = filedialog.askdirectory(title="Choose a folder to watch", parent=root)
        if not folder or not os.path.isdir(folder):
            return
        folder = os.path.abspath(folder)
        if folder in cfg.monitored_folders:
            messagebox.showinfo("Already watched", f"Already watching:\n{folder}", parent=root)
            return
        cfg.add_monitored_folder(folder, [])
        watch_list.insert("end", folder)

    def _remove_watch() -> None:
        sel = watch_list.curselection()
        if not sel:
            return
        folder = watch_list.get(sel[0])
        if messagebox.askyesno(
            "Remove folder", f"Stop watching:\n{folder}?", parent=root
        ):
            cfg.remove_monitored_folder(folder)
            watch_list.delete(sel[0])
            _selected_folder.clear()
            dest_list.delete(0, "end")

    tk.Button(wbtn, text="+ Watch", bg=t["accent"], fg=t["bg"],
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_add_watch).pack(side="left", padx=(0, 4))
    tk.Button(wbtn, text="- Remove", bg=t["danger"], fg="#ffffff",
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_remove_watch).pack(side="left")

    # Destination buttons
    def _add_dest() -> None:
        if not _selected_folder:
            messagebox.showwarning("No folder selected",
                                   "Select a watched folder first.", parent=root)
            return
        folder = _selected_folder[0]
        dest = filedialog.askdirectory(
            title=f"Add destination for {os.path.basename(folder)}", parent=root
        )
        if not dest:
            return
        dest = os.path.abspath(dest)
        current = list(cfg.get_folder_destinations(folder))
        if dest in current:
            messagebox.showinfo("Already added", f"Already a destination:\n{dest}", parent=root)
            return
        current.append(dest)
        cfg.set_destinations(folder, current)
        dest_list.insert("end", dest)

    def _remove_dest() -> None:
        if not _selected_folder:
            return
        sel = dest_list.curselection()
        if not sel:
            return
        folder = _selected_folder[0]
        dest = dest_list.get(sel[0])
        current = list(cfg.get_folder_destinations(folder))
        if dest in current:
            current.remove(dest)
            cfg.set_destinations(folder, current)
        dest_list.delete(sel[0])

    tk.Button(dbtn, text="+ Add destination", bg=t["accent"], fg=t["bg"],
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_add_dest).pack(side="left", padx=(0, 4))
    tk.Button(dbtn, text="- Remove", bg=t["danger"], fg="#ffffff",
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_remove_dest).pack(side="left")

    # ── Quick Add Folder sub-settings ──────────────────────────────────
    sep = tk.Frame(f, height=1, bg=t["btn_bg"])
    sep.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=6)

    qa_frame = tk.Frame(f, bg=t["bg"])
    qa_frame.grid(row=4, column=0, columnspan=2, sticky="w", padx=8)

    _section(qa_frame, "Quick-Add Folder Options", t).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(4, 4)
    )
    tk.Label(qa_frame, text="When a new folder is added via the sort prompt:", bg=t["bg"],
             fg=t["fg"], font=("Segoe UI", 9, "italic")).grid(
        row=1, column=0, columnspan=2, sticky="w"
    )

    qa_inherit = tk.BooleanVar(value=cfg.get_setting("quick_add_inherit_destinations", True))
    qa_whitelist = tk.BooleanVar(value=cfg.get_setting("quick_add_auto_whitelist", True))
    qa_watch = tk.BooleanVar(value=cfg.get_setting("quick_add_auto_start_watch", True))

    _check(qa_frame, "Inherit parent destinations (skip picker)", qa_inherit, t).grid(
        row=2, column=0, columnspan=2, sticky="w", pady=2
    )
    _check(qa_frame, "Auto-whitelist new folder name", qa_whitelist, t).grid(
        row=3, column=0, columnspan=2, sticky="w", pady=2
    )
    _check(qa_frame, "Start watching immediately", qa_watch, t).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=2
    )

    # ── Per-folder label + whitelist ────────────────────────────────────
    sep2 = tk.Frame(f, height=1, bg=t["btn_bg"])
    sep2.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=6)

    detail_frame = tk.Frame(f, bg=t["bg"])
    detail_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 4))
    f.rowconfigure(6, weight=0)

    _section(detail_frame, "Per-Folder Details", t).grid(
        row=0, column=0, columnspan=4, sticky="w", pady=(4, 4)
    )

    # Folder Label
    tk.Label(detail_frame, text="Folder Label:", bg=t["bg"], fg=t["fg"],
             font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
    folder_label_var = tk.StringVar(value="")
    folder_label_entry = tk.Entry(
        detail_frame, textvariable=folder_label_var,
        bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10), width=36,
    )
    folder_label_entry.grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)

    # Per-folder whitelist
    tk.Label(detail_frame, text="Per-folder whitelist:", bg=t["bg"], fg=t["fg"],
             font=("Segoe UI", 10)).grid(row=2, column=0, sticky="nw", padx=(0, 6), pady=2)
    pfwl_list = tk.Listbox(
        detail_frame, bg=t["list_bg"], fg=t["list_fg"],
        selectbackground=t["list_select_bg"], selectforeground=t["list_select_fg"],
        font=("Segoe UI", 9), relief="flat", height=4, width=36,
    )
    pfwl_list.grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)
    pfwl_btn = tk.Frame(detail_frame, bg=t["bg"])
    pfwl_btn.grid(row=3, column=1, columnspan=3, sticky="w", pady=(2, 4))

    def _pfwl_add() -> None:
        if not _selected_folder:
            return
        pat = simpledialog.askstring(
            "Add whitelist pattern",
            "Enter a glob pattern (e.g. *.log):",
            parent=root,
        )
        if pat and pat.strip():
            cfg.add_to_folder_whitelist(_selected_folder[0], pat.strip())
            pfwl_list.insert("end", pat.strip())

    def _pfwl_remove() -> None:
        if not _selected_folder:
            return
        sel = pfwl_list.curselection()
        if not sel:
            return
        item = pfwl_list.get(sel[0])
        cfg.remove_from_folder_whitelist(_selected_folder[0], item)
        pfwl_list.delete(sel[0])

    tk.Button(pfwl_btn, text="+ Add", bg=t["accent"], fg=t["bg"],
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_pfwl_add).pack(side="left", padx=(0, 4))
    tk.Button(pfwl_btn, text="- Remove", bg=t["danger"], fg="#ffffff",
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_pfwl_remove).pack(side="left")

    # Track label changes and write to config
    _label_trace_active: list[bool] = [False]

    def _on_label_write(*_: object) -> None:
        if _label_trace_active[0] and _selected_folder:
            cfg.set_folder_label(_selected_folder[0], folder_label_var.get())

    folder_label_var.trace_add("write", _on_label_write)

    def _refresh_per_folder_details() -> None:
        """Update label and whitelist widgets when the selected folder changes."""
        _label_trace_active[0] = False
        pfwl_list.delete(0, "end")
        if not _selected_folder:
            folder_label_var.set("")
            _label_trace_active[0] = True
            return
        folder = _selected_folder[0]
        folder_label_var.set(cfg.get_folder_label(folder))
        for pat in cfg.get_folder_whitelist(folder):
            pfwl_list.insert("end", pat)
        _label_trace_active[0] = True

    # Patch _on_watch_select to also refresh per-folder details
    original_on_watch_select = _on_watch_select

    def _on_watch_select_extended(event: object = None) -> None:
        original_on_watch_select(event)
        _refresh_per_folder_details()

    watch_list.bind("<<ListboxSelect>>", _on_watch_select_extended)

    # Return the quick-add vars so _save() can persist them
    return {  # type: ignore[return-value]
        "quick_add_inherit_destinations": qa_inherit,
        "quick_add_auto_whitelist": qa_whitelist,
        "quick_add_auto_start_watch": qa_watch,
    }


def _build_rules_tab(nb: ttk.Notebook, cfg: "Config", t: dict, root: tk.Tk) -> None:
    """Build the Rules tab: whitelist, ignore patterns, rename patterns."""
    f = tk.Frame(nb, bg=t["bg"])
    nb.add(f, text="Rules")

    # ── Whitelist ──────────────────────────────────────────────────────
    _section(f, "Whitelist (never sort these)", t).pack(anchor="w", padx=8, pady=(10, 2))
    tk.Label(f, text="Files matching these patterns are silently skipped (glob, e.g. *.log).",
             bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=8)

    wl_list = tk.Listbox(f, bg=t["list_bg"], fg=t["list_fg"],
                         selectbackground=t["list_select_bg"],
                         selectforeground=t["list_select_fg"],
                         font=("Segoe UI", 9), relief="flat", height=4)
    wl_list.pack(fill="x", padx=8, pady=2)
    for pat in cfg.get_whitelist():
        wl_list.insert("end", pat)

    def _add_wl() -> None:
        dlg = tk.Toplevel(root)
        dlg.title("Add Whitelist Pattern")
        dlg.configure(bg=t["bg"])
        dlg.geometry("300x110")
        tk.Label(dlg, text="Pattern (e.g. *.log):", bg=t["bg"], fg=t["fg"],
                 font=("Segoe UI", 10)).pack(pady=(10, 2))
        entry = tk.Entry(dlg, bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10))
        entry.pack(padx=16, fill="x")
        def _ok() -> None:
            p = entry.get().strip()
            if p:
                cfg.add_to_whitelist(p)
                wl_list.insert("end", p)
            dlg.destroy()
        tk.Button(dlg, text="Add", bg=t["accent"], fg=t["bg"],
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=_ok).pack(pady=6)

    def _rm_wl() -> None:
        sel = wl_list.curselection()
        if sel:
            p = wl_list.get(sel[0])
            cfg.remove_from_whitelist(p)
            wl_list.delete(sel[0])

    wl_btns = tk.Frame(f, bg=t["bg"])
    wl_btns.pack(anchor="w", padx=8)
    tk.Button(wl_btns, text="+ Add", bg=t["accent"], fg=t["bg"],
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_add_wl).pack(side="left", padx=(0, 4))
    tk.Button(wl_btns, text="- Remove", bg=t["danger"], fg="#ffffff",
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_rm_wl).pack(side="left")

    # ── Ignore patterns ────────────────────────────────────────────────
    _section(f, "Ignore Patterns (watcher skips these)", t).pack(
        anchor="w", padx=8, pady=(10, 2)
    )
    tk.Label(f, text="Files matching these patterns are not detected at all (glob, e.g. ~$*).",
             bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=8)

    ig_list = tk.Listbox(f, bg=t["list_bg"], fg=t["list_fg"],
                         selectbackground=t["list_select_bg"],
                         selectforeground=t["list_select_fg"],
                         font=("Segoe UI", 9), relief="flat", height=4)
    ig_list.pack(fill="x", padx=8, pady=2)
    for pat in cfg.ignore_patterns:
        ig_list.insert("end", pat)

    def _add_ig() -> None:
        dlg = tk.Toplevel(root)
        dlg.title("Add Ignore Pattern")
        dlg.configure(bg=t["bg"])
        dlg.geometry("300x110")
        tk.Label(dlg, text="Pattern (e.g. *.tmp):", bg=t["bg"], fg=t["fg"],
                 font=("Segoe UI", 10)).pack(pady=(10, 2))
        entry = tk.Entry(dlg, bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10))
        entry.pack(padx=16, fill="x")
        def _ok() -> None:
            p = entry.get().strip()
            if p:
                cfg.add_ignore_pattern(p)
                ig_list.insert("end", p)
            dlg.destroy()
        tk.Button(dlg, text="Add", bg=t["accent"], fg=t["bg"],
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=_ok).pack(pady=6)

    def _rm_ig() -> None:
        sel = ig_list.curselection()
        if sel:
            p = ig_list.get(sel[0])
            cfg.remove_ignore_pattern(p)
            ig_list.delete(sel[0])

    ig_btns = tk.Frame(f, bg=t["bg"])
    ig_btns.pack(anchor="w", padx=8)
    tk.Button(ig_btns, text="+ Add", bg=t["accent"], fg=t["bg"],
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_add_ig).pack(side="left", padx=(0, 4))
    tk.Button(ig_btns, text="- Remove", bg=t["danger"], fg="#ffffff",
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_rm_ig).pack(side="left")

    # ── Rename patterns ────────────────────────────────────────────────
    _section(f, "Rename Patterns (auto-rename on move)", t).pack(
        anchor="w", padx=8, pady=(10, 2)
    )
    tk.Label(
        f,
        text='Pattern tokens: {name} {ext} {date}  e.g. ".pdf" -> "{date}_{name}{ext}"',
        bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9, "italic"),
    ).pack(anchor="w", padx=8)

    rp_list = tk.Listbox(f, bg=t["list_bg"], fg=t["list_fg"],
                         selectbackground=t["list_select_bg"],
                         selectforeground=t["list_select_fg"],
                         font=("Segoe UI", 9), relief="flat", height=4)
    rp_list.pack(fill="x", padx=8, pady=2)

    def _fmt_rp(entry: dict) -> str:
        exts = ", ".join(entry.get("extensions", []))
        pat = entry.get("pattern", "")
        enabled = "" if entry.get("enabled", True) else " [disabled]"
        return f"{exts} -> {pat}{enabled}"

    for rp in cfg.rename_patterns:
        rp_list.insert("end", _fmt_rp(rp))

    def _add_rp() -> None:
        dlg = tk.Toplevel(root)
        dlg.title("Add Rename Pattern")
        dlg.configure(bg=t["bg"])
        dlg.geometry("380x180")

        def _row(r: int, lbl: str) -> tk.Entry:
            tk.Label(dlg, text=lbl, bg=t["bg"], fg=t["fg"],
                     font=("Segoe UI", 10)).grid(row=r, column=0, sticky="w", padx=12, pady=4)
            e = tk.Entry(dlg, bg=t["entry_bg"], fg=t["entry_fg"], font=("Segoe UI", 10), width=28)
            e.grid(row=r, column=1, padx=8, pady=4)
            return e

        ext_entry = _row(0, "Extensions (e.g. .pdf .doc):")
        pat_entry = _row(1, "Pattern (e.g. {date}_{name}{ext}):")

        def _ok() -> None:
            raw_exts = ext_entry.get().strip()
            pat = pat_entry.get().strip()
            if not raw_exts or not pat:
                dlg.destroy()
                return
            exts = [e if e.startswith(".") else f".{e}"
                    for e in raw_exts.split() if e]
            entry = {"extensions": exts, "pattern": pat, "enabled": True}
            cfg.rename_patterns.append(entry)  # mutate in-place
            cfg.save()
            rp_list.insert("end", _fmt_rp(entry))
            dlg.destroy()

        tk.Button(dlg, text="Add", bg=t["accent"], fg=t["bg"],
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  command=_ok).grid(row=2, column=0, columnspan=2, pady=8)

    def _rm_rp() -> None:
        sel = rp_list.curselection()
        if not sel:
            return
        idx = sel[0]
        patterns = cfg.rename_patterns
        if idx < len(patterns):
            del patterns[idx]
            cfg.save()
        rp_list.delete(idx)

    def _toggle_rp() -> None:
        sel = rp_list.curselection()
        if not sel:
            return
        idx = sel[0]
        patterns = cfg.rename_patterns
        if idx < len(patterns):
            patterns[idx]["enabled"] = not patterns[idx].get("enabled", True)
            cfg.save()
            rp_list.delete(idx)
            rp_list.insert(idx, _fmt_rp(patterns[idx]))

    rp_btns = tk.Frame(f, bg=t["bg"])
    rp_btns.pack(anchor="w", padx=8, pady=(0, 8))
    tk.Button(rp_btns, text="+ Add", bg=t["accent"], fg=t["bg"],
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_add_rp).pack(side="left", padx=(0, 4))
    tk.Button(rp_btns, text="- Remove", bg=t["danger"], fg="#ffffff",
              font=("Segoe UI", 9, "bold"), relief="flat",
              command=_rm_rp).pack(side="left", padx=(0, 4))
    tk.Button(rp_btns, text="Enable/Disable", bg=t["btn_bg"], fg=t["btn_fg"],
              font=("Segoe UI", 9), relief="flat",
              command=_toggle_rp).pack(side="left")


def _build_system_tab(nb: ttk.Notebook, cfg: "Config", t: dict, root: tk.Tk) -> dict:
    """Build the System tab: autostart, batch mode, import/export."""
    f = tk.Frame(nb, bg=t["bg"])
    nb.add(f, text="System")

    pad = {"padx": (0, 8), "pady": 4}

    _section(f, "Startup", t).grid(row=0, column=0, columnspan=2, sticky="w", pady=(12, 4))
    _label(f, "Start on login:", t).grid(row=1, column=0, sticky="w", **pad)
    autostart_var = tk.BooleanVar(value=is_autostart_enabled())
    _check(f, "Enabled", autostart_var, t).grid(row=1, column=1, sticky="w", **pad)

    _section(f, "Batch Processing", t).grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(12, 4)
    )
    _label(f, "Batch mode style:", t).grid(row=3, column=0, sticky="w", **pad)
    batch_var = tk.StringVar(value=cfg.get_setting("batch_mode_style", "one-by-one"))
    tk.OptionMenu(f, batch_var, "one-by-one", "batch-list").grid(
        row=3, column=1, sticky="ew", **pad
    )

    _section(f, "Config Backup", t).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=(12, 4)
    )

    io_frame = tk.Frame(f, bg=t["bg"])
    io_frame.grid(row=5, column=0, columnspan=2, sticky="w", pady=4)

    def _export() -> None:
        path = filedialog.asksaveasfilename(
            title="Export Config",
            defaultextension=".zip",
            filetypes=[("Zip files", "*.zip")],
            parent=root,
        )
        if path:
            cfg.export_config(path)
            messagebox.showinfo("Export", "Config exported successfully.", parent=root)

    def _import() -> None:
        path = filedialog.askopenfilename(
            title="Import Config",
            filetypes=[("Zip files", "*.zip")],
            parent=root,
        )
        if path:
            cfg.import_config(path)
            messagebox.showinfo(
                "Import", "Config imported. Restart File Wayfinder to apply.", parent=root
            )

    tk.Button(io_frame, text="Export Config...", bg=t["btn_bg"], fg=t["btn_fg"],
              font=("Segoe UI", 9), relief="flat", command=_export).pack(side="left", padx=(0, 6))
    tk.Button(io_frame, text="Import Config...", bg=t["btn_bg"], fg=t["btn_fg"],
              font=("Segoe UI", 9), relief="flat", command=_import).pack(side="left")

    f.columnconfigure(1, weight=1)
    return {
        "autostart": autostart_var,
        "batch_mode_style": batch_var,
    }


# ── Main dialog ───────────────────────────────────────────────────────

class SettingsDialog:
    """Tabbed modal settings window."""

    def __init__(self, config: "Config") -> None:
        self._config = config
        self._theme = get_theme(config.get_setting("theme", "dark"))

    def show(self) -> None:
        """Display the settings dialog (blocks until closed)."""
        t = self._theme
        cfg = self._config

        root = tk.Tk()
        root.title("File Wayfinder -- Settings")
        root.configure(bg=t["bg"])
        root.resizable(True, True)
        root.minsize(540, 520)

        w, h = 600, 600
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        # Style notebook to match theme
        style = ttk.Style(root)
        style.theme_use("default")
        style.configure("TNotebook", background=t["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=t["btn_bg"], foreground=t["btn_fg"],
                        padding=[10, 4], font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", t["accent"])],
                  foreground=[("selected", t["bg"])])

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=12, pady=(12, 4))

        gen_vars = _build_general_tab(nb, cfg, t)
        mon_vars = _build_monitoring_tab(nb, cfg, t)
        folder_vars = _build_folders_tab(nb, cfg, t, root)
        _build_rules_tab(nb, cfg, t, root)
        sys_vars = _build_system_tab(nb, cfg, t, root)

        # ── Save / Cancel buttons ──────────────────────────────────────
        def _save() -> None:
            settings: dict = {}
            # General
            for key, var in gen_vars.items():
                settings[key] = var.get()
            # Monitoring
            for key, var in mon_vars.items():
                settings[key] = var.get()
            # Folder quick-add options
            for key, var in folder_vars.items():
                settings[key] = var.get()
            # System
            settings["batch_mode_style"] = sys_vars["batch_mode_style"].get()

            cfg.save_many(settings)
            set_autostart(sys_vars["autostart"].get())
            logger.info("Settings saved.")
            root.destroy()

        btn_row = tk.Frame(root, bg=t["bg"])
        btn_row.pack(pady=8)
        tk.Button(
            btn_row, text="Save", bg=t["accent"], fg=t["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat", command=_save, width=10,
        ).pack(side="left", padx=6)
        tk.Button(
            btn_row, text="Cancel", bg=t["btn_bg"], fg=t["btn_fg"],
            font=("Segoe UI", 10), relief="flat", command=root.destroy, width=10,
        ).pack(side="left", padx=6)

        root.mainloop()



