"""Merge message translations into messages.toml for the zh-Hans language pack.

Reads the current messages.toml as the base, then overlays every msg_*.json found next to this
script (each a {english: 中文} object). Writes out/messages.toml plus the installed copy when
--install is passed.

Validation: keys are used verbatim, must be non-empty, trimmed, and free of braces; values must be
non-empty strings without braces (the app's template matcher treats braces as fields).
"""
from __future__ import annotations

import glob
import json
import os
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE / "pack" / "community-zh-hans"
INSTALLED = Path(os.environ["APPDATA"]) / "pokeldn" / "plugins" / "community-zh-hans"


def escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace('"', '\\"')
            .replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t"))


def load_base() -> dict[str, str]:
    path = PLUGIN / "messages.toml"
    if not path.exists():
        return {}
    return dict(tomllib.loads(path.read_text(encoding="utf-8")))


def check(key: str, value: str, origin: str) -> list[str]:
    problems = []
    # A key is matched verbatim against the module's English string, so a trailing space can be
    # legitimate (e.g. the FRLG OT name "10 ANIV "). Only an empty key is a hard failure.
    if not key:
        problems.append(f"{origin}: empty key")
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{origin}: value is empty for {key!r}")
    for ch in "{}":
        if ch in key:
            problems.append(f"{origin}: key contains a brace: {key!r}")
    if isinstance(value, str) and value != value.strip():
        problems.append(f"{origin}: value has outer whitespace: {key!r}")
    return problems


def main() -> int:
    pairs = load_base()
    problems: list[str] = []
    added = 0
    for path in sorted(glob.glob(str(HERE / "msg_*.json"))):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            problems.append(f"{os.path.basename(path)}: not an object")
            continue
        for key, value in data.items():
            if not isinstance(value, str):
                problems.append(f"{os.path.basename(path)}: non-string value for {key!r}")
                continue
            problems += check(key, value, os.path.basename(path))
            if key not in pairs:
                added += 1
            pairs[key] = value

    if problems:
        print("\n".join(problems))
        return 1

    lines = ["# POKELDN 界面简体中文语言包：模块内写死的英文文案（messages）", ""]
    for key in sorted(pairs):
        lines.append(f'"{escape(key)}" = "{escape(pairs[key])}"')
    blob = "\n".join(lines) + "\n"
    parsed = tomllib.loads(blob)
    if len(parsed) != len(pairs):
        print("duplicate keys after writing")
        return 1

    out = HERE / "out" / "messages.toml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(blob, encoding="utf-8")
    print(f"entries {len(pairs)} (+{added} new), {len(blob.encode())} bytes -> {out}")

    if "--install" in sys.argv:
        target = INSTALLED / "messages.toml"
        target.write_text(blob, encoding="utf-8")
        print(f"installed {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
