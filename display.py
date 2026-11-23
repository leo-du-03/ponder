"""Generate chat-replay HTML pages of an LLM response under three confidence-display modes.

The response is a report of paragraphs. Rated sentences are marked inline as
[[sentence text|85]].

  none      hovering a rated sentence shows a popup with the sentence only, no confidence
  text      hovering a rated sentence shows a popup with the sentence and its confidence as a number ("85%") to its right
  animated  hovering a rated sentence shows a popup with the sentence and an animated face expressing the confidence to its right

Usage:
  python display.py data/sample_response.json --mode all
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
TEMPLATE_PATH = HERE / "templates" / "chat.html"
MODES = ("none", "text", "animated")
N_PARAGRAPHS = 3
MARK_RE = re.compile(r"\[\[(.+?)\|\s*(\d+(?:\.\d+)?)\s*\]\]", re.S)


def parse_paragraph(text: str) -> list:
    """Split a paragraph into segments: plain text, or {"text", "confidence"} for [[...|NN]] marks."""
    segments, pos = [], 0
    for m in MARK_RE.finditer(text):
        if m.start() > pos:
            segments.append({"text": text[pos:m.start()]})
        conf = float(m.group(2))
        segments.append({"text": m.group(1), "confidence": int(conf) if conf.is_integer() else conf})
        pos = m.end()
    if pos < len(text):
        segments.append({"text": text[pos:]})
    return segments


def load_response(path: Path, allow_any_count: bool = False) -> dict:
    """Load and validate a response JSON file. Raises ValueError listing every problem."""
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = []

    if not isinstance(data.get("user_prompt"), str) or not data["user_prompt"].strip():
        errors.append("'user_prompt' must be a non-empty string")
    for key in ("assistant_intro", "assistant_outro"):
        if not isinstance(data.setdefault(key, ""), str):
            errors.append(f"'{key}' must be a string")
    data.setdefault("id", path.stem)

    paragraphs = data.get("paragraphs")
    if not isinstance(paragraphs, list):
        errors.append("'paragraphs' must be a list of strings")
        paragraphs = []
    elif not allow_any_count and len(paragraphs) != N_PARAGRAPHS:
        errors.append(f"expected {N_PARAGRAPHS} paragraphs, found {len(paragraphs)} (use --allow-any-count to override)")

    parsed, n_rated = [], 0
    for i, para in enumerate(paragraphs, 1):
        if not isinstance(para, str) or not para.strip():
            errors.append(f"paragraph {i}: must be a non-empty string")
            continue
        segments = parse_paragraph(para)
        parsed.append(segments)
        for seg in segments:
            text = seg["text"]
            if "confidence" in seg:
                n_rated += 1
                if not text.strip():
                    errors.append(f"paragraph {i}: a rated sentence is empty")
                if not 0 <= seg["confidence"] <= 100:
                    errors.append(f"paragraph {i}: confidence must be from 0 to 100, got {seg['confidence']} for {text[:40]!r}")
            if "[[" in text or "]]" in text or "|" in text:
                errors.append(f"paragraph {i}: malformed confidence mark near {text.strip()[:40]!r} (expected [[sentence|NN]])")
    if paragraphs and not n_rated:
        errors.append("no rated sentences found (mark them as [[sentence|NN]])")
    data["paragraphs"] = parsed

    if errors:
        raise ValueError(f"{path}:\n  " + "\n  ".join(errors))
    return data


def render(data: dict, mode: str, speed: int, stream: bool, hint: bool, autoplay: bool) -> str:
    if mode == "none":
        # Keep confidences out of the page source too, not just off the screen.
        # Rated sentences stay marked as claims so they still get the hover popup.
        data = {**data, "paragraphs": [[{"text": seg["text"], **({"claim": True} if "confidence" in seg else {})}
                                        for seg in para]
                                       for para in data["paragraphs"]]}
    config = {
        "data": data,
        "mode": mode,
        "speed": speed,
        "stream": stream,
        "hint": hint,
        "autoplay": autoplay,
    }
    # Escape "</" so report text can never close the <script> tag.
    config_js = json.dumps(config, ensure_ascii=True).replace("</", "<\\/")
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.substitute(CONFIG=config_js, TITLE=html.escape(data.get("topic") or "Chat"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("response", type=Path, help="response JSON file")
    parser.add_argument("--mode", choices=(*MODES, "all"), default="all")
    parser.add_argument("--out", type=Path, default=HERE / "out", help="output directory")
    parser.add_argument("--speed", type=int, default=30, help="ms per streamed word")
    parser.add_argument("--no-stream", action="store_true", help="show the whole reply at once")
    parser.add_argument("--hint", action="store_true", help="tell users to hover over underlined sentences")
    parser.add_argument("--autoplay", action="store_true", help="start immediately instead of showing a Start button")
    parser.add_argument("--allow-any-count", action="store_true", help=f"allow a paragraph count other than {N_PARAGRAPHS}")
    args = parser.parse_args()

    try:
        data = load_response(args.response, args.allow_any_count)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        sys.exit(f"error: {e}")

    args.out.mkdir(parents=True, exist_ok=True)
    modes = MODES if args.mode == "all" else (args.mode,)
    for mode in modes:
        page = render(data, mode, args.speed, not args.no_stream, args.hint, args.autoplay)
        out_path = args.out / f"{data['id']}_{mode}.html"
        out_path.write_text(page, encoding="utf-8")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
