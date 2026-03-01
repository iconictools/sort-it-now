# Sort It Now — Project Analysis & Design Questionnaire

> **Purpose:** This document rates the current state of the project and asks
> you (the project owner) about every unaddressed decision and improvement
> opportunity. Fill in your answers in the **→ Answer:** lines, then hand
> this back to guide the next round of development.

---

## 📊 Project Rating (current state)

| Category              | Score  | Notes                                                       |
|-----------------------|--------|-------------------------------------------------------------|
| Code Quality          | 8 / 10 | Clean separation of concerns; proper threading; no bare excepts |
| Test Coverage         | 4 / 10 | ~35% — core logic tested, but 0% on UI, integration, threading |
| Security              | 6 / 10 | Parameterised SQL ✅, but no path validation, no signing     |
| UX / Design           | 5 / 10 | Functional but bare-bones; no settings UI; limited feedback  |
| Documentation         | 7 / 10 | Good README; inline docstrings; no troubleshooting guide     |
| Cross-Platform        | 4 / 10 | Builds for 3 OSes but no signing, notarisation, or Wayland testing |
| Error Handling        | 3 / 10 | Most exceptions unhandled; no recovery or user-facing alerts |
| Build / CI            | 6 / 10 | Multi-platform ✅; missing linting, signing, version tags     |
| Feature Completeness  | 7 / 10 | Core loop works; polish & power-user features missing        |
| **Overall**           | **5.5 / 10** | **Usable for power users; not production-ready for a general audience** |

---

## 📝 Questionnaire

Fill in each **→ Answer:** to guide the next development iteration.

---

### 1 — Target Audience & Scope

**Q1.1** Who is the primary user?
(a) You personally  (b) Technical/power users  (c) General public / non-technical

→ Answer:

**Q1.2** What platforms must be supported at launch?
(a) Windows only  (b) macOS only  (c) Linux only  (d) All three  (e) Other

→ Answer:

**Q1.3** Should the app be distributable via a package manager?
(a) PyPI (`pip install sort-it-now`)  (b) Homebrew / Chocolatey / Snap  (c) Standalone binary only  (d) Not important yet

→ Answer:

---

### 2 — Installation & First Run

**Q2.1** On first launch the app currently opens a **tkinter Setup Wizard** to pick folders. Is that good enough, or would you prefer:
(a) Keep the GUI wizard  (b) A CLI/terminal questionnaire instead  (c) Both (user chooses)  (d) Just edit the JSON config manually

→ Answer:

**Q2.2** Should the app auto-start on login?
(a) Yes — provide a toggle in settings  (b) No — user starts it manually  (c) Ask during first run

→ Answer:

**Q2.3** Should the installer / first-run create **default monitored folders** automatically (e.g. ~/Downloads, ~/Desktop)?
(a) Yes, pre-fill common folders  (b) No, always ask the user  (c) Detect the OS and suggest intelligently

→ Answer:

---

### 3 — Monitoring Behaviour

**Q3.1** Should sub-folders inside a monitored folder also be watched (recursive)?
(a) Yes, always  (b) No, top-level only (current)  (c) Let the user choose per folder

→ Answer:

**Q3.2** The current prompt delay is **3 seconds** (wait for downloads to finish). Is that right for you?
(a) 3 s is fine  (b) Shorter (1–2 s)  (c) Longer (5–10 s)  (d) Make it configurable per folder

→ Answer:

**Q3.3** Should the watcher detect **file renames** and **file modifications**, or only new files?
(a) New files only  (b) New + renamed  (c) New + renamed + modified (current)  (d) Let the user choose

→ Answer:

**Q3.4** What should happen when the monitored folder itself is deleted or becomes unavailable (e.g. USB drive removed)?
(a) Show a warning notification  (b) Silently disable that folder and re-enable when it reappears  (c) Remove it from the config

→ Answer:

---

### 4 — Prompt & Classification UX

**Q4.1** The current prompt is a tkinter popup. Would you prefer:
(a) Keep tkinter (current)  (b) Native OS notifications with action buttons  (c) A web-based UI (browser)  (d) Terminal-based popup (curses/rich)

→ Answer:

**Q4.2** Should the prompt show a **file preview** (icon, first few lines of text, image thumbnail)?
(a) Yes — full preview  (b) Just the file icon + size  (c) No — file name is enough (current)

→ Answer:

**Q4.3** Should the prompt have a **timeout** (auto-dismiss after N seconds)?
(a) Yes, auto-ignore after ___ seconds  (b) Yes, auto-move to a default folder after ___ seconds  (c) No, wait forever (current)

→ Answer:

**Q4.4** Maximum number of destination buttons shown in the prompt? Currently **6**.
(a) 6 is fine  (b) Show all  (c) Show top 3 + "More…" expander  (d) Other: ___

→ Answer:

**Q4.5** Should the user be able to **create a new destination folder** directly from the prompt?
(a) Yes — add a "New folder…" button  (b) No — configure destinations beforehand only

→ Answer:

---

### 5 — Auto-Learning & Rules

**Q5.1** The app currently auto-learns a rule after **3 consistent choices** for the same extension. Good threshold?
(a) 3 is fine  (b) Make it configurable  (c) Lower (2)  (d) Higher (5+)

→ Answer:

**Q5.2** Should auto-rules be based on more than just file extension?
(a) Extension only (current)  (b) Extension + filename pattern (e.g. `invoice_*.pdf`)  (c) Extension + file size range  (d) Extension + source app (if detectable)  (e) All of the above

→ Answer:

