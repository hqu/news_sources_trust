"""Write index_standalone.html — index.html with data.json embedded, no server needed.

Collaborators get one file they can open by double-clicking. The served version
(index.html + data.json) still works and is what to use while iterating.
"""
import json, os
D=os.path.dirname(os.path.abspath(__file__))
html=open(os.path.join(D,"index.html")).read()
data=json.load(open(os.path.join(D,"data.json")))
out=html.replace("__PAYLOAD__", json.dumps(data, separators=(",",":")))
assert "__PAYLOAD__" not in out, "placeholder not found in index.html"
p=os.path.join(D,"index_standalone.html")
open(p,"w").write(out)
print(f"wrote index_standalone.html ({os.path.getsize(p)/1024:.0f} KB, self-contained)")
