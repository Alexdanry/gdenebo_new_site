#!/usr/bin/env python3
"""Builds tilda/gdenebo-tilda.html: the whole site as ONE block for Tilda's HTML ("T123") block.

  python3 tilda/build.py                      # images from https://gdenebo.onrender.com/
  python3 tilda/build.py https://my.cdn/gd/   # images from your own host (trailing slash)

What it does
  * scopes every CSS rule under .gd so the site cannot restyle the rest of the Tilda page
  * renames @keyframes/@property with a gd- prefix so they cannot clash with Tilda's
  * rewrites image URLs (img/...) to absolute ones (an HTML block has no files of its own)
  * keeps the page scripts (nav bar, VK loop, Spotify scaler)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://gdenebo.onrender.com/").rstrip("/") + "/"

html = (ROOT / "index.html").read_text(encoding="utf-8")
css = (ROOT / "style.css").read_text(encoding="utf-8")

# ---------------------------------------------------------------- CSS scoping
css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
ANIM_NAMES = sorted(set(re.findall(r"@keyframes\s+([\w-]+)", css)), key=len, reverse=True)
PROPS = re.findall(r"@property\s+(--[\w-]+)", css)


def blocks(text):
    """Split into (prelude, body) top-level blocks by brace matching."""
    out, i, n = [], 0, len(text)
    while i < n:
        j = text.find("{", i)
        if j == -1:
            break
        prelude = text[i:j].strip()
        depth, k = 1, j + 1
        while depth and k < n:
            depth += (text[k] == "{") - (text[k] == "}")
            k += 1
        out.append((prelude, text[j + 1:k - 1]))
        i = k
    return out


def scope_selector(sel):
    sel = sel.strip()
    if sel in ("html", "body", ":root", "html, body"):
        return ".gd"
    sel = re.sub(r"^(html|body|:root)\s+", "", sel)
    return ".gd " + sel


def process(text):
    out = []
    for prelude, body in blocks(text):
        if prelude.startswith(("@keyframes", "@property")):
            name = prelude.split()[-1]
            out.append(f"{prelude.split()[0]} gd-{name.lstrip('-')} {{{body}}}" if prelude.startswith("@keyframes")
                       else f"@property {name} {{{body}}}")
        elif prelude.startswith(("@media", "@supports", "@container")):
            out.append(f"{prelude} {{\n{process(body)}\n}}")
        else:
            sels = ", ".join(scope_selector(s) for s in prelude.split(","))
            out.append(f"{sels} {{{body}}}")
    return "\n".join(out)


css = process(css)
for name in ANIM_NAMES:
    css = re.sub(rf"(animation(?:-name)?\s*:[^;{{}}]*?)(?<![\w-]){re.escape(name)}(?![\w-])", rf"\1gd-{name}", css)
css = css.replace("url(img/", f"url({BASE}img/")

# ---------------------------------------------------------------- HTML -> one block
body = re.search(r"<body>(.*)</body>", html, flags=re.S).group(1)
scripts = "".join(re.findall(r"<script.*?</script>", body, flags=re.S))
markup = re.sub(r"<script.*?</script>", "", body, flags=re.S)
markup = re.sub(r'(src|href)="img/', rf'\1="{BASE}img/', markup)
markup = re.sub(r"\?v=\d+", "", markup)

smooth = "<script>document.documentElement.style.scrollBehavior='smooth';</script>"
out = f"""<!-- gdenebo: paste into a Tilda "HTML" (T123) block. Images come from {BASE} -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
{css}
</style>
<div class="gd">
{markup.strip()}
</div>
{scripts}
{smooth}
"""
dest = ROOT / "tilda" / "gdenebo-tilda.html"
dest.write_text(out, encoding="utf-8")
print(f"wrote {dest.relative_to(ROOT)}  ({len(out) // 1024} KB, images from {BASE})")
