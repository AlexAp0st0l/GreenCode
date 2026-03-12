"""
greencode/cli/measure.py
━━━━━━━━━━━━━━━━━━━━━━━
Core CO₂ measurement engine.
Wraps CodeCarbon and adds project-level tracking, history, and grading.
"""

from __future__ import annotations

import json
import os
import subprocess
import datetime
from pathlib import Path
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────────────

HISTORY_DIR = Path(".greencode")
HISTORY_FILE = HISTORY_DIR / "history.json"
LATEST_FILE  = HISTORY_DIR / "latest.json"
BADGE_FILE   = HISTORY_DIR / "badge.svg"

# Grade thresholds (grams CO₂)
GRADE_GREEN  = 10.0   # 🌿 excellent
GRADE_YELLOW = 50.0   # 🌡 moderate
# above 50g   → 🔥 red

GRADE_LABELS = {
    "green":  {"emoji": "🌿", "label": "low carbon",    "color": "#22C55E"},
    "yellow": {"emoji": "🌡", "label": "moderate",       "color": "#EAB308"},
    "red":    {"emoji": "🔥", "label": "high carbon",    "color": "#EF4444"},
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _git_sha() -> str:
    """Returns short git SHA or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _project_name(path: str) -> str:
    return Path(path).resolve().name


def grade(grams: float) -> str:
    if grams < GRADE_GREEN:
        return "green"
    if grams < GRADE_YELLOW:
        return "yellow"
    return "red"


# ── Main measurement ─────────────────────────────────────────────────────────

def measure(
    path: str = ".",
    command: Optional[list[str]] = None,
    duration: int = 120,
    country_iso: str = "DEU",   # default: Germany (EU average)
    save: bool = True,
) -> dict:
    """
    Measure CO₂ emissions while running tests or a command.

    Args:
        path:        Project directory to measure
        command:     Custom command to run. Default: pytest
        duration:    Max timeout seconds
        country_iso: ISO country code for emission factors
        save:        Whether to save result to history

    Returns:
        dict with kg_co2, grams_co2, grade, label, timestamp, commit, branch
    """
    try:
        from codecarbon import EmissionsTracker
        _codecarbon_available = True
    except ImportError:
        _codecarbon_available = False

    HISTORY_DIR.mkdir(exist_ok=True)

    cmd = command or ["python", "-m", "pytest", path, "--tb=no", "-q", "--no-header"]

    # ── Real measurement ──────────────────────────────────────────────────
    if _codecarbon_available:
        tracker = EmissionsTracker(
            project_name=_project_name(path),
            output_dir=str(HISTORY_DIR),
            country_iso_code=country_iso,
            measure_power_secs=1,
            log_level="error",
            save_to_file=False,
        )
        tracker.start()
        try:
            subprocess.run(cmd, capture_output=True, timeout=duration)
        except subprocess.TimeoutExpired:
            pass
        finally:
            emissions_kg = tracker.stop() or 0.0
    else:
        # ── Estimation fallback (no CodeCarbon installed) ─────────────────
        # Rough estimate: 0.1 kWh per minute of CPU × local emission factor
        emissions_kg = _estimate_without_codecarbon(cmd, duration, country_iso)

    grams = round(emissions_kg * 1000, 4)
    g = grade(grams)
    meta = GRADE_LABELS[g]

    result = {
        "kg_co2":      round(emissions_kg, 8),
        "grams_co2":   grams,
        "grade":       g,
        "emoji":       meta["emoji"],
        "label":       meta["label"],
        "color":       meta["color"],
        "timestamp":   datetime.datetime.utcnow().isoformat() + "Z",
        "commit":      _git_sha(),
        "branch":      _git_branch(),
        "project":     _project_name(path),
        "country_iso": country_iso,
        "command":     " ".join(cmd),
        "note":        "estimated" if not _codecarbon_available else "measured",
    }

    if save:
        _save(result)

    return result


def _estimate_without_codecarbon(
    cmd: list[str], duration: int, country_iso: str
) -> float:
    """
    Rough estimation when CodeCarbon is not installed.
    Based on: avg laptop TDP ~15W, emission factor ~0.4 kg CO₂/kWh.
    """
    EMISSION_FACTORS = {          # kg CO₂ per kWh
        "DEU": 0.366, "USA": 0.386, "GBR": 0.233,
        "FRA": 0.056, "CHN": 0.555, "RUS": 0.322,
    }
    factor = EMISSION_FACTORS.get(country_iso, 0.4)

    start = datetime.datetime.utcnow()
    try:
        subprocess.run(cmd, capture_output=True, timeout=duration)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    elapsed_hours = (datetime.datetime.utcnow() - start).total_seconds() / 3600

    tdp_kw = 0.015   # 15W typical laptop
    kwh = tdp_kw * elapsed_hours
    return kwh * factor


# ── History ───────────────────────────────────────────────────────────────────

def _save(result: dict) -> None:
    HISTORY_FILE.parent.mkdir(exist_ok=True)

    # latest
    LATEST_FILE.write_text(json.dumps(result, indent=2))

    # history list (keep last 100)
    history = _load_history()
    history.append(result)
    history = history[-100:]
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def _load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except json.JSONDecodeError:
            return []
    return []


def load_latest() -> Optional[dict]:
    """Load the most recent measurement from disk."""
    if LATEST_FILE.exists():
        try:
            return json.loads(LATEST_FILE.read_text())
        except json.JSONDecodeError:
            return None
    return None


def load_history() -> list[dict]:
    return _load_history()


def compare(current: dict, previous: Optional[dict]) -> dict:
    """
    Compare two measurements and return delta info.
    Returns dict with delta_grams, delta_pct, direction.
    """
    if not previous:
        return {"delta_grams": 0.0, "delta_pct": 0.0, "direction": "first"}

    delta = current["grams_co2"] - previous["grams_co2"]
    pct = (delta / previous["grams_co2"] * 100) if previous["grams_co2"] > 0 else 0.0

    return {
        "delta_grams": round(delta, 4),
        "delta_pct":   round(pct, 2),
        "direction":   "up" if delta > 0 else "down" if delta < 0 else "same",
        "prev_grade":  previous.get("grade"),
        "curr_grade":  current.get("grade"),
    }
