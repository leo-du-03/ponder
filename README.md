# ponder

Generates self-contained HTML pages that replay a chat with an LLM, for studying how
different ways of displaying confidence affect readers. The assistant's reply is a short
report in which some sentences carry a confidence rating (0–100). Each page shows the
same reply under one of three display modes.

| Mode       | Hovering a rated sentence shows…                                              |
|------------|-------------------------------------------------------------------------------|
| `none`     | a popup with the sentence only. Confidences are left out of the page source too. |
| `text`     | the sentence plus its confidence as a number (e.g. `85%`)                      |
| `animated` | the sentence plus an animated face that expresses the confidence              |

## Layout

```
display.py          generator script (Python 3, standard library only)
templates/chat.html page template: styles, popup, face animation, streaming playback
data/               response JSON files, one per topic
out/                generated pages, named <id>_<mode>.html
```

## Usage

```bash
# All three modes for one response
python display.py data/sample_response.json

# A single mode
python display.py data/food_waste.json --mode animated --allow-any-count
```

Options:

| Flag                | Default | Effect                                                        |
|---------------------|---------|---------------------------------------------------------------|
| `--mode`            | `all`   | `none`, `text`, `animated`, or `all`                          |
| `--out DIR`         | `out/`  | output directory                                              |
| `--speed MS`        | `30`    | milliseconds per streamed word                                |
| `--no-stream`       | off     | show the whole reply at once                                  |
| `--hint`            | off     | show a note telling users to hover over underlined sentences  |
| `--autoplay`        | off     | start right away instead of showing a Start button            |
| `--allow-any-count` | off     | accept a paragraph count other than 3                         |

The output pages need no server or network access; open them directly in a browser.

## Response format

```json
{
  "id": "coffee_health",
  "topic": "Health effects of coffee",
  "user_prompt": "Research the health effects of drinking coffee and write me a short 3-paragraph report.",
  "assistant_intro": "",
  "paragraphs": [
    "Plain text. [[A rated sentence.|90]] More plain text.",
    "...",
    "..."
  ],
  "assistant_outro": ""
}
```

- `user_prompt` (required): the message shown in the user's bubble.
- `paragraphs` (required): exactly 3 strings unless `--allow-any-count` is passed.
  Mark rated sentences inline as `[[sentence text|NN]]`, where `NN` is 0–100.
  At least one rated sentence is required.
- `id`: used in output file names. Defaults to the JSON file's name.
- `topic`: the page title.
- `assistant_intro`, `assistant_outro`: optional text before and after the report.

The script validates the file and lists every problem it finds (malformed marks,
out-of-range confidences, wrong paragraph count) before writing anything.

Note: `covid_work.json`, `food_waste.json` and `study_abroad.json` have 4 paragraphs each,
so they need `--allow-any-count`.

## Tuning the face

Constants at the top of the `<script>` in [templates/chat.html](templates/chat.html):

- `FACE_MIN` / `FACE_MAX` (50 / 100): the confidence range the face's expression spans.
  Anything below `FACE_MIN` gets the most unsure face.
- `BUCKET_LOW` / `BUCKET_HIGH` (70 / 85): thresholds for the idle animation. Below 70 the
  face wobbles, glances aside and sweats; between 70 and 85 it tilts; above 85 it nods.
- `TYPING_MS`, `PAUSE_MS`, `MORPH_MS`: timing for the typing indicator, the pause between
  paragraphs, and the face's entrance morph.

The page uses a fixed light theme so that every participant sees the same visuals.

## AI Usage Disclosure
Claude Opus 5.5 was used to assist in the writing and debugging of this code.