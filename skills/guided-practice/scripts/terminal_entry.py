"""Export the keyboard-driven mastery viewer as a standalone POSIX shell script."""

import re
import shlex

from terminal_map import _width, terminal_sections


def _print_view(view, styles):
    # The fixed format keeps record text literal, including quotes, %, and backslashes.
    pieces = []
    for part in re.split(r"(\x1b\[[0-9;]+m)", view):
        if part.startswith("\x1b["):
            style = styles.setdefault(part, f"s{len(styles)}")
            pieces.append(f'"${style}"')
        elif part:
            pieces.append(shlex.quote(part))
    return "printf '%s' " + " ".join(pieces)


def _layouts(data, widths, **options):
    # Store each distinct fragment once. Each width's layout holds just its indices.
    fragments = {"": 0}

    def index(view):
        return str(fragments.setdefault(view, len(fragments)))

    layouts = []
    for columns in widths:
        header, rows, footer = terminal_sections(data, width=columns, **options)
        if not header and not rows and not footer:
            header = "\n"
        ids = [index(header), index(footer)]
        for row in rows:
            ids.extend(index(part) for part in row)
        if not layouts or ids != layouts[-1][1]:
            layouts.append((columns, ids))

    styles = {}
    functions = ["block() {", '    case "$1" in']
    for view, number in fragments.items():
        if view:
            functions.append(f"        {number}) {_print_view(view, styles)} ;;")
    functions.extend(["    esac", "}", "draw() {"])
    for i, (columns, ids) in enumerate(reversed(layouts)):
        if len(layouts) > 1:
            if i == len(layouts) - 1:
                functions.append("    else")
            else:
                branch = "if" if i == 0 else "elif"
                functions.append(f'    {branch} [ "$columns" -ge {columns} ]; then')
        functions.append("        draw_rows " + " ".join(ids))
    if len(layouts) > 1:
        functions.append("    fi")
    functions.append("}")
    return styles, functions


_VIEWER = r"""
draw_rows() {
    block "$1"
    footer=$2
    shift 2
    row=0
    while [ "$#" -gt 0 ]; do
        if [ "$row" -eq "$selected" ] && [ "$interactive$expanded" != 00 ]; then
            if [ "$interactive" = 1 ]; then printf '\001\n'; fi
            block "$2"
            if [ "$expanded" = 1 ]; then block "$3"; fi
            if [ "$interactive" = 1 ]; then printf '\002\n'; fi
        else
            block "$1"
        fi
        shift 3
        row=$((row + 1))
    done
    block "$footer"
}

dimensions() {
    size=$(stty size 2>/dev/null) || return 1
    set -- $size
    height=${1:-24}
    columns=${2:-80}
    if [ "$height" -lt 1 ]; then height=24; fi
    if [ "$columns" -lt 1 ]; then columns=80; fi
}

redraw() {
    dimensions
    printf '\033[H\033[2J'
    draw | awk -v height="$height" -v columns="$columns" -v page="$page" \
        -v help="$help" -v help_width="$help_width" -v paging="$paging" -v paging_width="$paging_width" '
        $0 == "\001" { start = n + 1; next }
        $0 == "\002" { finish = n; next }
        { lines[++n] = $0 }
        END {
            room = height - int((help_width + columns - 1) / columns) - 1
            if (start && finish - start + 1 > room) {
                help = help "\n" paging
                room -= int((paging_width + columns - 1) / columns)
            }
            if (room < 1) room = 1
            first = finish > room ? finish - room + 1 : 1
            if (start && first > start) first = start
            if (page && finish - start + 1 > room) {
                first += page * room
                if (first > finish - room + 1) first = finish - room + 1
            }
            for (i = first; i <= n && i < first + room; i++) print lines[i]
            printf "\n%s", help
            exit (start && first + room <= finish)
        }'
    next_page=$?
}

restore() {
    stty "$saved" 2>/dev/null
    if [ "$interactive" = 1 ]; then printf '\033[?25h\033[?1049l'; fi
}

interactive=0
columns=80
if [ ! -t 0 ] || [ ! -t 1 ] || [ "${TERM-}" = dumb ]; then
    if [ -t 0 ] && [ -t 1 ]; then dimensions; fi
    draw
    exit
fi
saved=$(stty -g 2>/dev/null) || { draw; exit; }
trap restore 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
# A bounded terminal read also lets the shell handle a signal sent to it alone.
stty -echo -icanon min 0 time 10 || { draw; exit; }
interactive=1
printf '\033[?1049h\033[?25l'
page=0
redraw
sequence=
carriage_return=$(printf '\r')
while :; do
    # A sentinel preserves Return across command substitution on an otherwise empty read.
    key=$(dd bs=1 count=1 2>/dev/null && printf .) || break
    key=${key%.}
    if [ -z "$key" ]; then
        previous="$height:$columns"
        dimensions || break
        if [ "$previous" != "$height:$columns" ]; then page=0; redraw; fi
        continue
    fi
    case "$key" in
        "$escape") sequence=esc; continue ;;
        q|Q) break ;;
    esac
    case "$sequence:$key" in
        'esc:['|esc:O) sequence=arrow; continue ;;
        arrow:5|arrow:6) sequence="page$key"; continue ;;
        'page5:~'|:b) if [ "$page" -gt 0 ]; then page=$((page - 1)); fi ;;
        'page6:~'|:f) if [ "$next_page" = 1 ]; then page=$((page + 1)); fi ;;
        arrow:A|:k) if [ "$selected" -gt 0 ]; then selected=$((selected - 1)); fi; page=0 ;;
        arrow:B|:j) if [ "$selected" -lt "$last" ]; then selected=$((selected + 1)); fi; page=0 ;;
        :'
'|:"$carriage_return"|:' ') expanded=$((1 - expanded)); page=0 ;;
        *) sequence=; continue ;;
    esac
    sequence=
    redraw
done
"""


