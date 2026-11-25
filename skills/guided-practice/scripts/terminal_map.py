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


def render_terminal(data, *, width, color, ascii_only=False, inspect_level=None, detail=None):
    """Return the validated map as terminal text, including its final newline."""
    width = max(1, min(width, 100))
    joiner = " | " if ascii_only else " · "
    lines = []

    def paint(text, sgr):
        return f"\x1b[{sgr}m{text}\x1b[0m" if color else text

    def paragraph(text, *, indent=0, sgr=None):
        indent = min(indent, max(0, width - 2))
        for line in _wrap(text, width - indent):
            lines.append(" " * indent + (paint(line, sgr) if sgr else line))

    paragraph(data["topic"], sgr="1;36")
    abilities = data["abilities"]
    if detail is None:
        expanded = next((a for a in abilities if a.get("focus") and a.get("next_check")), None)
    else:
        expanded = next((a for a in abilities if a["name"] == detail), None)
        if expanded is None:
            raise ValueError(f"unknown ability {detail!r}")

    column = min(20, width // 3, max((_width(a["name"]) for a in abilities), default=0))
    colors = {"guided": "33", "observed": "36", "unassessed": "39"}
    full, empty = ("#", ".") if ascii_only else ("■", "□")
    for ability in abilities:
        name = ability["name"]
        status = ability["status"]
        level = ability.get("level")
        if level is not None:
            status = f"{full * level}{empty * (5 - level)} {level}/5"
        focus = f" [{data['focus_label']}]" if ability.get("focus") else ""
        gap = " " * (2 + max(0, column - _width(name)))
        sgr = colors[ability["state"]]
        if _width(name + gap + status + focus) <= width:
            lines.append(name + gap + paint(status + focus, sgr))
        else:
            paragraph(f"{name} {status}{focus}", sgr=sgr)
        if ability is expanded:
            if detail is not None:
                if level is not None and ability["status"]:
                    paragraph(ability["status"], indent=2)
                paragraph(ability["evidence"], indent=2)
            if ability.get("next_check"):
                paragraph(f"{data['check_label']}{joiner}{ability['next_check']}", indent=2)

    context = []
    for key in ("goal", "current"):
        level = data[key]
        if level is not None:
            context.append(f"{data[key + '_label']} {level}/5 {data['levels'][level]['label']}")
    if context:
        paragraph(joiner.join(context))
    if inspect_level is not None:
        item = data["levels"][inspect_level]
        paragraph(f"{inspect_level}/5 {item['label']}{joiner}{item['meaning']}")
    return "\n".join(lines) + "\n"
