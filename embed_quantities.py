"""Inline quantities.json into quantities.html -> quantities_standalone.html.

Matches embed_data.py / embed_gaps.py: the served pair is quantities.html + quantities.json,
the self-contained copy carries the payload in its #payload script tag so it opens from Finder.
"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(H, "quantities.html")).read()
data = open(os.path.join(H, "quantities.json")).read()
tag = '<script id="payload" type="application/json"></script>'
assert tag in html, "payload tag not found"
out = html.replace(tag, '<script id="payload" type="application/json">' + data + '</script>')
p = os.path.join(H, "quantities_standalone.html")
open(p, "w").write(out)
print(f"wrote quantities_standalone.html  {os.path.getsize(p)/1024:.0f} KB")
