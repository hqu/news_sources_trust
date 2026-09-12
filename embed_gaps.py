"""Inline gap_data.json into gaps.html so the page works on a bare file:// open."""
import os
H=os.path.dirname(os.path.abspath(__file__))
html=open(os.path.join(H,"gaps.html"),encoding="utf-8").read()
data=open(os.path.join(H,"gap_data.json"),encoding="utf-8").read()
assert "__PAYLOAD__" in html
out=html.replace("__PAYLOAD__",data); assert "__PAYLOAD__" not in out
open(os.path.join(H,"gaps_standalone.html"),"w",encoding="utf-8").write(out)
print(f"wrote gaps_standalone.html ({len(out)//1024} KB, self-contained)")
