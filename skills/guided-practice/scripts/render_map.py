"""Render a guided-practice assessment in a terminal or a self-contained web page."""

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

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
    "goal_label": "Goal", "focus_label": "Focus", "check_label": "Next check",
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
        entry["focus"] = item.get("focus", False)
        if type(entry["focus"]) is not bool:
            raise ValueError("ability focus must be true or false")
        entry["next_check"] = string(item.get("next_check", ""), "next_check")
        if entry["state"] == "unassessed" and entry["level"] is not None:
            raise ValueError("an unassessed ability must have a null or omitted level")
        data["abilities"].append(entry)
    if sum(a["focus"] for a in data["abilities"]) > 1:
        raise ValueError("select one focus at a time")
    return data


def web_map(data, standalone):
    page = TEMPLATE.read_text(encoding="utf-8")
    # Drop source indentation before expanding repeated rows or inserting learner text.
    page = re.sub(r"\n[ \t]+", "\n", page)
    layout = page.split('<template id="gp-layout">', 1)[1].split("</template>", 1)[0]
    slots = re.compile(r"{{([#^])(\w+)}}([\s\S]*?){{/\2}}|{{(\w+)}}")

    def expand(markup, context):
        def fill(match):
            kind, key, content, field = match.groups()
            if field:
                value = context.get(field)
                return "" if value is None else html.escape(str(value))
            value = context.get(key)
            if isinstance(value, list):
                return "".join(expand(content, {**context, **item}) for item in value)
            present = value is not None and value is not False and value != ""
            return expand(content, context) if present == (kind == "#") else ""

        return slots.sub(fill, markup)

    goal = data["goal"]
    report = expand(layout, {**data, "goal_name": "" if goal is None else data["levels"][goal]["label"]})
    # Exports contain the completed report and native disclosures, including in script-free hosts.
    prefix = page.split('<article id="gp-report"', 1)[0]
    if standalone:
        prefix = prefix.replace('<html lang="en"', f'<html lang="{html.escape(data["lang"])}"', 1)
        prefix = prefix.replace("<title>Mastery map</title>", f'<title>{html.escape(data["topic"])}</title>', 1)
    else:
        prefix = prefix[prefix.index("<style>"):]
    shortcuts = page[page.index('<script id="gp-keys">'):]
    return (f'{prefix}<article id="gp-report" aria-labelledby="gp-topic" lang="{html.escape(data["lang"])}">'
            f'{report}</article>\n</section>\n{shortcuts}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", help="UTF-8 assessment JSON file or - for stdin")
    parser.add_argument("--format", choices=("terminal", "command", "html", "fragment"), default="terminal")
    parser.add_argument("--output", type=Path, help="write output to this file (default: stdout)")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    parser.add_argument("--width", type=int, help="terminal width in columns")
    parser.add_argument("--once", action="store_true", help="print the terminal view and return to the prompt")
    parser.add_argument("--inspect", type=int, choices=range(6), help="inspect a level in the terminal")
    parser.add_argument("--detail", metavar="ABILITY", help="show the evidence for a named ability in the terminal")
    parser.add_argument("--ascii", action="store_true", help="use ASCII graph marks in the terminal")
    args = parser.parse_args()
    try:
        source = sys.stdin.read() if args.record == "-" else Path(args.record).read_text(encoding="utf-8")
        raw = json.loads(source)
        if not isinstance(raw, dict):
            raise ValueError("expected a JSON object")
        data = load_map(raw)
        is_tty = args.output is None and sys.stdout.isatty()
        interactive = (args.format == "terminal" and is_tty and sys.stdin.isatty()
                       and os.name == "posix" and os.environ.get("TERM") != "dumb"
                       and not args.once and args.detail is None and args.inspect is None)
        if args.format == "command" or interactive:
            from terminal_entry import terminal_entry

            output = terminal_entry(data, width=args.width, color_mode=args.color,
                                    ascii_only=args.ascii, inspect_level=args.inspect, detail=args.detail)
            if interactive:
                with tempfile.TemporaryDirectory() as directory:
                    entry = Path(directory) / "mastery.sh"
                    entry.write_text(output, encoding="utf-8")
                    try:
                        return subprocess.call(["/bin/sh", str(entry)])
                    except KeyboardInterrupt:
                        return 130
        elif args.format == "terminal":
            from terminal_map import render_terminal

            auto_color = is_tty and os.environ.get("TERM") != "dumb" and not os.environ.get("NO_COLOR")
            color = args.color == "always" or (args.color == "auto" and auto_color)
            width = args.width if args.width is not None else shutil.get_terminal_size((80, 24)).columns
            if width <= 0:
                raise ValueError("width must be positive")
            output = render_terminal(data, width=width, color=color, ascii_only=args.ascii,
                                     inspect_level=args.inspect, detail=args.detail)
        else:
            output = web_map(data, standalone=args.format == "html")
        if args.output and args.format == "command":
            # A learner can keep a viewer open while the next assessment replaces it.
            destination = args.output.resolve()
            with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
                entry = Path(directory) / "mastery.command"
                entry.write_text(output, encoding="utf-8")
                mode = destination.stat().st_mode if destination.exists() else 0o600
                entry.chmod(stat.S_IMODE(mode) | stat.S_IXUSR)
                entry.replace(destination)
        elif args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (ValueError, KeyError, TypeError, OSError) as e:
        parser.exit(1, f"Cannot render mastery map: {e}\n")


if __name__ == "__main__":
    sys.exit(main())
