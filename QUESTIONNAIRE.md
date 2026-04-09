# Iconic File Filer — Project Analysis & Design Questionnaire

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

→ Answer: **(a)** You personally

**Q1.2** What platforms must be supported at launch?
(a) Windows only  (b) macOS only  (c) Linux only  (d) All three  (e) Other

→ Answer: **(e)** Windows and Linux

**Q1.3** Should the app be distributable via a package manager?
(a) PyPI (`pip install iconic-filer`)  (b) Homebrew / Chocolatey / Snap  (c) Standalone binary only  (d) Not important yet

→ Answer: **(c)** Standalone binary only

---

### 2 — Installation & First Run

**Q2.1** On first launch the app currently opens a **tkinter Setup Wizard** to pick folders. Is that good enough, or would you prefer:
(a) Keep the GUI wizard  (b) A CLI/terminal questionnaire instead  (c) Both (user chooses)  (d) Just edit the JSON config manually

→ Answer: **(c)** Both (user chooses)

**Q2.2** Should the app auto-start on login?
(a) Yes — provide a toggle in settings  (b) No — user starts it manually  (c) Ask during first run

→ Answer: **(a)** Yes — provide a toggle in settings

**Q2.3** Should the installer / first-run create **default monitored folders** automatically (e.g. ~/Downloads, ~/Desktop)?
(a) Yes, pre-fill common folders  (b) No, always ask the user  (c) Detect the OS and suggest intelligently

→ Answer: **(b)** No, always ask the user

---

### 3 — Monitoring Behaviour

**Q3.1** Should sub-folders inside a monitored folder also be watched (recursive)?
(a) Yes, always  (b) No, top-level only (current)  (c) Let the user choose per folder

→ Answer: **(b)** No, top-level only. If the user wants a subfolder watched, they should add it explicitly.

**Q3.2** The current prompt delay is **3 seconds** (wait for downloads to finish). Is that right for you?
(a) 3 s is fine  (b) Shorter (1–2 s)  (c) Longer (5–10 s)  (d) Make it configurable per folder

→ Answer: **(a)** 3 s is fine

**Q3.3** Should the watcher detect **file renames** and **file modifications**, or only new files?
(a) New files only  (b) New + renamed  (c) New + renamed + modified (current)  (d) Let the user choose

→ Answer: **(a)** New files only — but renames/modifications of whitelisted items should be smartly tracked too.

**Q3.4** What should happen when the monitored folder itself is deleted or becomes unavailable (e.g. USB drive removed)?
(a) Show a warning notification  (b) Silently disable that folder and re-enable when it reappears  (c) Remove it from the config

→ Answer: **(a)** Show a warning notification. Prompt the user to change the selected folder, or to create a new one under the same name if applicable.

---

### 4 — Prompt & Classification UX

**Q4.1** The current prompt is a tkinter popup. Would you prefer:
(a) Keep tkinter (current)  (b) Native OS notifications with action buttons  (c) A web-based UI (browser)  (d) Terminal-based popup (curses/rich)

→ Answer: **(b)** Native OS notifications with action buttons

**Q4.2** Should the prompt show a **file preview** (icon, first few lines of text, image thumbnail)?
(a) Yes — full preview  (b) Just the file icon + size  (c) No — file name is enough (current)

→ Answer: **(b)** Just the file icon + size

**Q4.3** Should the prompt have a **timeout** (auto-dismiss after N seconds)?
(a) Yes, auto-ignore after ___ seconds  (b) Yes, auto-move to a default folder after ___ seconds  (c) No, wait forever (current)

→ Answer: **(c)** No, wait forever

**Q4.4** Maximum number of destination buttons shown in the prompt? Currently **6**.
(a) 6 is fine  (b) Show all  (c) Show top 3 + "More…" expander  (d) Other: ___

→ Answer: **(a + b)** Show all destinations — add a scroll if needed, go smart about this.

**Q4.5** Should the user be able to **create a new destination folder** directly from the prompt?
(a) Yes — add a "New folder…" button  (b) No — configure destinations beforehand only

→ Answer: **(a)** Yes — add a "New folder…" button

---

### 5 — Auto-Learning & Rules

**Q5.1** The app currently auto-learns a rule after **3 consistent choices** for the same extension. Good threshold?
(a) 3 is fine  (b) Make it configurable  (c) Lower (2)  (d) Higher (5+)

→ Answer: This rule should be **optional and configurable**.

**Q5.2** Should auto-rules be based on more than just file extension?
(a) Extension only (current)  (b) Extension + filename pattern (e.g. `invoice_*.pdf`)  (c) Extension + file size range  (d) Extension + source app (if detectable)  (e) All of the above

→ Answer: *(no preference stated)*

**Q5.3** Should there be a **rule management UI** to view, edit, and delete learned rules?
(a) Yes — essential  (b) Nice to have  (c) Not needed — just edit the JSON

