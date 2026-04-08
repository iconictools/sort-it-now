"""Extracted dashboard and batch-list windows for File Wayfinder."""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from file_wayfinder.themes import get_theme

logger = logging.getLogger(__name__)


def show_dashboard(
    config: Any,
    history: Any,
    batch_queue: list[str],
    lock: threading.Lock,
    watcher: Any,
    theme_name: str,
) -> None:
    """Open the enhanced dashboard window (blocks until closed)."""
    theme = get_theme(theme_name)

    root = tk.Tk()
    root.title("File Wayfinder -- Dashboard")
    root.configure(bg=theme["bg"])
    root.geometry("560x520")

    tk.Label(
        root,
        text="Dashboard",
        bg=theme["bg"], fg=theme["accent"],
        font=("Segoe UI", 16, "bold"),
    ).pack(pady=(16, 8))

    # -- Pending files --
    with lock:
        pending = len(batch_queue)
    if pending:
        tk.Label(
            root,
            text=f"Pending: {pending} file(s) in queue (focus mode)",
            bg=theme["bg"], fg=theme["danger"],
            font=("Segoe UI", 10),
        ).pack(pady=4)

    # -- Sorting stats --
    stats_frame = tk.Frame(root, bg=theme["bg"])
    stats_frame.pack(fill="x", padx=24, pady=4)

    total = history.total_count()
    today = history.count_since(time.time() - 86400)
    week = history.count_since(time.time() - 7 * 86400)

    tk.Label(
        stats_frame,
        text=f"Total sorted: {total}   |   Today: {today}   |   This week: {week}",
        bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 10),
    ).pack(anchor="w")

    # -- File type / destination taxonomy stats --
    try:
        rows = history.all_moves()
        ext_counts: dict[str, int] = {}
        dest_counts: dict[str, int] = {}
        for src_path, dst_path in rows:
            _, ext = os.path.splitext(src_path)
            if ext:
                ext_lower = ext.lower()
                ext_counts[ext_lower] = ext_counts.get(ext_lower, 0) + 1
            dest_name = os.path.basename(os.path.dirname(dst_path))
            if dest_name:
                dest_counts[dest_name] = dest_counts.get(dest_name, 0) + 1
        if ext_counts:
            top_exts = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ext_str = "  ".join(f"{e}×{c}" for e, c in top_exts)
            tax_frame = tk.Frame(root, bg=theme["bg"])
            tax_frame.pack(fill="x", padx=24, pady=(4, 0))
            tk.Label(
                tax_frame, text="Top file types:",
                bg=theme["bg"], fg=theme["accent"], font=("Segoe UI", 9, "bold"),
            ).pack(side="left")
            tk.Label(
                tax_frame, text=ext_str,
                bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 9),
            ).pack(side="left", padx=(6, 0))
        if dest_counts:
            top_dests = sorted(dest_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            dest_str = "  ".join(f"{d}×{c}" for d, c in top_dests)
            dest_tax_frame = tk.Frame(root, bg=theme["bg"])
            dest_tax_frame.pack(fill="x", padx=24, pady=(2, 0))
            tk.Label(
                dest_tax_frame, text="Top destinations:",
                bg=theme["bg"], fg=theme["accent"], font=("Segoe UI", 9, "bold"),
            ).pack(side="left")
            tk.Label(
                dest_tax_frame, text=dest_str,
                bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 9),
            ).pack(side="left", padx=(6, 0))
    except (sqlite3.Error, OSError, AttributeError):
        logger.debug("Taxonomy stats unavailable", exc_info=True)

    # -- Inbox Zero progress --
    if pending > 0 or today > 0:
        progress_frame = tk.Frame(root, bg=theme["bg"])
        progress_frame.pack(fill="x", padx=24, pady=4)
        processed = today - pending if today > pending else today
        ratio = max(0.0, processed / max(today, 1))
        bar_w = 400
        canvas = tk.Canvas(
            progress_frame, width=bar_w, height=20,
            bg=theme["list_bg"], highlightthickness=0,
        )
        canvas.pack(anchor="w")
        fill_w = int(bar_w * ratio)
        canvas.create_rectangle(
            0, 0, fill_w, 20, fill=theme["success"], outline=""
        )
        pct = int(ratio * 100)
        tk.Label(
            progress_frame,
            text=f"Inbox Zero: {pct}%",
            bg=theme["bg"], fg=theme["success"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

    # -- Activity Heatmap (last 84 days = 12 weeks) --
    heatmap_frame = tk.Frame(root, bg=theme["bg"])
    heatmap_frame.pack(fill="x", padx=24, pady=(8, 4))
    tk.Label(
        heatmap_frame, text="Activity (last 12 weeks):",
        bg=theme["bg"], fg=theme["accent"], font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w")

    day_counts: dict[int, int] = {}
    try:
        for timestamp in history.all_timestamps():
            day = int(timestamp // 86400)
            day_counts[day] = day_counts.get(day, 0) + 1
    except Exception:
        pass

    cell_size = 14
    gap = 2
    weeks = 12
    days_per_week = 7
    hm_w = cell_size * weeks + gap * (weeks - 1)
    hm_h = cell_size * days_per_week + gap * (days_per_week - 1)
    hm_canvas = tk.Canvas(
        heatmap_frame, width=hm_w, height=hm_h,
        bg=theme["bg"], highlightthickness=0,
    )
    hm_canvas.pack(anchor="w", pady=(4, 0))

    today_day = int(time.time() // 86400)
    total_cells = weeks * days_per_week
    for cell_idx in range(total_cells):
        # cell 0 = oldest, last cell = today (bottom-right)
        day_offset = total_cells - 1 - cell_idx
        day_key = today_day - day_offset
        count = day_counts.get(day_key, 0)
        col = cell_idx // days_per_week
        row = cell_idx % days_per_week
        x0 = col * (cell_size + gap)
        y0 = row * (cell_size + gap)
        x1 = x0 + cell_size
        y1 = y0 + cell_size
        if count == 0:
            color = theme["bg"]
        elif count <= 2:
            color = "#2d6a2d"
        elif count <= 5:
            color = "#3fa53f"
        else:
            color = theme["success"]
        hm_canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline=theme["list_bg"])

    # -- Achievements --
    from file_wayfinder.achievements import Achievements

    ach_label_frame = tk.Frame(root, bg=theme["bg"])
    ach_label_frame.pack(fill="x", padx=24, pady=(8, 2))
    tk.Label(
        ach_label_frame, text="Achievements:",
        bg=theme["bg"], fg=theme["accent"], font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w")

    try:
        ach_db = os.path.join(os.path.dirname(config.path), "achievements.db")
        achs = Achievements(ach_db)
        all_achs = achs.all_status()
        achs.close()
        ach_grid = tk.Frame(root, bg=theme["bg"])
        ach_grid.pack(fill="x", padx=24, pady=(0, 4))
        for idx, ach in enumerate(all_achs):
            col = idx % 3
            row = idx // 3
            fg_color = theme["success"] if ach.unlocked else theme["muted"]
            tk.Label(
                ach_grid,
                text=f"{ach.emoji} {ach.name}",
                bg=theme["bg"], fg=fg_color,
                font=("Segoe UI", 9),
                anchor="w",
            ).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=1)
    except Exception:
        logger.debug("Achievements panel unavailable", exc_info=True)

    # -- Rules summary --
    from file_wayfinder.rules import Rules

    rules_count = 0
    try:
        # Try to access rules through the config path
        rules_path = os.path.join(
            os.path.dirname(config.path), "rules.json"
        )
        if os.path.exists(rules_path):
            tmp_rules = Rules(rules_path)
            rules_count = len(tmp_rules.extension_map)
    except (OSError, AttributeError):
        pass

    tk.Label(
        root,
        text=f"Active rules: {rules_count}",
        bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 10),
    ).pack(padx=24, anchor="w", pady=(8, 4))

    # -- Undo history with clickable checkpoints --
    tk.Label(
        root,
        text="Recent Actions (click to undo back to that point):",
        bg=theme["bg"], fg=theme["accent"],
        font=("Segoe UI", 11, "bold"),
    ).pack(pady=(12, 4), padx=24, anchor="w")

    history_frame = tk.Frame(root, bg=theme["bg"])
    history_frame.pack(fill="both", expand=True, padx=24, pady=4)

    scrollbar = tk.Scrollbar(history_frame)
    scrollbar.pack(side="right", fill="y")

    history_list = tk.Listbox(
        history_frame,
        bg=theme["list_bg"], fg=theme["list_fg"],
        selectbackground=theme["list_select_bg"],
        selectforeground=theme["list_select_fg"],
        font=("Segoe UI", 9), relief="flat",
        yscrollcommand=scrollbar.set,
    )
    history_list.pack(fill="both", expand=True)
    scrollbar.config(command=history_list.yview)

    recent = history.recent(50)
    for action in recent:
        status = "[undone]" if action["undone"] else "[done]"
        src_name = os.path.basename(action["src_path"])
        dst_name = os.path.basename(os.path.dirname(action["dst_path"]))
        history_list.insert(
            "end", f"{status}  {src_name}  ->  {dst_name}"
        )

    def _undo_to_selected() -> None:
        sel = history_list.curselection()
        if not sel:
            return
        idx = sel[0]
        actions_to_undo = recent[: idx + 1]
        undone_count = 0
        for action in actions_to_undo:
            if not action["undone"]:
                result = history.undo_by_id(action["id"])
                if result:
                    watcher.mark_self_moved(result[1])
                    undone_count += 1
        if undone_count:
            logger.info("Bulk undone %d action(s).", undone_count)
        # Refresh list
        history_list.delete(0, "end")
        refreshed = history.recent(50)
        for action in refreshed:
            status = "[undone]" if action["undone"] else "[done]"
            src_name = os.path.basename(action["src_path"])
            dst_name = os.path.basename(
                os.path.dirname(action["dst_path"])
            )
            history_list.insert(
                "end", f"{status}  {src_name}  ->  {dst_name}"
            )

    btn_frame = tk.Frame(root, bg=theme["bg"])
    btn_frame.pack(pady=8)
    tk.Button(
        btn_frame, text="Undo to selected",
        bg=theme["accent"], fg=theme["bg"],
        font=("Segoe UI", 10, "bold"), relief="flat",
        command=_undo_to_selected,
    ).pack(side="left", padx=4)
    tk.Button(
        btn_frame, text="Close",
        bg=theme["btn_bg"], fg=theme["btn_fg"],
        font=("Segoe UI", 10), relief="flat",
        command=root.destroy,
    ).pack(side="left", padx=4)

    root.mainloop()


def show_batch_list(
    config: Any,
    rules: Any,
    watcher: Any,
    queue: list[str],
    theme_name: str,
    move_file_fn: Callable[[str, str], None],
) -> None:
    """Show a batch processing window listing all pending files."""
    theme = get_theme(theme_name)

    root = tk.Tk()
    root.title("File Wayfinder -- Batch Processing")
    root.configure(bg=theme["bg"])
    root.geometry("600x400")

    tk.Label(
        root,
        text=f"Batch: {len(queue)} file(s) pending",
        bg=theme["bg"], fg=theme["accent"],
        font=("Segoe UI", 14, "bold"),
    ).pack(pady=(16, 8))

    canvas = tk.Canvas(root, bg=theme["bg"], highlightthickness=0)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=theme["bg"])
    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=inner, anchor="nw", width=560)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(fill="both", expand=True, padx=16, pady=4)

    dest_vars: list[tuple[str, tk.StringVar]] = []

    all_dests: list[str] = []
    for folder in config.monitored_folders:
        for d in config.get_folder_destinations(folder):
            if d not in all_dests:
                all_dests.append(d)

    if not all_dests:
        tk.Label(
            inner,
            text="No destinations configured. Add folders in Settings.",
            bg=theme["bg"], fg=theme["danger"], font=("Segoe UI", 10),
        ).pack(pady=8)

    for filepath in queue:
        if not os.path.exists(filepath):
            continue
        row = tk.Frame(inner, bg=theme["bg"])
        row.pack(fill="x", pady=2)

        tk.Label(
            row, text=os.path.basename(filepath),
            bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 9),
            width=30, anchor="w",
        ).pack(side="left")

        dest_var = tk.StringVar(value=all_dests[0] if all_dests else "")
        if all_dests:
            menu = ttk.Combobox(
                row, textvariable=dest_var, values=all_dests,
                state="readonly", width=30,
            )
            menu.pack(side="left", padx=4)
        dest_vars.append((filepath, dest_var))

    def _process_all() -> None:
        for filepath, var in dest_vars:
            dest = var.get()
            if dest and os.path.exists(filepath):
                move_file_fn(filepath, dest)
                rules.record_action(filepath, dest)
        root.destroy()

    btn_frame = tk.Frame(root, bg=theme["bg"])
    btn_frame.pack(pady=8)
    tk.Button(
        btn_frame, text="Move All",
        bg=theme["accent"], fg=theme["bg"],
        font=("Segoe UI", 10, "bold"), relief="flat",
        command=_process_all,
    ).pack(side="left", padx=4)
    tk.Button(
        btn_frame, text="Cancel",
        bg=theme["btn_bg"], fg=theme["btn_fg"],
        font=("Segoe UI", 10), relief="flat",
        command=root.destroy,
    ).pack(side="left", padx=4)

    root.mainloop()
