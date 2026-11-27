# Rendering a mastery map

The renderer uses Python 3.9 or later and the standard library. Run these commands from the skill's directory. Store the UTF-8 session record with the learner's local session artifacts.

| Record field | Content |
| --- | --- |
| `topic`, `summary` | Topic name and an optional short assessment caption. |
| `goal` | Shared target, 0–5. Defaults to 4. Existing records may also contain an explicit topic rating in `current`. |
| `abilities` | Ordered subskills with `name`, `status`, `state`, `evidence`, and `level` (0–5 or null). Preserve the distinction between a first independent success and a confirmed independent level. |
| `focus`, `next_check` on an ability | Set `focus: true` on the one subskill under practice. Optionally record what the next question should test. Keep the solution out of this cue. |
| `state` on each ability | Use `guided` for work completed with help, `observed` for demonstrated work, or `unassessed` for an untested ability. Supply a numeric level only when assessed. |
| `lang`, `goal_label`, `scale_label`, `evidence_label`, `focus_label`, `check_label` | Optional language tag and localized display labels. |
| `levels` | Optional list of six objects with a short `label` and a one-sentence `meaning`, ordered 0–5. Supply these and the display labels for languages other than English. |

Draw in the current terminal.

```sh
python3 scripts/render_map.py session.json
```

On a Mac or Linux terminal, use ↑/↓ or j/k to select a subskill and Return or Space to toggle its evidence. Press `s` to read the six level definitions and `s` again to return to the same row. Press `q` to quit.

Use `--once` for a compact snapshot or `--once --scale` to print the whole scale. Use `--detail "Ability name"` for one row's evidence or `--inspect 4` for a single level. The display follows the terminal width and `NO_COLOR`, with overrides for `--width`, `--ascii` and `--color`. Use `-` to read a record from stdin.

To share the terminal view, export a self-contained file alongside the record.

```sh
python3 scripts/render_map.py session.json --format command --output mastery.command
```

Double-click the exported file on macOS, or run `sh /path/to/mastery.command` in a POSIX shell. On a Mac you can display it in a new terminal with `open -a Terminal /path/to/mastery.command`. Give the learner the actual path, quoted when needed. The exported view works offline with the system shell and includes the scores at export time.

Generate a standalone page for a phone or browser, or a fragment for an inline chat surface.

```sh
python3 scripts/render_map.py session.json --format html --output mastery.html
python3 scripts/render_map.py session.json --format fragment --output mastery-fragment.html
```

Link to the generated page. It opens offline and each ability expands to show its evidence. The bundled `assets/mastery-map.html` also opens on its own and lets the reader choose a local record.