→ Answer: **(a)** Yes — essential

**Q5.4** When an auto-rule fires (file moved silently), should the user be notified?
(a) Yes — brief toast/notification  (b) Yes — tray icon badge count  (c) No — silent is fine  (d) Configurable

→ Answer: **(c)** Silent is fine, but it should be logged like every move in the app.

---

### 6 — Focus Mode & Batch Processing

**Q6.1** Focus mode currently **queues files** and processes them when toggled off. Should it also support a **timed snooze** (e.g. "snooze for 2 hours")?
(a) Yes — add snooze timer  (b) No — manual toggle is enough

→ Answer: **(b)** No — manual toggle is enough

**Q6.2** When processing the batch queue, should all files be presented one-by-one or as a **batch list** where you check destinations?
(a) One-by-one prompts (current)  (b) A single window listing all pending files with dropdowns  (c) Let the user choose

→ Answer: **(c)** Let the user choose

**Q6.3** Should the app integrate with system Do Not Disturb / Focus Assist modes?
(a) Yes — auto-pause when DND is on  (b) No — keep them independent

→ Answer: Make it a choice (user decides)

---

### 7 — Dashboard & History

**Q7.1** The dashboard currently shows **recent actions** only. What else should it show?
(a) Add pending/queued files  (b) Add sorting statistics (files sorted today, this week)  (c) Add "Inbox Zero" progress bar  (d) Add rule management  (e) All of the above

→ Answer: **(e)** All of the above

**Q7.2** Should undo support **bulk undo** (undo the last N actions at once)?
(a) Yes  (b) No — one at a time is fine (current)

→ Answer: A history list with checkpoints you can click to go back to.

**Q7.3** How long should action history be kept?
(a) Forever  (b) Last 30 days  (c) Last 1000 actions  (d) Configurable

→ Answer: **(c)** Last 1000 actions

---

### 8 — Error Handling & Resilience

**Q8.1** When a file move fails (permissions, disk full, destination gone), what should happen?
(a) Show error dialog + offer retry  (b) Log silently and skip  (c) Move to a fallback "unsorted" folder  (d) Configurable

→ Answer: **(c)** Move to a fallback "unsorted" folder

**Q8.2** If the config file is corrupted (bad JSON), should the app:
(a) Reset to defaults + back up the old file  (b) Show an error and refuse to start  (c) Try to repair the JSON

→ Answer: **(a)** Reset to defaults + back up the old file

**Q8.3** Should the app **log to a file** in addition to the console?
(a) Yes — always  (b) Yes — when `--verbose` is used  (c) No — console only (current)

→ Answer: **(a)** Yes — always

---

### 9 — Security & Privacy

**Q9.1** Should the config file permissions be restricted (e.g. `chmod 600`)?
(a) Yes — only the owner should read it  (b) Not important

→ Answer: **(b)** Not important

**Q9.2** Should destination folders be validated (prevent moving files outside a user-defined allowlist)?
(a) Yes — strict allowlist  (b) No — trust the user's config

→ Answer: **(b)** No — trust the user's config. But if a folder doesn't exist, prompt to create it.

**Q9.3** For distributed builds, should executables be **code-signed**?
(a) Yes — macOS notarisation + Windows Authenticode  (b) Only if distributing publicly  (c) Not needed for now

→ Answer: Do what you must.

---

### 10 — Build, CI & Release

**Q10.1** Should CI also run **linting and type-checking** (e.g. `ruff`, `mypy`)?
(a) Yes — fail the build on lint errors  (b) Yes — report but don't fail  (c) Not needed

→ Answer: Do what you must.

**Q10.2** Should CI test against **multiple Python versions** (3.9, 3.10, 3.11, 3.12)?
(a) Yes — matrix build  (b) No — latest only is fine

→ Answer: **(a)** Yes — matrix build

**Q10.3** Should releases be **automated** (tag → build → GitHub Release with changelog)?
(a) Yes — automatic on tag push  (b) No — manual releases are fine

→ Answer: **(a)** Yes — automatic on tag push

**Q10.4** Should the project be **published to PyPI**?
(a) Yes  (b) Not yet  (c) Never

→ Answer: Unsure

---

### 11 — Future Features (Priority Check)

