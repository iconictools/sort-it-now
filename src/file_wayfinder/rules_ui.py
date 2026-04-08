"""Rule management UI for File Wayfinder (tkinter-based).

Lets the user view, edit, and delete learned auto-sort rules.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from file_wayfinder.themes import get_theme

if TYPE_CHECKING:
    from file_wayfinder.config import Config
    from file_wayfinder.rules import Rules

logger = logging.getLogger(__name__)


class RulesDialog:
    """Window to manage learned auto-sort rules."""

    def __init__(self, rules: Rules, config: Config) -> None:
        self._rules = rules
        self._theme = get_theme(config.get_setting("theme", "dark"))

    def show(self) -> None:
        """Display the rule management dialog."""
        t = self._theme
        root = tk.Tk()
        root.title("File Wayfinder -- Rules")
        root.configure(bg=t["bg"])
        root.resizable(False, False)

        w, h = 520, 640
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        tk.Label(
            root, text="Auto-Sort Rules",
            bg=t["bg"], fg=t["accent"],
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(16, 4))
        tk.Label(
            root,
            text="Extensions are mapped to destination folders.",
            bg=t["bg"], fg=t["muted"], font=("Segoe UI", 9),
        ).pack(pady=(0, 8))

        # Rule list
        list_frame = tk.Frame(root, bg=t["bg"])
        list_frame.pack(fill="both", expand=True, padx=24, pady=4)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(
            list_frame,
            bg=t["list_bg"], fg=t["list_fg"],
            selectbackground=t["list_select_bg"],
            selectforeground=t["list_select_fg"],
            font=("Segoe UI", 10), relief="flat",
            yscrollcommand=scrollbar.set,
        )
        listbox.pack(fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def _refresh() -> None:
            listbox.delete(0, "end")
            for ext, dest in sorted(self._rules.extension_map.items()):
                dest_name = os.path.basename(dest) if os.path.sep in dest else dest
                listbox.insert("end", f"{ext}  ->  {dest_name}  ({dest})")

        _refresh()

        # Buttons
        btn_frame = tk.Frame(root, bg=t["bg"])
        btn_frame.pack(pady=8)

        def _add_rule() -> None:
            dlg = tk.Toplevel(root)
            dlg.title("Add Rule")
            dlg.configure(bg=t["bg"])
            dlg.geometry("320x150")
            dlg.attributes("-topmost", True)

            tk.Label(
                dlg, text="Extension (e.g. .pdf):", bg=t["bg"], fg=t["fg"],
                font=("Segoe UI", 10),
            ).pack(pady=(12, 2))
            ext_entry = tk.Entry(
                dlg, bg=t["entry_bg"], fg=t["entry_fg"],
                font=("Segoe UI", 10),
            )
            ext_entry.pack(padx=20, fill="x")

            def _pick_and_save() -> None:
                ext = ext_entry.get().strip()
                if not ext:
                    return
                dest = filedialog.askdirectory(
                    title=f"Destination for {ext}", parent=dlg
                )
                if dest:
                    self._rules.set_rule(ext, dest)
                    _refresh()
                    dlg.destroy()

            tk.Button(
                dlg, text="Choose destination...", bg=t["accent"], fg=t["bg"],
                font=("Segoe UI", 10, "bold"), relief="flat",
                command=_pick_and_save,
            ).pack(pady=12)

        def _edit_rule() -> None:
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            ext = text.split("  ->  ")[0].strip()
            dest = filedialog.askdirectory(
                title=f"New destination for {ext}", parent=root
            )
            if dest:
                self._rules.set_rule(ext, dest)
                _refresh()

        def _delete_rule() -> None:
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            ext = text.split("  ->  ")[0].strip()
            if messagebox.askyesno(
                "Delete rule", f"Remove the rule for {ext}?", parent=root
            ):
                self._rules.remove_rule(ext)
                _refresh()

        tk.Button(
            btn_frame, text="+ Add", bg=t["accent"], fg=t["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat", command=_add_rule,
            width=8,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_frame, text="Edit", bg=t["btn_bg"], fg=t["btn_fg"],
            font=("Segoe UI", 10), relief="flat", command=_edit_rule,
            width=8,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_frame, text="Delete", bg=t["danger"], fg="#ffffff",
            font=("Segoe UI", 10, "bold"), relief="flat",
            command=_delete_rule, width=8,
        ).pack(side="left", padx=4)

        tk.Button(
            root, text="Close", bg=t["btn_bg"], fg=t["btn_fg"],
            font=("Segoe UI", 10), relief="flat", command=root.destroy,
            width=10,
        ).pack(pady=(0, 12))

        # -- Pattern Rules Section --
        tk.Label(
            root, text="Pattern Rules (glob/regex):",
            bg=t["bg"], fg=t["accent"],
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(4, 4), padx=24, anchor="w")

        pat_frame = tk.Frame(root, bg=t["bg"])
        pat_frame.pack(fill="both", expand=True, padx=24, pady=4)

        pat_scrollbar = tk.Scrollbar(pat_frame)
        pat_scrollbar.pack(side="right", fill="y")

        pat_listbox = tk.Listbox(
            pat_frame,
            bg=t["list_bg"], fg=t["list_fg"],
            selectbackground=t["list_select_bg"],
            selectforeground=t["list_select_fg"],
            font=("Segoe UI", 10), relief="flat",
            yscrollcommand=pat_scrollbar.set,
        )
        pat_listbox.pack(fill="both", expand=True)
        pat_scrollbar.config(command=pat_listbox.yview)

        def _refresh_patterns() -> None:
            pat_listbox.delete(0, "end")
            for rule in self._rules.pattern_rules:
                dest_name = os.path.basename(rule["destination"])
                pat_listbox.insert(
                    "end",
                    f"[{rule.get('type', 'glob')}]  "
                    f"{rule['pattern']}  ->  {dest_name}",
                )

        _refresh_patterns()

        pat_btn_frame = tk.Frame(root, bg=t["bg"])
        pat_btn_frame.pack(pady=4)

        def _add_pattern_rule() -> None:
            dlg = tk.Toplevel(root)
            dlg.title("Add Pattern Rule")
            dlg.configure(bg=t["bg"])
            dlg.geometry("360x220")
            dlg.attributes("-topmost", True)

            tk.Label(
                dlg, text="Pattern (e.g. invoice*.pdf):",
                bg=t["bg"], fg=t["fg"], font=("Segoe UI", 10),
            ).pack(pady=(12, 2))
            pat_entry = tk.Entry(
                dlg, bg=t["entry_bg"], fg=t["entry_fg"],
                font=("Segoe UI", 10),
            )
            pat_entry.pack(padx=20, fill="x")

            tk.Label(
                dlg, text="Type:", bg=t["bg"], fg=t["fg"],
                font=("Segoe UI", 10),
            ).pack(pady=(8, 2))
            type_var = tk.StringVar(value="glob")
            type_menu = tk.OptionMenu(dlg, type_var, "glob", "regex")
            type_menu.config(
                bg=t["btn_bg"], fg=t["btn_fg"], font=("Segoe UI", 10),
                relief="flat",
            )
            type_menu.pack()

            def _pick_dest() -> None:
                pat = pat_entry.get().strip()
                if not pat:
                    return
                dest = filedialog.askdirectory(
                    title=f"Destination for {pat}", parent=dlg
                )
                if dest:
                    self._rules.set_pattern_rule(
                        pat, dest, type_var.get()
                    )
                    _refresh_patterns()
                    dlg.destroy()

            tk.Button(
                dlg, text="Choose destination...",
                bg=t["accent"], fg=t["bg"],
                font=("Segoe UI", 10, "bold"), relief="flat",
                command=_pick_dest,
            ).pack(pady=12)

        def _delete_pattern_rule() -> None:
            sel = pat_listbox.curselection()
            if not sel:
                return
            rules = self._rules.pattern_rules
            if sel[0] < len(rules):
                pattern = rules[sel[0]]["pattern"]
                if messagebox.askyesno(
                    "Delete pattern rule",
                    f"Remove the rule for '{pattern}'?",
                    parent=root,
                ):
                    self._rules.remove_pattern_rule(pattern)
                    _refresh_patterns()

        tk.Button(
            pat_btn_frame, text="+ Add Pattern",
            bg=t["accent"], fg=t["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat",
            command=_add_pattern_rule, width=12,
        ).pack(side="left", padx=4)
        tk.Button(
            pat_btn_frame, text="Delete Pattern",
            bg=t["danger"], fg="#ffffff",
            font=("Segoe UI", 10, "bold"), relief="flat",
            command=_delete_pattern_rule, width=12,
        ).pack(side="left", padx=4)

        root.mainloop()
