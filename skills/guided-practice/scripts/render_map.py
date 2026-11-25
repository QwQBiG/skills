"""Render a guided-practice assessment in a terminal or a self-contained web page."""

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys

TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "mastery-map.html"
DEFAULT_LEVELS = [
    ("New", "This idea is new to the learner."),
    ("Recognize", "Recognizes the idea when it appears."),
    ("Follow", "Can follow a worked example."),
    ("Guided", "Can apply the idea with help."),
    ("Independent", "Can choose and apply the method independently."),
    ("Adapt", "Can explain the method and adapt it to an unfamiliar constraint."),
]
LABELS = {
    "lang": "en", "summary": "", "scale_label": "Mastery scale",
    "evidence_label": "Skills and evidence", "current_label": "Current",
    "goal_label": "Goal",
}


def string(value, key):
    if not isinstance(value, str) or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value):
        raise ValueError(f"{key} must be a single line of text")
    return value.strip()


def grade(value, key):
    if value is not None and (type(value) is not int or not 0 <= value <= 5):
        raise ValueError(f"{key} must be an integer from 0 to 5 or null")
    return value


def load_map(raw):
    data = {k: string(raw.get(k, default), k) for k, default in LABELS.items()}
    data["topic"] = string(raw["topic"], "topic")
    data["current"] = grade(raw.get("current"), "current")
    data["goal"] = grade(raw.get("goal", 4), "goal")
    levels = raw.get("levels", [dict(label=s, meaning=m) for s, m in DEFAULT_LEVELS])
    if not isinstance(levels, list) or len(levels) != 6:
        raise ValueError("levels needs six entries in order from 0 through 5")
    data["levels"] = [{k: string(level[k], k) for k in ("label", "meaning")} for level in levels]
    if not isinstance(raw["abilities"], list):
        raise ValueError("abilities must be a list")
    data["abilities"] = []
    for item in raw["abilities"]:
        entry = {k: string(item[k], k) for k in ("name", "status", "evidence", "state")}
        if entry["state"] not in ("guided", "observed", "unassessed"):
            raise ValueError("state must be guided, observed, or unassessed")
        entry["level"] = grade(item.get("level"), "ability level")
        if entry["state"] == "unassessed" and entry["level"] is not None:
            raise ValueError("an unassessed ability must have a null or omitted level")
        data["abilities"].append(entry)
    return data


def web_map(data, standalone):
    esc = html.escape
    selected = next((n for n in (data["current"], data["goal"]) if n is not None), 0)
    steps, meanings, abilities = [], [], []
    for n, level in enumerate(data["levels"]):
        roles, classes = [], ["gp-step"]
        for key in ("current", "goal"):
            if n == data[key]:
                roles.append(esc(data[key + "_label"]))
                classes.append("is-" + key)
        checked = " checked" if n == selected else ""
        steps.append(
            f'<div class="{" ".join(classes)}" style="--step:{n}">'
            f'<input class="gp-choice" type="radio" name="gp-level" id="gp-level-{n}"{checked}>'
            f'<label for="gp-level-{n}"><span class="gp-bar"><span class="gp-n">{n}</span></span>'
            f'<span class="gp-name">{esc(level["label"])}</span><span class="gp-role">{" · ".join(roles)}</span>'
            f'</label></div>'
        )
        meanings.append(f'<p class="gp-meaning" data-level="{n}">{esc(level["meaning"])}</p>')
    for i, a in enumerate(data["abilities"]):
        meter = ""
        if a["level"] is not None:
            score = a["level"]
            marks = "".join('<i class="is-filled"></i>' if n < score else "<i></i>" for n in range(5))
            meter = f'<span class="gp-level-meter" aria-hidden="true">{marks}</span> {score}/5 · '
        opened = " open" if i == 0 else ""
        abilities.append(
            f'<details class="gp-ability" data-state="{a["state"]}"{opened}><summary>'
            f'<span class="gp-mark" aria-hidden="true"></span><span class="gp-ability-name">{esc(a["name"])}</span>'
            f'<span class="gp-status">{meter}{esc(a["status"])}</span></summary><p>{esc(a["evidence"])}</p></details>'
        )
    fields = {key.upper(): esc(data[key]) for key in ("topic", "lang", "summary", "scale_label", "evidence_label")}
    fields.update(STEPS="\n".join(steps), MEANINGS="\n".join(meanings), ABILITIES="\n".join(abilities))
    fragment = re.sub(r"@@([A-Z_]+)@@", lambda m: fields[m[1]], TEMPLATE.read_text(encoding="utf-8"))
    if not standalone:
        return fragment
    return (f'<!doctype html><html lang="{fields["LANG"]}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta name="color-scheme" content="light dark">'
            f'<title>{fields["TOPIC"]}</title></head><body>{fragment}</body></html>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", help="UTF-8 assessment JSON file or - for stdin")
    parser.add_argument("--format", choices=("terminal", "html", "fragment"), default="terminal")
    parser.add_argument("--output", type=Path, help="write output to this file (default: stdout)")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    parser.add_argument("--width", type=int, help="terminal width in columns")
    parser.add_argument("--inspect", type=int, choices=range(6), help="inspect a level in the terminal")
    parser.add_argument("--ascii", action="store_true", help="use ASCII graph marks in the terminal")
    args = parser.parse_args()
    try:
        source = sys.stdin.read() if args.record == "-" else Path(args.record).read_text(encoding="utf-8")
        raw = json.loads(source)
        if not isinstance(raw, dict):
            raise ValueError("expected a JSON object")
        data = load_map(raw)
        if args.format == "terminal":
            from terminal_map import render_terminal

            is_tty = args.output is None and sys.stdout.isatty()
            auto_color = is_tty and os.environ.get("TERM") != "dumb" and not os.environ.get("NO_COLOR")
            color = args.color == "always" or (args.color == "auto" and auto_color)
            width = args.width if args.width is not None else shutil.get_terminal_size((80, 24)).columns
            if width <= 0:
                raise ValueError("width must be positive")
            output = render_terminal(data, width=width, color=color, ascii_only=args.ascii,
                                     inspect_level=args.inspect)
        else:
            output = web_map(data, standalone=args.format == "html")
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (ValueError, KeyError, TypeError, OSError) as e:
        parser.exit(1, f"Cannot render mastery map: {e}\n")


if __name__ == "__main__":
    main()
