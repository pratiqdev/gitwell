"""
Configuration for gitwell: YAML in ``.gitwell`` / ``.gitwell_globals`` and
``gitwell config`` (argparse).

``gitwell.cli`` reads the merged ``config`` mapping after ``loadConfig()``.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import yaml

from gitwell.utils import clamp, pad

DEFAULT_CONFIG: dict[str, Any] = {
    "heading_type": 1,
    "history_type": 1,
    "diff_type": 1,
    "commit_type": 1,
    "final_type": 1,
    "history_length": 10,
    "diff_length": 3,
    "final_length": 1,
    "stage_command": "git add -A",
    "auto_stage": True,
}

CONFIG_DISPLAY_ORDER: tuple[str, ...] = (
    "heading_type",
    "history_type",
    "diff_type",
    "commit_type",
    "final_type",
    "history_length",
    "diff_length",
    "final_length",
    "stage_command",
    "auto_stage",
)

config: dict[str, Any] = {}
loaded_global_config: dict[str, Any] = {}
local_config_file = ".gitwell"
global_config_file = ".gitwell_globals"


def loadConfig(quiet: bool = False) -> None:
    """Merge defaults, ``.gitwell_globals``, and ``.gitwell`` into ``config``."""
    if os.path.exists(global_config_file):
        with open(global_config_file, encoding="utf-8") as file:
            g = yaml.safe_load(file) or {}
        if not isinstance(g, dict):
            g = {}
        loaded_global_config.clear()
        loaded_global_config.update(g)
    else:
        if not quiet:
            print(">> No global config, creating with defaults...")
        with open(global_config_file, "w", encoding="utf-8") as file:
            yaml.safe_dump(DEFAULT_CONFIG, file, sort_keys=False)
        loaded_global_config.clear()
        loaded_global_config.update(dict(DEFAULT_CONFIG))

    config.clear()
    config.update(DEFAULT_CONFIG.copy())
    config.update(loaded_global_config)

    if os.path.exists(local_config_file):
        with open(local_config_file, encoding="utf-8") as file:
            loc = yaml.safe_load(file) or {}
        if isinstance(loc, dict):
            config.update(loc)
    else:
        if not quiet:
            print(">> No local config, using globals")

    _coerce_config_values()


def _coerce_config_values() -> None:
    """Normalize types after YAML merge (e.g. auto_stage as string)."""
    v = config.get("auto_stage", DEFAULT_CONFIG["auto_stage"])
    if isinstance(v, bool):
        config["auto_stage"] = v
    elif isinstance(v, str):
        try:
            config["auto_stage"] = parse_bool_str(v)
        except ValueError:
            config["auto_stage"] = bool(DEFAULT_CONFIG["auto_stage"])
    else:
        config["auto_stage"] = bool(v)

    sc = config.get("stage_command", DEFAULT_CONFIG["stage_command"])
    config["stage_command"] = _normalize_stage_command(sc)


def _normalize_stage_command(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if s.lower() in ("", "none", "null"):
        return ""
    return s


def parse_bool_str(text: str) -> bool:
    sl = text.strip().lower()
    if sl in ("true", "1", "yes", "on"):
        return True
    if sl in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"expected true/false, got {text!r}")


def argparse_bool(value: str) -> bool:
    try:
        return parse_bool_str(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e


def _clamp_type(key: str, val: int) -> int:
    if "length" in key:
        return int(clamp(val, 1, 10))
    return int(clamp(val, 0, 4))


def build_updates_from_namespace(ns: argparse.Namespace) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if ns.heading is not None:
        updates["heading_type"] = _clamp_type("heading_type", ns.heading)
    if ns.history_type is not None:
        updates["history_type"] = _clamp_type("history_type", ns.history_type)
    if ns.diff_type is not None:
        updates["diff_type"] = _clamp_type("diff_type", ns.diff_type)
    if ns.commit_type is not None:
        updates["commit_type"] = _clamp_type("commit_type", ns.commit_type)
    if ns.final_type is not None:
        updates["final_type"] = _clamp_type("final_type", ns.final_type)
    if ns.history_length is not None:
        updates["history_length"] = _clamp_type("history_length", ns.history_length)
    if ns.diff_length is not None:
        updates["diff_length"] = _clamp_type("diff_length", ns.diff_length)
    if ns.final_length is not None:
        updates["final_length"] = _clamp_type("final_length", ns.final_length)
    if ns.stage_command is not None:
        updates["stage_command"] = _normalize_stage_command(ns.stage_command)
    if ns.auto_stage is not None:
        updates["auto_stage"] = bool(ns.auto_stage)
    return updates


def persist_local(updates: dict[str, Any]) -> None:
    if not updates:
        return
    file_data: dict[str, Any] = {}
    if os.path.exists(local_config_file):
        with open(local_config_file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if isinstance(raw, dict):
            file_data.update(raw)
    file_data.update(updates)
    with open(local_config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(file_data, f, sort_keys=False)


def persist_global(updates: dict[str, Any]) -> None:
    if not updates:
        return
    file_data: dict[str, Any] = {}
    if os.path.exists(global_config_file):
        with open(global_config_file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if isinstance(raw, dict):
            file_data.update(raw)
    merged = DEFAULT_CONFIG.copy()
    merged.update(file_data)
    merged.update(updates)
    with open(global_config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, sort_keys=False)


def apply_config_cli(ns: argparse.Namespace) -> None:
    """Parse ``gitwell config`` namespace, write YAML, reload, print banner + values."""
    updates = build_updates_from_namespace(ns)
    if updates:
        if ns.global_:
            persist_global(updates)
        else:
            persist_local(updates)
    loadConfig(quiet=True)

    if ns.global_:
        print("GLOBAL GITWELL CONFIG")
    else:
        print("LOCAL GITWELL CONFIG")

    for key in CONFIG_DISPLAY_ORDER:
        if key in config:
            print(f">> {pad(key, 18)} {config[key]}")


def build_config_argument_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gitwell config", add_help=False)
    p.add_argument("--help", action="help", help="show this help message and exit")
    p.add_argument("-g", "--global", dest="global_", action="store_true", help="write global config file")
    p.add_argument("--heading", "-h", type=int, metavar="N", help="heading_type (0–4)")
    p.add_argument("--history-type", "-y", type=int, metavar="N", help="history_type (0–4)")
    p.add_argument("--diff-type", "-d", type=int, metavar="N", help="diff_type (0–4)")
    p.add_argument("--commit-type", "-c", type=int, metavar="N", help="commit_type (0–4)")
    p.add_argument("--final-type", "-f", type=int, metavar="N", help="final_type (0–4)")
    p.add_argument("--history-length", "-L", type=int, metavar="N", help="history_length (1–10)")
    p.add_argument("--diff-length", "-D", type=int, metavar="N", help="diff_length (1–10)")
    p.add_argument("--final-length", "-N", type=int, metavar="N", help="final_length (1–10)")
    p.add_argument("--stage-command", "-s", metavar="CMD", help="stage_command shell string (empty to disable)")
    p.add_argument("--auto-stage", "-a", type=argparse_bool, metavar="BOOL", help="auto_stage true|false")
    return p


def main() -> None:
    print(
        "The console script `gitwell-config` was removed. Use:\n"
        "  gitwell config ...\n"
        "  python -m gitwell config ...",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