**Q5.3** Should there be a **rule management UI** to view, edit, and delete learned rules?
(a) Yes — essential  (b) Nice to have  (c) Not needed — just edit the JSON

→ Answer:

**Q5.4** When an auto-rule fires (file moved silently), should the user be notified?
(a) Yes — brief toast/notification  (b) Yes — tray icon badge count  (c) No — silent is fine  (d) Configurable

→ Answer:

---

### 6 — Focus Mode & Batch Processing

**Q6.1** Focus mode currently **queues files** and processes them when toggled off. Should it also support a **timed snooze** (e.g. "snooze for 2 hours")?
(a) Yes — add snooze timer  (b) No — manual toggle is enough

→ Answer:

**Q6.2** When processing the batch queue, should all files be presented one-by-one or as a **batch list** where you check destinations?
(a) One-by-one prompts (current)  (b) A single window listing all pending files with dropdowns  (c) Let the user choose

→ Answer:

**Q6.3** Should the app integrate with system Do Not Disturb / Focus Assist modes?
(a) Yes — auto-pause when DND is on  (b) No — keep them independent

→ Answer:

---

### 7 — Dashboard & History

**Q7.1** The dashboard currently shows **recent actions** only. What else should it show?
(a) Add pending/queued files  (b) Add sorting statistics (files sorted today, this week)  (c) Add "Inbox Zero" progress bar  (d) Add rule management  (e) All of the above

→ Answer:

**Q7.2** Should undo support **bulk undo** (undo the last N actions at once)?
(a) Yes  (b) No — one at a time is fine (current)

→ Answer:

**Q7.3** How long should action history be kept?
(a) Forever  (b) Last 30 days  (c) Last 1000 actions  (d) Configurable

→ Answer:

---

### 8 — Error Handling & Resilience

**Q8.1** When a file move fails (permissions, disk full, destination gone), what should happen?
(a) Show error dialog + offer retry  (b) Log silently and skip  (c) Move to a fallback "unsorted" folder  (d) Configurable

→ Answer:

**Q8.2** If the config file is corrupted (bad JSON), should the app:
(a) Reset to defaults + back up the old file  (b) Show an error and refuse to start  (c) Try to repair the JSON

→ Answer:

**Q8.3** Should the app **log to a file** in addition to the console?
(a) Yes — always  (b) Yes — when `--verbose` is used  (c) No — console only (current)

→ Answer:

---

### 9 — Security & Privacy

**Q9.1** Should the config file permissions be restricted (e.g. `chmod 600`)?
(a) Yes — only the owner should read it  (b) Not important

→ Answer:

**Q9.2** Should destination folders be validated (prevent moving files outside a user-defined allowlist)?
(a) Yes — strict allowlist  (b) No — trust the user's config

→ Answer:

**Q9.3** For distributed builds, should executables be **code-signed**?
(a) Yes — macOS notarisation + Windows Authenticode  (b) Only if distributing publicly  (c) Not needed for now

→ Answer:

---

### 10 — Build, CI & Release

**Q10.1** Should CI also run **linting and type-checking** (e.g. `ruff`, `mypy`)?
(a) Yes — fail the build on lint errors  (b) Yes — report but don't fail  (c) Not needed

→ Answer:

**Q10.2** Should CI test against **multiple Python versions** (3.9, 3.10, 3.11, 3.12)?
(a) Yes — matrix build  (b) No — latest only is fine

→ Answer:

**Q10.3** Should releases be **automated** (tag → build → GitHub Release with changelog)?
(a) Yes — automatic on tag push  (b) No — manual releases are fine

→ Answer:

**Q10.4** Should the project be **published to PyPI**?
(a) Yes  (b) Not yet  (c) Never

→ Answer:

---

### 11 — Future Features (Priority Check)

Rate each feature: **H**igh / **M**edium / **L**ow / **N**o (don't want it).

| # | Feature | Priority |
|---|---------|----------|
| 11.1 | Settings dialog (GUI to edit config without touching JSON) | |
| 11.2 | Rule management UI (view/edit/delete learned rules) | |
| 11.3 | Global hotkey to open dashboard (e.g. Ctrl+Shift+S) | |
| 11.4 | Sorting statistics & streaks ("You sorted 47 files this week!") | |
| 11.5 | Custom destination sub-folder templates (e.g. `Documents/{year}/{month}/`) | |
| 11.6 | Multi-step rules (e.g. "if PDF AND > 5 MB → Archive") | |
| 11.7 | System tray tooltip showing pending count | |
| 11.8 | "Send to Trash" as a destination option | |
| 11.9 | Plugin / extension system for custom classifiers | |
| 11.10 | Cloud sync of config (e.g. via a Git repo or Dropbox) | |
| 11.11 | Sound / system notification on auto-sort | |
| 11.12 | Dark / light theme toggle | |
| 11.13 | Autostart on login (OS integration) | |
| 11.14 | Tray icon badge with pending file count | |
| 11.15 | Conflict resolution UI (merge / overwrite / rename) | |

---

### 12 — Anything Else?

**Q12.1** Is there anything about the current behaviour that bothers you?

→ Answer:

**Q12.2** Any feature from a competing tool you'd like to replicate?

→ Answer:

**Q12.3** Any hard constraints (e.g. "must stay under 50 MB", "no internet access")?

→ Answer:

---

## ✅ How to Use This

1. Fill in every **→ Answer:** line above.
2. Commit this file back to the repo (or paste your answers in a GitHub issue).
3. The next development round will use your answers to prioritise work.