Rate each feature: **H**igh / **M**edium / **L**ow / **N**o (don't want it).

| # | Feature | Priority |
|---|---------|----------|
| 11.1 | Settings dialog (GUI to edit config without touching JSON) | **H** ✅ |
| 11.2 | Rule management UI (view/edit/delete learned rules) | **H** ✅ |
| 11.3 | Global hotkey to open dashboard (e.g. Ctrl+Shift+S) | **N** ❌ |
| 11.4 | Sorting statistics & streaks ("You sorted 47 files this week!") | **N** ❌ |
| 11.5 | Custom destination sub-folder templates (e.g. `Documents/{year}/{month}/`) | **N** ❌ |
| 11.6 | Multi-step rules (e.g. "if PDF AND > 5 MB → Archive") | — |
| 11.7 | System tray tooltip showing pending count | — |
| 11.8 | "Send to Trash" as a destination option | — |
| 11.9 | Plugin / extension system for custom classifiers | **L** |
| 11.10 | Cloud sync of config (e.g. via a Git repo or Dropbox) | **N** ❌ |
| 11.11 | Sound / system notification on auto-sort | **N** ❌ |
| 11.12 | Dark / light theme toggle | **H** ✅ |
| 11.13 | Autostart on login (OS integration) | **H** ✅ |
| 11.14 | Tray icon badge with pending file count | **H** ✅ |
| 11.15 | Conflict resolution UI (merge / overwrite / rename) | **H** ✅ |

---

### 12 — Anything Else?

**Q12.1** Is there anything about the current behaviour that bothers you?

→ Answer: Haven't tested yet. Do **preventive bugfixing**.

**Q12.2** Any feature from a competing tool you'd like to replicate?

→ Answer: *(none)*

**Q12.3** Any hard constraints (e.g. "must stay under 50 MB", "no internet access")?

→ Answer: No hard constraints.

---

## ✅ How to Use This

1. Fill in every **→ Answer:** line above.
2. Commit this file back to the repo (or paste your answers in a GitHub issue).
3. The next development round will use your answers to prioritise work.

---

## 🧭 Iconic File Filer — Direction Questionnaire (Round 2)

> Now that the core features are built, here are the roadblocks, ideas, and
> questions I need your direction on. Reply inline or via PR comments.

---

### D1. Tkinter Thread Safety

**Context:** tkinter is not thread-safe — creating `tk.Tk()` windows from
background threads works on most systems but can cause random crashes on
macOS and occasionally on Windows. Currently, every popup (sort prompt,
settings, rules, dashboard, conflict) runs in its own background thread.

**Question:** Should I refactor the UI to use a single tkinter main loop
with `root.after()` for cross-thread communication? This is a significant
rewrite of the UI layer but would eliminate all possible tkinter crashes.

→ **Answer:** Keep the current background-thread approach (works reliably on Windows and Linux, the supported platforms). A full `root.after()` refactor is deferred.

**Context:** The config directory changed from `~/.sort-it-now/` to
`~/.iconic-filer/`. Existing users would lose their config, rules,
and history.

**Question:** Should I add an auto-migration that copies files from
`~/.sort-it-now/` to `~/.iconic-filer/` on first run if the old
directory exists? Or start fresh?

(a) Auto-migrate old config on first run
(b) Start fresh — no migration
(c) Prompt the user to choose

→ **Answer:** **(a)** Auto-migrate on first run. If `~/.sort-it-now/config.json` exists and `~/.iconic-filer/config.json` does not, copy the old directory to the new one silently and log it.

---

### D3. Notification Fallback Strategy

**Context:** `plyer` notifications work on most systems but fail silently
on some Linux distros without a notification daemon. Currently we fall
back to logging.

**Question:** When native notifications fail, should we:

(a) Fall back to a small tkinter toast popup (always works, but another window)
(b) Just log it (current behavior)
(c) Show a transient tkinter label that auto-dismisses after 3 seconds

→ **Answer:** **(b)** Just log it. No popup fallback — keep it clean.

---

### D4. Rule Conflict Resolution

**Context:** If an auto-learned extension rule says `.pdf → Documents`
but a pattern rule says `invoice*.pdf → Finances`, which wins? Currently
auto-rules are checked first.

**Question:** What should the priority order be?

(a) Pattern rules first, then auto-learned (more specific wins)
(b) Auto-learned first, then pattern rules (current behavior)
(c) Let the user configure the priority order in settings

→ **Answer:** **(a)** Pattern rules first. Note: auto-learn rules have been removed entirely from the codebase — only pattern rules remain.

---

### D5. Multi-Instance Protection

**Context:** If the user accidentally launches the app twice, both
instances would watch the same folders and race to move files, causing
errors. There's no lock file or single-instance check.

**Question:** Should I add a lock file to prevent multiple instances?

(a) Yes — show a message and exit if already running
(b) No — it's fine for personal use

→ **Answer:** Already implemented! Launching the app twice prompts the user whether to add a new folder to the running instance (merging into one) or start an independent second instance. Multi-instance collaboration is automatic and user-directed.

---

### D6. Folder Monitoring Depth

**Context:** Currently we watch folders non-recursively (top-level only).
If a user drops a file into a subfolder of a monitored folder, it won't
be detected.

**Question:** Should I add an option for recursive monitoring?

(a) Add a per-folder "recursive" toggle in settings
(b) Keep it non-recursive only
(c) Make it a global setting

→ **Answer:** **(b)** Keep it non-recursive only. If a subfolder needs monitoring, the user should add it explicitly via the tray menu or settings.

---

### D7. CLI Mode

**Context:** The `--setup-cli` flag lets users configure folders from the
terminal, but the app itself always needs a display for the tray icon and
prompts.

**Question:** Would a headless/daemon mode be useful? Files would be
sorted purely by rules (no prompts), with results only in the log file.
Useful for servers or running in the background without a desktop.

(a) Yes — add a `--headless` mode
(b) No — GUI-only is fine

→ **Answer:** **(b)** GUI-only. This is a user-facing desktop app, not a server tool.

---

### D8. Statistics & Analytics

**Context:** The dashboard shows basic counts (total, today, this week).
We could track more: most sorted file types, busiest time of day,
most-used destinations, average files per day.

**Question:** How deep should statistics go?

(a) Current level is fine (basic counts)
(b) Add detailed analytics (charts, trends, breakdown by type)
(c) Add a simple weekly summary notification

→ **Answer:** Per-user taxonomy analytics. Statistics should be shaped by how each user organises files — track breakdowns by extension, destination, and time of day. Since taxonomy varies per user, analytics should adapt and highlight the user's own patterns rather than generic counts.

---

### D9. Iconic File Filer Icon & Branding

**Context:** The tray icon is currently a simple programmatically-drawn
blue folder shape. With the rename to Iconic File Filer, we could design
a proper icon.

**Question:** Should I:

(a) Keep the generated icon (simple, works)
(b) Create a more distinctive compass/waypoint-themed icon in code
(c) You'll provide an icon file later

→ **Answer:** **(b)** Compass/waypoint-themed icon drawn in code. The tray icon must display the number of folders being watched by that instance in the tooltip.

---

### D10. Undo Scope

**Context:** Undo currently moves the file back to its original location.
But if the file was renamed during the move (via rename patterns), the
undo restores the renamed file to the original location — it doesn't
undo the rename.

**Question:** Should undo also reverse the rename?

(a) Yes — full undo including name restoration
(b) No — just move it back (current behavior)

→ **Answer:** Ask the user. When a rename occurred during the move, prompt whether to also restore the original filename. Already implemented as `"undo_restore_name": "ask"`.

---

### D11. Future Feature Ideas

**Rate each feature 1–5 (1 = don't care, 5 = must have):**

- [ ] Drag-and-drop sort: drag files onto the tray icon to sort them
- [ ] Keyboard shortcuts in sort prompt (1 = first dest, 2 = second, etc.)
- [ ] Tagging system: add metadata tags to files during sort
- [ ] Search across sorted files (find where something went)
- [ ] Scheduled cleanup reminders ("You have 50 unsorted files")
- [ ] Cloud sync of config/rules (e.g. via Google Drive or Dropbox folder)
- [ ] Plugins/extensions API for custom sort logic
- [ ] File type learning from content (not just extension)
- [ ] Right-click context menu integration ("Sort with Iconic File Filer")
- [ ] Batch rename tool (separate from sort, just for renaming files)

→ **Ratings:**

- Drag-and-drop sort: **4** — If multiple folders are watched, ask the user which folder context to use
- Keyboard shortcuts in sort prompt: **1** — don't care
- Tagging system: **1** — don't care
- Search across sorted files: **(not rated)**
- Undo for accumulated unsorted / unbound items: **maybe** — a log/undo system with unbound items (optimal log-based approach)
- Scheduled cleanup reminders: **M** — yes, can work for files on timeout / still unsorted
- Cloud sync: **N** — no
- Plugins/extensions API: **N** — no
- File type learning from content: **N** — no
- Right-click context menu: **N** — no. The sort prompt already has an editable name field ("rename" button)
- Batch rename tool: **N** — no

---

### D12. Testing Strategy

**Context:** We have 90 unit tests covering config, rules, history,
watcher, classifier, themes, whitelist, duplicate detection, pattern
rules, and more. Missing: integration tests that test the full flow
(file appears → prompt → move → history recorded).

**Question:** Should I invest time in integration/E2E tests?

(a) Yes — add integration tests for the main flow
(b) Unit tests are sufficient for now
(c) Add integration tests but only for the critical path

→ **Answer:** **(c)** Integration tests for the critical path only (file detected → move → history recorded).

---

### D13. Documentation

**Context:** README covers installation and basic usage. There's no
user guide, FAQ, or contributing guide.

**Question:** What documentation should I add?

(a) A user guide / getting started tutorial
(b) A FAQ section in the README
(c) A CONTRIBUTING.md for open-source contributions
(d) All of the above
(e) README is sufficient

→ **Answer:** **(d)** All of the above — go thorough. User guide, FAQ, contributing guide.
