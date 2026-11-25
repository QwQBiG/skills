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

Draw in the current terminal:

```sh
python3 scripts/render_map.py session.json
```

The terminal uses one compact row per subskill. Use `--detail "Ability name"` for its evidence or `--inspect 4` for the level definition. The display adapts to the terminal width and respects `NO_COLOR`. Override with `--width 48`, `--ascii`, or `--color always` as needed. Use `-` to read a record from stdin.

Generate a standalone page for a phone or browser, or a fragment for an inline chat surface:

```sh
python3 scripts/render_map.py session.json --format html --output mastery.html
python3 scripts/render_map.py session.json --format fragment --output mastery-fragment.html
```

The standalone page opens offline. Expand an ability to see its evidence. Keep the record between turns and render it when the learner needs the full picture.
