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
        # Unspaced CJK text can start in the unused cells of the preceding line.
        if size <= width and not (line and any(unicodedata.east_asian_width(c) in ("W", "F") for c in word)):
            if line:
                yield line
            line, used = word, size
            continue
        if line:
            line += " "
            used += 1
        for cluster in _clusters(word):
            size = _cell_width(cluster)
            if line and used + size > width:
                yield line.rstrip()
                line, used = "", 0
            line += cluster
            used += size
    if line:
        yield line


def terminal_sections(data, *, width, color, ascii_only=False, inspect_level=None):
    """Return the header, (normal, selected, evidence, focus cue) rows, and footer."""
    width = max(1, min(width, 100))
    joiner = " | " if ascii_only else " · "
    cursor, focus_mark, rail = (">", "*", "|") if ascii_only else ("▸", "✦", "│")
    filled, empty = ("=", ".") if ascii_only else ("▮", "▯")
    rose = "35;38;5;211"
    marks = {
        "observed": "+" if ascii_only else "◇",
        "guided": "~",
        "unassessed": "-" if ascii_only else "—",
    }

    def paint(text, sgr):
        return f"\x1b[{sgr}m{text}\x1b[0m" if color and sgr and text else text

    def paragraph(text, *, indent=0, sgr=None):
        indent = min(indent, max(0, width - 2))
        return "".join(" " * indent + paint(line, sgr) + "\n" for line in _wrap(text, width - indent))

    def caption(key):
        level = data[key]
        if level is None:
            return ""
        return f"{data[key + '_label']} {level}/5 {data['levels'][level]['label']}".strip()

    abilities = data["abilities"]
    longest = max((_width(a["name"]) for a in abilities), default=0)
    # Leave a cell between the keyboard cursor and the teaching focus.
    margin = 4
    column_gap = 1 if width < 36 else 2
    column = min(longest, max(0, width - margin - column_gap - 10))

    title, goal = data["topic"], caption("goal")
    title_width = _width(title)
    room = width - title_width - _width(goal)
    flower = ""
    if title and room >= (5 if goal else 2):
        flower = paint("*" if ascii_only else "✿", rose) + " "
        title_width += 2
        room -= 2
    if title and goal and room >= 3:
        gap = min(room, max(3, margin + column_gap + column - title_width))
        header = flower + paint(title, "1;35") + " " * gap + goal + "\n"
    else:
        header = flower + paragraph(title, sgr="1;35") + paragraph(goal)
    if header and abilities:
        header += "\n"

    def sections_for(ability):
        name, level = ability["name"], ability.get("level")
        focus, check = ability.get("focus"), ability.get("next_check")
        if level is None:
            reading = marks[ability["state"]]
            value = ability["status"]
            colored_value = value
        else:
            reading = f"{level}/5"
            past = filled * level
            remaining = empty * (5 - level)
            value = past + remaining
            colored_value = paint(past, rose) + remaining

        if focus and not check and data["focus_label"]:
            label = f"  [{data['focus_label']}]"
            value += label
            colored_value += label
        name_width = _width(name)
        gap = column_gap + max(0, column - name_width)
        room = width - margin - name_width - gap - _width(reading) - _width(value)
        padding = " " * max(1, min(5 - _width(reading), room)) if value else ""
        result = reading + padding + colored_value
        result_width = _width(reading + padding + value)
        gap = min(gap, max(column_gap, width - margin - name_width - result_width))

        def row(selected):
            cursor_cell = paint(cursor, rose) if selected else " "
            focus_cell = focus_mark if focus else " "
            gutter = cursor_cell + " " + focus_cell + " "
            name_style = "1" if selected else None
            if margin + name_width + gap + result_width <= width:
                return gutter + paint(name, name_style) + " " * gap + result + "\n"

            if width >= margin + 2:
                name_block = paragraph(name, indent=margin, sgr=name_style)
                name_block = gutter + name_block[margin:]
            else:
                markers = " ".join(mark for mark, visible in ((cursor, selected), (focus_mark, focus)) if visible)
                name_block = paragraph(markers) + paragraph(name, sgr=name_style)
            if margin + result_width <= width:
                return name_block + " " * margin + result + "\n"
            return name_block + paragraph(reading + "  " + value, indent=margin)

        cue = paragraph(data["check_label"] + joiner + check, indent=margin) if check else ""
        evidence = ability["evidence"]
        if level is not None and ability["status"]:
            evidence = joiner.join(filter(None, (ability["status"], evidence)))
        # The evidence guide begins at the name column, one level below its row.
        if width >= margin + 4:
            prefix = " " * margin + paint(rail, rose) + " "
            detail = "".join(prefix + line + "\n" for line in _wrap(evidence, width - margin - 2))
        else:
            detail = paragraph(evidence)
        if not focus:
            detail += cue
        focus_cue = cue if focus else ""
        return row(False), row(True), detail, focus_cue

    footer = paragraph(caption("current"))
    if inspect_level is not None:
        item = data["levels"][inspect_level]
        footer += paragraph(f"{inspect_level}/5 {item['label']}{joiner}{item['meaning']}")
    return header, [sections_for(ability) for ability in abilities], footer


def render_terminal(data, *, width, color, ascii_only=False, inspect_level=None, detail=None):
    """Return the compact noninteractive map, optionally expanding one ability."""
    selected = None
    if detail is not None:
        selected = next((i for i, a in enumerate(data["abilities"]) if a["name"] == detail), None)
        if selected is None:
            raise ValueError(f"unknown ability {detail!r}")
    header, rows, footer = terminal_sections(
        data, width=width, color=color, ascii_only=ascii_only, inspect_level=inspect_level
    )
    body = "".join((highlight + evidence if i == selected else normal) + cue
                   for i, (normal, highlight, evidence, cue) in enumerate(rows))
    return header + body + footer or "\n"
