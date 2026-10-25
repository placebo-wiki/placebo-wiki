"""Removes em dashes from text: the project bans them (owner's rule, 25.10.2026)."""
import re
import sys

DASH = "\u2014"


def clean(text: str) -> str:
    text = re.sub(rf"[  ]+{DASH}[  ]*(?=\n|$|\"|'|`|<)", "", text)
    text = re.sub(rf"[  ]+{DASH}[  ]+", ": ", text)
    return text.replace(DASH, "-")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        out = clean(src)
        if out != src:
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
            print("fixed", path)
