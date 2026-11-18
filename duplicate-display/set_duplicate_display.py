#!/usr/bin/env python3
"""Set the Windows projection topology to Duplicate (equivalent to Win+P).

Designed for managed Windows 10/11 endpoints. Run this script in the
interactive user's session, normally from a user-logon scheduled task or an
Intune user-context script. It requires no third-party Python packages.
"""

from __future__ import annotations

import argparse
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import sys
import time


# SetDisplayConfig flags from WinUser.h.
SDC_APPLY = 0x00000080
SDC_TOPOLOGY_CLONE = 0x00000002

# Win32 status codes most useful to endpoint administrators.
ERROR_SUCCESS = 0
ERROR_ACCESS_DENIED = 5
ERROR_NOT_SUPPORTED = 50
ERROR_INVALID_PARAMETER = 87


def default_log_path() -> Path:
    """Return a machine-wide log path, falling back to the user's temp area."""
    program_data = os.environ.get("ProgramData")
    if program_data:
        return Path(program_data) / "UniversityDisplayMode" / "display_mode.log"
    return Path(os.environ.get("TEMP", ".")) / "UniversityDisplayMode.log"


def configure_logging(log_path: Path, verbose: bool) -> logging.Logger:
    logger = logging.getLogger("set_duplicate_display")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S"
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("Could not open log file %s: %s", log_path, exc)

    return logger


def set_duplicate_mode() -> int:
    """Ask Windows to apply the clone/duplicate topology."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    set_display_config = user32.SetDisplayConfig
    set_display_config.argtypes = [
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    set_display_config.restype = ctypes.c_long

    # This is the Win32 equivalent of DisplaySwitch.exe /clone. Topology flags
    # select Windows' stored/best clone configuration and cannot be combined
    # with flags intended for caller-supplied path/mode arrays.
    flags = SDC_APPLY | SDC_TOPOLOGY_CLONE
    return int(set_display_config(0, None, 0, None, flags))


def explain_status(status: int) -> str:
    known = {
        ERROR_ACCESS_DENIED: "access denied; run in the interactive user's session",
        ERROR_NOT_SUPPORTED: "duplicate mode is not supported by the current display configuration",
        ERROR_INVALID_PARAMETER: "Windows rejected the requested display topology",
    }
    if status in known:
        return known[status]
    try:
        return ctypes.FormatError(status).strip() or f"Win32 status {status}"
    except (ValueError, OSError):
        return f"Win32 status {status}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set Windows projection mode to Duplicate (Win+P → Duplicate)."
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=5,
        help="number of attempts while displays initialize (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="seconds between attempts (default: 3)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=default_log_path(),
        help="log-file path",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    logger = configure_logging(args.log, args.verbose)

    if platform.system() != "Windows":
        logger.error("This script supports Windows 10/11 only.")
        return 2
    if args.retries < 1 or args.delay < 0:
        logger.error("--retries must be at least 1 and --delay cannot be negative.")
        return 2

    for attempt in range(1, args.retries + 1):
        logger.info("Applying Duplicate display mode (attempt %d/%d).", attempt, args.retries)
        status = set_duplicate_mode()
        if status == ERROR_SUCCESS:
            logger.info("Duplicate display mode applied successfully.")
            return 0

        logger.warning("Attempt %d failed: %s (code %d).", attempt, explain_status(status), status)
        if status == ERROR_ACCESS_DENIED:
            break
        if attempt < args.retries:
            time.sleep(args.delay)

    logger.error("Unable to apply Duplicate display mode.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
