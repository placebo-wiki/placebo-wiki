"""Fails if text contains an em dash. Used by the git pre-commit hook and the Claude Code edit hook."""
import json
import subprocess
import sys

DASH = "\u2014"


def git_staged() -> int:
    files = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                           capture_output=True, text=True, check=True).stdout.split()
    bad = []
    for f in files:
        if f.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".mp4", ".woff2", ".zip")):
            continue
        blob = subprocess.run(["git", "show", f":{f}"], capture_output=True, check=True).stdout
        if DASH.encode() in blob:
            bad.append(f)
    if bad:
        print("Длинное тире запрещено в проекте. Уберите его из: " + ", ".join(bad) +
              ". Быстро: python3 tools/nodash.py <файлы>", file=sys.stderr)
        return 1
    return 0


def claude_hook() -> int:
    data = json.load(sys.stdin)
    ti = data.get("tool_input", {})
    path = ti.get("file_path", "")
    if "/placebo-wiki/" not in path:
        return 0
    text = ti.get("content", "") + ti.get("new_string", "")
    if DASH in text:
        print("Длинное тире запрещено в проекте placebo-wiki (правило владельца). Перепиши без него: двоеточие, запятая или точка.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(claude_hook() if "--claude" in sys.argv else git_staged())
