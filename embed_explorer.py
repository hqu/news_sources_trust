"""Inline data.json into explorer.html so the page works on a bare file:// open.

Same reason as embed_data.py: fetch() is blocked for file:// origins, so a double-clicked
explorer.html would silently render nothing. Writes explorer_standalone.html.
Aggregated model output only; no respondent-level data is present in either file.
"""
import json, os, datetime
H = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(H, "explorer.html"), encoding="utf-8").read()
payload = open(os.path.join(H, "data.json"), encoding="utf-8").read()
assert "__PAYLOAD__" in html, "placeholder missing from explorer.html"
out = html.replace("__PAYLOAD__", payload)
assert "__PAYLOAD__" not in out
p = os.path.join(H, "explorer_standalone.html")
open(p, "w", encoding="utf-8").write(out)
print(f"wrote explorer_standalone.html ({len(out)//1024} KB, self-contained) "
      f"at {datetime.datetime.now():%Y-%m-%d %H:%M}")
