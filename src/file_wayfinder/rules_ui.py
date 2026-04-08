"""Rule management UI for File Wayfinder (customtkinter-based).

Lets the user view, edit, and delete learned auto-sort rules.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from file_wayfinder.themes import apply_ctk_appearance, get_theme

if TYPE_CHECKING:
    from file_wayfinder.config import Config
    from file_wayfinder.rules import Rules

logger = logging.getLogger(__name__)


class RulesDialog:
    """Window to manage learned auto-sort rules."""

    def __init__(self, rules: "Rules", config: "Config") -> None:
        self._rules = rules
        self._theme_name = config.get_setting("theme", "dark")
        self._theme = get_theme(self._theme_name)

    def show(self) -> None:
        """Display the rule management dialog."""
        t = self._theme
        apply_ctk_appearance(self._theme_name)

        root = ctk.CTk()
        root.title("File Wayfinder — Rules")
        root.resizable(True, True)

        w, h = 560, 680
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        ctk.CTkLabel(
            root, text="⚙ Auto-Sort Rules",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=t["accent"],
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            root,
            text="Extensions are mapped to destination folders.",
            font=ctk.CTkFont(size=10),
            text_color=t["muted"],
        ).pack(pady=(0, 8))

        # ── Extension rules list ──────────────────────────────────────
        ctk.CTkLabel(
            root, text="Extension Rules",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=t["accent"],
        ).pack(anchor="w", padx=24, pady=(4, 2))

        list_frame = tk.Frame(root, bg=t["list_bg"])
        list_frame.pack(fill="both", expand=True, padx=24, pady=4)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(
            list_frame,
            bg=t["list_bg"], fg=t["list_fg"],
            selectbackground=t["list_select_bg"],
            selectforeground=t["list_select_fg"],
            font=("TkDefaultFont", 10), relief="flat",
            yscrollcommand=scrollbar.set,
        )
        listbox.pack(fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def _refresh() -> None:
            listbox.delete(0, "end")
            for ext, dest in sorted(self._rules.extension_map.items()):
                dest_name = os.path.basename(dest) if os.path.sep in dest else dest
                listbox.insert("end", f"  {ext}  →  {dest_name}  ({dest})")

        _refresh()

        # Buttons for extension rules
        btn_frame = ctk.CTkFrame(root, fg_color="transparent")
        btn_frame.pack(pady=6)

        def _add_rule() -> None:
            dlg = ctk.CTkToplevel(root)
            dlg.title("Add Rule")
            dlg.geometry("340x180")
            dlg.attributes("-topmost", True)
            dlg.grab_set()

            ctk.CTkLabel(
                dlg, text="Extension (e.g. .pdf):",
                font=ctk.CTkFont(size=11),
            ).pack(pady=(16, 4))
            ext_entry = ctk.CTkEntry(
                dlg, font=ctk.CTkFont(size=11),
                border_color=t["accent"],
            )
            ext_entry.pack(padx=24, fill="x")

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

            ctk.CTkButton(
                dlg, text="Choose destination…",
                fg_color=t["accent"], text_color="#1e1e2e",
                hover_color=t["btn_active"],
                font=ctk.CTkFont(size=11, weight="bold"),
                corner_radius=8,
                command=_pick_and_save,
            ).pack(pady=16)

        def _edit_rule() -> None:
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            ext = text.strip().split("  →  ")[0].strip()
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
            ext = text.strip().split("  →  ")[0].strip()
            if messagebox.askyesno(
                "Delete rule", f"Remove the rule for {ext}?", parent=root
            ):
                self._rules.remove_rule(ext)
                _refresh()

        ctk.CTkButton(
            btn_frame, text="+ Add",
            fg_color=t["accent"], text_color="#1e1e2e",
            hover_color=t["btn_active"],
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=8, width=90,
            command=_add_rule,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Edit",
            fg_color=t["btn_bg"], text_color=t["btn_fg"],
            hover_color=t["muted"],
            font=ctk.CTkFont(size=10),
            corner_radius=8, width=90,
            command=_edit_rule,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Delete",
            fg_color=t["danger"], text_color="#ffffff",
            hover_color="#c9374a",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=8, width=90,
            command=_delete_rule,
        ).pack(side="left", padx=4)

        # ── Pattern rules section ─────────────────────────────────────
        ctk.CTkLabel(
            root, text="Pattern Rules (glob/regex)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=t["accent"],
        ).pack(anchor="w", padx=24, pady=(12, 4))

        pat_frame = tk.Frame(root, bg=t["list_bg"])
        pat_frame.pack(fill="both", expand=True, padx=24, pady=4)

        pat_scrollbar = tk.Scrollbar(pat_frame)
        pat_scrollbar.pack(side="right", fill="y")

        pat_listbox = tk.Listbox(
            pat_frame,
            bg=t["list_bg"], fg=t["list_fg"],
            selectbackground=t["list_select_bg"],
            selectforeground=t["list_select_fg"],
            font=("TkDefaultFont", 10), relief="flat",
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
                    f"  [{rule.get('type', 'glob')}]  "
                    f"{rule['pattern']}  →  {dest_name}",
                )

        _refresh_patterns()

        pat_btn_frame = ctk.CTkFrame(root, fg_color="transparent")
        pat_btn_frame.pack(pady=6)

        def _add_pattern_rule() -> None:
            dlg = ctk.CTkToplevel(root)
            dlg.title("Add Pattern Rule")
            dlg.geometry("380x240")
            dlg.attributes("-topmost", True)
            dlg.grab_set()

            ctk.CTkLabel(
                dlg, text="Pattern (e.g. invoice*.pdf):",
                font=ctk.CTkFont(size=11),
            ).pack(pady=(16, 4))
            pat_entry = ctk.CTkEntry(
                dlg, font=ctk.CTkFont(size=11),
                border_color=t["accent"],
            )
            pat_entry.pack(padx=24, fill="x")

            ctk.CTkLabel(
                dlg, text="Type:",
                font=ctk.CTkFont(size=11),
            ).pack(pady=(12, 4))
            type_var = tk.StringVar(value="glob")
            ctk.CTkOptionMenu(
                dlg, variable=type_var, values=["glob", "regex"],
                font=ctk.CTkFont(size=11),
            ).pack()

            def _pick_dest() -> None:
                pat = pat_entry.get().strip()
                if not pat:
                    return
                dest = filedialog.askdirectory(
                    title=f"Destination for {pat}", parent=dlg
                )
                if dest:
                    self._rules.set_pattern_rule(pat, dest, type_var.get())
                    _refresh_patterns()
                    dlg.destroy()

            ctk.CTkButton(
                dlg, text="Choose destination…",
                fg_color=t["accent"], text_color="#1e1e2e",
                hover_color=t["btn_active"],
                font=ctk.CTkFont(size=11, weight="bold"),
                corner_radius=8,
                command=_pick_dest,
            ).pack(pady=16)

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

        ctk.CTkButton(
            pat_btn_frame, text="+ Add Pattern",
            fg_color=t["accent"], text_color="#1e1e2e",
            hover_color=t["btn_active"],
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=8, width=120,
            command=_add_pattern_rule,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            pat_btn_frame, text="Delete Pattern",
            fg_color=t["danger"], text_color="#ffffff",
            hover_color="#c9374a",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=8, width=120,
            command=_delete_pattern_rule,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            root, text="Close",
            fg_color=t["btn_bg"], text_color=t["btn_fg"],
            hover_color=t["muted"],
            font=ctk.CTkFont(size=11),
            corner_radius=8, width=100,
            command=root.destroy,
        ).pack(pady=(4, 16))

        root.mainloop()
