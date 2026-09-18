"""Inline data.json into gradient.html so the page works on a bare file:// open."""
import os
H=os.path.dirname(os.path.abspath(__file__))
html=open(os.path.join(H,"gradient.html"),encoding="utf-8").read()
data=open(os.path.join(H,"data.json"),encoding="utf-8").read()
assert "__PAYLOAD__" in html
out=html.replace("__PAYLOAD__",data); assert "__PAYLOAD__" not in out
open(os.path.join(H,"gradient_standalone.html"),"w",encoding="utf-8").write(out)
print(f"wrote gradient_standalone.html ({len(out)//1024} KB, self-contained)")
