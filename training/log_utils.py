"""
Shared logging utility for training scripts.

Creates a time/date/run-stamped directory under:
    <repo-root>/logs/training/<YYYY-MM-DD>/<HHmmss>_<symbol>_<timeframe>[_<label>]/

Two log handlers are configured:
    StreamHandler(sys.stdout)    — console (INFO and above)
    FileHandler(run_dir/run.log) — file (DEBUG and above)

Structured JSON events are written to run_dir/run.jsonl via write_event().
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root: training/log_utils.py → training/ → repo-root/
_REPO_ROOT = Path(__file__).resolve().parent.parent
_TRAINING_LOGS_ROOT = _REPO_ROOT / "logs" / "training"

_LOG_FMT = logging.Formatter(
    fmt="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)


def _utc_converter(*_):
    return datetime.now(timezone.utc).timetuple()


_LOG_FMT.converter = _utc_converter  # type: ignore[method-assign]


def setup_run_logger(
    symbol: str,
    timeframe: str,
    label: str = "",
    output_dir: "Path | str | None" = None,
    *,
    log_level_console: int = logging.INFO,
    log_level_file: int = logging.DEBUG,
) -> "tuple[logging.Logger, Path]":
    """
    Configure a logger for one training run and return it together with the run directory.

    Parameters
    ----------
    symbol           : instrument symbol, e.g. "EURUSD"
    timeframe        : bar timeframe, e.g. "H4"
    label            : optional label appended to the auto-generated dir name, e.g. "exp-001"
    output_dir       : if provided, use this path as the run directory instead of
                       auto-generating under logs/training/
    log_level_console: logging level for stdout handler (default INFO)
    log_level_file   : logging level for file handler (default DEBUG)

    Returns
    -------
    logger  : configured logging.Logger
    run_dir : Path to the run directory (write all artefacts here)
    """
    if output_dir is not None:
        run_dir = Path(output_dir).resolve()
    else:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H%M%S")
        dir_name = f"{time_str}_{symbol}_{timeframe}"
        if label:
            dir_name = f"{dir_name}_{label}"
        run_dir = _TRAINING_LOGS_ROOT / date_str / dir_name

    run_dir.mkdir(parents=True, exist_ok=True)

    # Use a unique logger name so multiple runs in the same process don't collide.
    now_tag = datetime.now(timezone.utc).strftime("%H%M%S%f")
    logger = logging.getLogger(f"training.{symbol}.{timeframe}.{now_tag}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Remove any handlers from a previous call with the same name (shouldn't happen,
    # but guards against accidental re-configuration in tests).
    logger.handlers.clear()

    console_h = logging.StreamHandler(sys.stdout)
    console_h.setLevel(log_level_console)
    console_h.setFormatter(_LOG_FMT)
    logger.addHandler(console_h)

    file_h = logging.FileHandler(run_dir / "run.log", encoding="utf-8")
    file_h.setLevel(log_level_file)
    file_h.setFormatter(_LOG_FMT)
    logger.addHandler(file_h)

    return logger, run_dir


def write_event(run_dir: Path, event: str, **fields) -> None:
    """Append one structured JSON event line to run_dir/run.jsonl."""
    record = {
        "timestampUtc": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    jsonl_path = run_dir / "run.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
