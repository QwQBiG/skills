# Rendering a mastery map

The renderer uses Python 3.9 or later and the standard library. Run these commands from the skill's directory. Store the UTF-8 session record with the learner's local session artifacts.

| Record field | Content |
| --- | --- |
| `topic`, `summary` | Topic name and an optional short assessment caption. |
| `current`, `goal` | Level from 0 to 5 or `null`. The default goal is 4. Use `null` for an unknown topic level. |
| `abilities` | An ordered list of objects with `name`, `status`, `state`, `evidence`, and an optional numeric `level`. |
| `state` on each ability | Use `guided` for work completed with help, `observed` for demonstrated work, or `unassessed` for an untested ability. Supply a numeric level only when assessed. |
| `lang`, `current_label`, `goal_label`, `scale_label`, `evidence_label` | Optional language tag and localized labels. Set `current_label` to the local word for “provisional” for a tentative rating. |
| `levels` | Optional list of six objects with a short `label` and a one-sentence `meaning`, ordered 0–5. Supply these and the display labels for languages other than English. |

Draw in the current terminal:

```sh
python3 scripts/render_map.py session.json
```

The terminal adapts to the available width. It uses color in interactive color terminals and respects `NO_COLOR`. Use `--inspect 4` to read the description of level 4, `--width 48` for a narrower display, or `--ascii` for basic glyphs. Use `--color always` for an ANSI-capable capture. Inputs can also be piped using `-` in place of the filename.

Generate a standalone page for a phone or browser, or a fragment for an inline chat surface:

```sh
python3 scripts/render_map.py session.json --format html --output mastery.html
python3 scripts/render_map.py session.json --format fragment --output mastery-fragment.html
```

Deliver the rendered result. The standalone page opens offline. Selecting a level reveals its meaning, and opening an ability shows the observation supporting its status. Exploring the diagram leaves the assessment intact.