def terminal_entry(data, *, width=None, ascii_only=False, inspect_level=None,
                   detail=None, color_mode="auto") -> str:
    """Build an offline viewer with keyboard controls and a pipe-friendly plain view."""
    if width is not None and width <= 0:
        raise ValueError("width must be positive")
    if color_mode not in ("auto", "always", "never"):
        raise ValueError("unknown color mode")
    abilities = data["abilities"]
    selected = next((i for i, a in enumerate(abilities) if a.get("focus")), 0)
    if detail is not None:
        selected = next((i for i, a in enumerate(abilities) if a["name"] == detail), None)
        if selected is None:
            raise ValueError(f"unknown ability {detail!r}")

    widths = (width,) if width is not None else (32, 48, 64, 80, 100)
    styles, functions = _layouts(data, widths, color=color_mode != "never",
                                 ascii_only=ascii_only, inspect_level=inspect_level)
    script = ["#!/bin/sh", "escape=$(printf '\\033')"]
    if styles:
        if color_mode == "always":
            script.append("color=1")
        else:
            script.extend(["color=''",
                           'if [ -t 1 ] && [ "${TERM-}" != dumb ] && [ -z "${NO_COLOR-}" ]; then color=1; fi'])
        for sgr, name in styles.items():
            script.append(name + '="${color:+$escape' + sgr[1:] + '}"')

    arrows = "Up/Down" if ascii_only else "↑↓"
    if data["lang"].lower().startswith("zh"):
        help_text = f"{arrows}/jk 选行  回车/空格 详情  q 退出"
        paging = "PgUp/PgDn 翻页"
    else:
        help_text = f"{arrows}/jk move  Return/Space details  q quit"
        paging = "PgUp/PgDn page through details"

    script.extend([f"selected={selected}", f"expanded={int(detail is not None)}",
                   f"last={len(abilities) - 1}", "help=" + shlex.quote(help_text),
                   f"help_width={_width(help_text)}", "paging=" + shlex.quote(paging),
                   f"paging_width={_width(paging)}", *functions, _VIEWER])
    return "\n".join(script)
