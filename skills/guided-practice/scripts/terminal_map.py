"""Draw a mastery map for a terminal using only the Python standard library."""

import unicodedata


def _regional(char):
    return "\U0001f1e6" <= char <= "\U0001f1ff"


def _clusters(text):
    """Keep common emoji sequences and combining marks together during wrapping."""
    cluster = ""
    for char in text:
        extends = (
            unicodedata.category(char).startswith("M")
            or char == "\u200d"
            or "\U0001f3fb" <= char <= "\U0001f3ff"
            or "\U000e0020" <= char <= "\U000e007f"
            or cluster.endswith("\u200d")
            or (len(cluster) == 1 and _regional(cluster) and _regional(char))
        )
        if cluster and not extends:
            yield cluster
            cluster = ""
        cluster += char
    if cluster:
        yield cluster


def _cell_width(cluster):
    if ("\ufe0f" in cluster or "\u20e3" in cluster
            or (len(cluster) == 2 and all(_regional(c) for c in cluster))):
        return 2
    return max(
        (2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
         for c in cluster if unicodedata.category(c)[0] not in ("C", "M")),
        default=0,
    )


def _width(text):
    return sum(_cell_width(cluster) for cluster in _clusters(text))


def _wrap(text, width):
    """Prefer whole words, but allow long words and unspaced scripts to wrap."""
    line = ""
    used = 0
    for word in text.split():
        size = _width(word)
        if line and used + 1 + size <= width:
            line += " " + word
            used += 1 + size
            continue
        if line:
            yield line
        if size <= width:
            line, used = word, size
            continue
        line, used = "", 0
        for cluster in _clusters(word):
            size = _cell_width(cluster)
            if line and used + size > width:
                yield line
                line, used = "", 0
            line += cluster
            used += size
    if line:
        yield line


def _center(text, width):
    free = max(0, width - _width(text))
    return " " * (free // 2) + text + " " * (free - free // 2)


def _staircase(width, current, goal, marks, fills, paint):
    gap = "  " if width >= 54 else " "
    cell = min(12, (width - 5 * len(gap)) // 6)
    margin = " " * max(0, (width - 6 * cell - 5 * len(gap)) // 2)
    columns = []
    for level in range(6):
        is_current = level == current
        is_goal = level == goal
        reached = current is not None and level < current
        if is_current and is_goal:
            pattern, color = fills[1] + fills[2], "1;35"
        elif is_current:
            pattern, color = fills[1], "1;32"
        elif is_goal:
            pattern, color = fills[2], "1;35"
        elif reached:
            pattern, color = fills[0], "36"
        else:
            pattern, color = fills[3], "34"
        bar = (pattern * cell)[:cell]
        marker = (marks[0] if is_current else "") + str(level) + (marks[1] if is_goal else "")
        columns.append((paint(bar, color), paint(_center(marker, cell), color)))

    for height in reversed(range(6)):
        parts = [bar if level >= height else " " * cell
                 for level, (bar, _) in enumerate(columns)]
        yield margin + gap.join(parts)
    yield margin + gap.join(label for _, label in columns)


def render_terminal(data, *, width, color, ascii_only=False, inspect_level=None):
    """Return the validated map as terminal text, including its final newline."""
    width = max(1, min(width, 100))
    marks = ("@", "^") if ascii_only else ("●", "◆")
    fills = ("=", "#", "/", ".") if ascii_only else ("▓", "█", "▒", "░")
    rule = "-" if ascii_only else "━"
    joiner = " | " if ascii_only else "  ·  "
    unknown = "-" if ascii_only else "—"
    lines = []

    def paint(text, sgr):
        return f"\x1b[{sgr}m{text}\x1b[0m" if color else text

    def paragraph(text, *, prefix="", sgr=None):
        indent = min(_width(prefix), max(0, width - 2))
        if indent != _width(prefix):
            prefix = ""
            indent = 0
        for i, line in enumerate(_wrap(text, width - indent)):
            line = (prefix if i == 0 else " " * indent) + line
            lines.append(paint(line, sgr) if sgr else line)

    paragraph(data["topic"], sgr="1;36")
    lines.append(paint(rule * width, "36"))
    if data.get("summary"):
        paragraph(data["summary"])
    lines.append("")
    paragraph(data["scale_label"], sgr="1")
    current, goal = data["current"], data["goal"]
    if width >= 23:
        lines.extend(_staircase(width, current, goal, marks, fills, paint))
    else:
        # On a very narrow terminal rotate the staircase so its labels still fit.
        for level in range(6):
            marker = (marks[0] if level == current else "") + (marks[1] if level == goal else "")
            paragraph(f"{level}{marker} {fills[1] * (level + 1)}", sgr="36")
    lines.append("")
    for marker, key, value, sgr in (
        (marks[0], "current_label", current, "1;32"),
        (marks[1], "goal_label", goal, "1;35"),
    ):
        value_text = unknown if value is None else f"{value} {data['levels'][value]['label']}"
        paragraph(f"{data[key]}  {value_text}", prefix=marker + " ", sgr=sgr)

    selected = next((n for n in (inspect_level, current, goal) if n is not None), None)
    if selected is not None:
        item = data["levels"][selected]
        paragraph(f"{selected} {item['label']}{joiner}{item['meaning']}")

    lines.append("")
    paragraph(data["evidence_label"], sgr="1")
    state_styles = {
        "guided": ("~" if ascii_only else "◐", "1;33"),
        "observed": ("*" if ascii_only else "●", "1;36"),
        "unassessed": ("o" if ascii_only else "○", "1"),
    }
    full, empty = ("#", ".") if ascii_only else ("■", "□")
    for i, ability in enumerate(data["abilities"]):
        if i:
            lines.append("")
        symbol, sgr = state_styles[ability["state"]]
        paragraph(ability["name"], prefix=symbol + " ", sgr=sgr)
        level = ability.get("level")
        status = ability["status"]
        if level is not None:
            meter = full * level + empty * (5 - level)
            status = f"{meter} {level}/5{joiner}{status}"
        paragraph(status, prefix="  ", sgr=sgr)
        paragraph(ability["evidence"], prefix="  ")
    return "\n".join(lines) + "\n"
