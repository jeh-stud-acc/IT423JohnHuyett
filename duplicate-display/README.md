# Classroom Duplicate-Display Fix

A small Python script that puts a Windows computer's displays into **Duplicate** mode, the same setting you'd pick by pressing **Win + P → Duplicate**. I wrote it during my IT support internship at Marymount University and deployed it to classroom computers there in September 2026.

## The problem

University classrooms have a Windows PC connected to both a monitor and a projector. The projector is supposed to mirror the monitor, so the class sees exactly what the instructor sees. On several classroom PCs that setting kept failing at login. That led to repeated complaints about the projector display, and fixing it by hand in each room didn't stick.

## How the script fixes it

- **Sets Duplicate mode directly through Windows.** It calls `SetDisplayConfig`, the Windows API behind the Win + P menu, asking for the "clone" (duplicate) layout. This is the same thing `DisplaySwitch.exe /clone` does.
- **Retries while the displays wake up.** Right after login, a projector may not be ready yet. The script tries up to 5 times, 3 seconds apart (both adjustable), and stops early if Windows denies access, since retrying won't help.
- **Explains failures in plain words.** Common Windows error codes, such as access denied or duplicate mode not supported, are written to the log with a readable explanation.
- **Keeps a log.** It writes to `C:\ProgramData\UniversityDisplayMode\display_mode.log`, rotating at 1 MB with 3 backups, so IT can check what happened on a machine after the fact. If that folder isn't writable, it falls back to the user's temp folder.
- **No extra packages.** It uses only the Python standard library (`ctypes` for the Windows call).

## Usage

```
python set_duplicate_display.py [--retries N] [--delay SECONDS] [--log PATH] [--verbose]
```

| Option | Default | What it does |
| --- | --- | --- |
| `--retries` | 5 | How many times to try while displays initialize |
| `--delay` | 3 | Seconds to wait between tries |
| `--log` | `%ProgramData%\UniversityDisplayMode\display_mode.log` | Where to write the log |
| `--verbose` | off | Log extra detail |

**Exit codes:** `0` success · `1` could not set Duplicate mode · `2` not running on Windows, or bad options.

## Deployment

Display settings belong to the logged-in user, so the script has to run **in that user's session**, not as SYSTEM.

1. **Package it as an .exe** so classroom PCs don't need Python installed, for example with PyInstaller:
   ```
   pyinstaller --onefile --noconsole set_duplicate_display.py
   ```
2. **Run it at every login with Task Scheduler.** Create a task with an **At log on** trigger for any user, set to run as the logged-in user (for example the `Users` group), with the .exe as the action.

The script can also be pushed as a user-context script through Microsoft Intune.

## Requirements

Windows 10 or 11 · Python 3.8+ (only if running the .py directly)
