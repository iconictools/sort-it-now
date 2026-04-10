"""Rule management UI for Iconic File Filer (customtkinter-based).

Lets the user view, add, edit, and delete auto-sort rules through a
card-based interface that matches the main prompt design.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog
from typing import TYPE_CHECKING, Any, Callable

import customtkinter as ctk

from iconic_filer.themes import apply_ctk_appearance, get_theme

if TYPE_CHECKING:
    from iconic_filer.config import Config
    from iconic_filer.rules import Rules

logger = logging.getLogger(__name__)


def _font(size: int = 12, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight=weight)


class RulesDialog:
    """Full-featured window to view, add, edit and delete sorting rules."""

    def __init__(self, rules: "Rules", config: "Config") -> None:
        self._rules = rules
        self._theme_name = config.get_setting("theme", "dark")
        self._theme = get_theme(self._theme_name)

    # ── Helpers ───────────────────────────────────────────────────────

    def _rule_card(
        self,
        parent: Any,
        t: dict,
        label: str,
        sublabel: str,
        on_edit: "Callable[[], None] | None",
        on_delete: "Callable[[], None]",
    ) -> None:
        """Render a single rule row with Edit and Delete buttons."""
        card = ctk.CTkFrame(parent, fg_color=t["btn_bg"], corner_radius=8)
        card.pack(fill="x", pady=3)
        card.grid_columnconfigure(1, weight=1)

        # Rule text
        ctk.CTkLabel(
            card, text=label,
            font=_font(12, "bold"),
            text_color=t["btn_fg"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(12, 4), pady=(8, 0))

        ctk.CTkLabel(
            card, text=sublabel,
            font=_font(9),
            text_color=t["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=(12, 4), pady=(0, 8))

        # Action buttons (right side)
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.grid(row=0, column=2, rowspan=2, padx=(4, 10), pady=6, sticky="e")

        if on_edit is not None:
            ctk.CTkButton(
                btn_box,
                text="✎ Edit",
                width=64,
                height=28,
                fg_color="transparent",
                border_color=t["accent"],
                border_width=1,
                text_color=t["accent"],
                hover_color=t["btn_active"],
                font=_font(10),
                corner_radius=6,
                command=on_edit,
            ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_box,
            text="✕",
            width=30,
            height=28,
            fg_color="transparent",
            border_color=t["danger"],
            border_width=1,
            text_color=t["danger"],
            hover_color=t["btn_bg"],
            font=_font(10, "bold"),
            corner_radius=6,
            command=on_delete,
        ).pack(side="left")

    # ── Main window ───────────────────────────────────────────────────

    def show(self) -> None:
        """Display the rule management dialog."""
        t = self._theme
        apply_ctk_appearance(self._theme_name)

        root = ctk.CTk()
        root.title("Iconic File Filer — Sorting Rules")
        root.resizable(True, True)

        w, h = 580, 680
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = max(40, root.winfo_screenheight() // 2 - h // 2)
        root.geometry(f"{w}x{h}+{sx}+{sy}")
        root.minsize(480, 500)
        root.attributes("-topmost", True)
        root.lift()
        root.after(300, lambda: root.attributes("-topmost", False))

        # ── Header ────────────────────────────────────────────────────
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            header,
            text="⚙",
            font=_font(26),
            width=44,
        ).pack(side="left", padx=(0, 10))

        htext = ctk.CTkFrame(header, fg_color="transparent")
        htext.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            htext,
            text="Sorting Rules Manager",
            font=_font(16, "bold"),
            text_color=t["accent"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            htext,
            text="Automatic sorting rules — applied before the prompt appears.",
            font=_font(9),
            text_color=t["muted"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkFrame(root, fg_color=t["btn_bg"], height=1).pack(
            fill="x", padx=24, pady=(12, 0)
        )

        # ── Tabs ──────────────────────────────────────────────────────
        tabs = ctk.CTkTabview(root, anchor="w")
        tabs.pack(fill="both", expand=True, padx=16, pady=4)
        tabs.add("Extension Rules")
        tabs.add("Pattern Rules")

        # ═════════════════════════════════════════════════════════════
        # Tab 1 — Extension Rules
        # ═════════════════════════════════════════════════════════════
        ext_tab = tabs.tab("Extension Rules")

        ctk.CTkLabel(
            ext_tab,
            text="Map a file extension to a destination folder.",
            font=_font(9),
            text_color=t["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(4, 8))

        # Rule cards
        ext_scroll = ctk.CTkScrollableFrame(
            ext_tab, fg_color="transparent", height=260
        )
        ext_scroll.pack(fill="both", expand=True)

        def _rebuild_ext_cards() -> None:
            for w in ext_scroll.winfo_children():
                w.destroy()
            ext_map = self._rules.extension_map
            if not ext_map:
                ctk.CTkLabel(
                    ext_scroll,
                    text="No extension rules yet.",
                    font=_font(10),
                    text_color=t["muted"],
                ).pack(pady=20)
                return
            for ext, dest in sorted(ext_map.items()):
                _ext, _dest = ext, dest  # capture loop vars

                def _edit(e: str = _ext, d: str = _dest) -> None:
                    new_dest = filedialog.askdirectory(
                        title=f"New destination for {e}", parent=root
                    )
                    if new_dest:
                        self._rules.set_rule(e, new_dest)
                        _rebuild_ext_cards()

                def _delete(e: str = _ext) -> None:
                    self._rules.remove_rule(e)
                    _rebuild_ext_cards()

                dest_name = os.path.basename(dest) or dest
                home = os.path.expanduser("~")
                short = dest.replace(home, "~") if dest.startswith(home) else dest
                self._rule_card(
                    ext_scroll, t,
                    label=f"{ext}  →  {dest_name}",
                    sublabel=short,
                    on_edit=_edit,
                    on_delete=_delete,
                )

        _rebuild_ext_cards()

        # Add-rule form at the bottom
        ctk.CTkFrame(ext_tab, fg_color=t["btn_bg"], height=1).pack(
            fill="x", pady=(10, 8)
        )

        add_ext_frame = ctk.CTkFrame(ext_tab, fg_color="transparent")
        add_ext_frame.pack(fill="x")
        add_ext_frame.grid_columnconfigure(0, weight=1)

        ext_var = tk.StringVar()
        ctk.CTkEntry(
            add_ext_frame,
            textvariable=ext_var,
            placeholder_text=".ext   (e.g. .pdf)",
            font=_font(11),
            border_color=t["accent"],
            height=36,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        def _add_ext_rule() -> None:
            ext = ext_var.get().strip()
            if not ext:
                return
            dest = filedialog.askdirectory(
                title=f"Destination folder for {ext}", parent=root
            )
            if dest:
                self._rules.set_rule(ext, dest)
                ext_var.set("")
                _rebuild_ext_cards()

        ctk.CTkButton(
            add_ext_frame,
            text="+ Add rule",
            height=36,
            fg_color=t["accent"],
            text_color="#1e1e2e",
            hover_color=t["btn_active"],
            font=_font(11, "bold"),
            corner_radius=8,
            command=_add_ext_rule,
        ).grid(row=0, column=1, sticky="e")

        # ═════════════════════════════════════════════════════════════
        # Tab 2 — Pattern Rules
        # ═════════════════════════════════════════════════════════════
        pat_tab = tabs.tab("Pattern Rules")

        ctk.CTkLabel(
            pat_tab,
            text="Match filenames by glob pattern (e.g. invoice*.pdf) or regex.",
            font=_font(9),
            text_color=t["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(4, 8))

        pat_scroll = ctk.CTkScrollableFrame(
            pat_tab, fg_color="transparent", height=260
        )
        pat_scroll.pack(fill="both", expand=True)

        def _rebuild_pat_cards() -> None:
            for w in pat_scroll.winfo_children():
                w.destroy()
            rules = self._rules.pattern_rules
            if not rules:
                ctk.CTkLabel(
                    pat_scroll,
                    text="No pattern rules yet.",
                    font=_font(10),
                    text_color=t["muted"],
                ).pack(pady=20)
                return
            for rule in rules:
                _pat = rule["pattern"]
                _rtype = rule.get("type", "glob")
                _dest = rule["destination"]

                def _delete(p: str = _pat) -> None:
                    self._rules.remove_pattern_rule(p)
                    _rebuild_pat_cards()

                dest_name = os.path.basename(_dest) or _dest
                home = os.path.expanduser("~")
                short = _dest.replace(home, "~") if _dest.startswith(home) else _dest
                self._rule_card(
                    pat_scroll, t,
                    label=f"[{_rtype}]  {_pat}  →  {dest_name}",
                    sublabel=short,
                    on_edit=None,   # pattern identity is the key; add new instead
                    on_delete=_delete,
                )

        _rebuild_pat_cards()

        # Add-pattern form at the bottom
        ctk.CTkFrame(pat_tab, fg_color=t["btn_bg"], height=1).pack(
            fill="x", pady=(10, 8)
        )

        add_pat_frame = ctk.CTkFrame(pat_tab, fg_color="transparent")
        add_pat_frame.pack(fill="x")
        add_pat_frame.grid_columnconfigure(0, weight=1)

        pat_var = tk.StringVar()
        ctk.CTkEntry(
            add_pat_frame,
            textvariable=pat_var,
            placeholder_text="Pattern  (e.g. invoice*.pdf)",
            font=_font(11),
            border_color=t["accent"],
            height=36,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        type_var = tk.StringVar(value="glob")
        ctk.CTkOptionMenu(
            add_pat_frame,
            variable=type_var,
            values=["glob", "regex"],
            width=90,
            height=36,
            font=_font(10),
        ).grid(row=0, column=1, padx=(0, 8))

        def _add_pat_rule() -> None:
            pat = pat_var.get().strip()
            if not pat:
                return
            dest = filedialog.askdirectory(
                title=f"Destination folder for '{pat}'", parent=root
            )
            if dest:
                self._rules.set_pattern_rule(pat, dest, type_var.get())
                pat_var.set("")
                _rebuild_pat_cards()

        ctk.CTkButton(
            add_pat_frame,
            text="+ Add rule",
            height=36,
            fg_color=t["accent"],
            text_color="#1e1e2e",
            hover_color=t["btn_active"],
            font=_font(11, "bold"),
            corner_radius=8,
            command=_add_pat_rule,
        ).grid(row=0, column=2, sticky="e")

        # ── Footer ────────────────────────────────────────────────────
        ctk.CTkFrame(root, fg_color=t["btn_bg"], height=1).pack(
            fill="x", padx=24, pady=(4, 0)
        )
        footer = ctk.CTkFrame(root, fg_color="transparent")
        footer.pack(fill="x", padx=24, pady=(6, 16))

        ctk.CTkLabel(
            footer,
            text="Rules run automatically — no prompt shown when a rule matches.",
            font=_font(9),
            text_color=t["muted"],
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="Close",
            height=32,
            fg_color=t["btn_bg"],
            text_color=t["btn_fg"],
            hover_color=t["muted"],
            font=_font(10),
            corner_radius=8,
            width=80,
            command=root.destroy,
        ).pack(side="right")

        root.mainloop()
