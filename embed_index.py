"""Inline quantities.json into index.html -> index_standalone.html.

Matches embed_data.py / embed_gaps.py: the served pair is index.html + quantities.json,
the self-contained copy carries the payload in its #payload script tag so it opens from Finder.
"""
import base64, json, os
H = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(H, "index.html")).read()
data = open(os.path.join(H, "quantities.json")).read()
tag = '<script id="payload" type="application/json"></script>'
assert tag in html, "payload tag not found"
out = html.replace(tag, '<script id="payload" type="application/json">' + data + '</script>')

# the flow map is a file reference when served and a data URI when opened from Finder
png = os.path.join(H, "figures", "information_flow_map_dashboard.png")
if os.path.exists(png):
    uri = "data:image/png;base64," + base64.b64encode(open(png, "rb").read()).decode()
    assert 'src="figures/information_flow_map_dashboard.png"' in out, "flow map img not found"
    out = out.replace('src="figures/information_flow_map_dashboard.png"', 'src="' + uri + '"')
else:
    print("  WARNING: figures/information_flow_map_dashboard.png missing, standalone will have a broken image")
p = os.path.join(H, "index_standalone.html")
open(p, "w").write(out)
print(f"wrote index_standalone.html  {os.path.getsize(p)/1024:.0f} KB")
