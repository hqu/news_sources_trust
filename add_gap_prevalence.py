"""Weighted share holding each outcome, on the gap dashboard's own sample.

The gap models are fitted on Democrats and Republicans only, so the prevalence quoted beside
an outcome there cannot be borrowed from the forest-plot payload, which includes independents.
One pass over the waves; writes `prev` onto each outcome in gap_data.json. Aggregates only.
"""
import pandas as pd, numpy as np, os, sys, json, warnings
warnings.filterwarnings("ignore")
P=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(P,"..","paper2","eda"))
import wave_rule, chip50_clean as CC, fn_labels as FL
D="/Users/hongqu/CHIP50_restricted"
G=json.load(open(os.path.join(P,"gap_data.json")))
VAR={"science":"pol_trust_science","doctors":"pol_trust_doctors","cdc":"pol_trust_cdc",
     "fda":"pol_trust_fda","pharma":"pol_trust_pharma","fauci":"pol_trust_fauci",
     "rfk":"pol_trust_rfk","musk":"pol_trust_musk","trump":"pol_trust_trump",
     "whitehouse":"pol_trust_white_house","scotus":"pol_trust_court","denial":"trump_win"}
FN={"gmo":"Genetically modified foods have harmful effects",
    "machines":"Voting machines in the 2020 election were rigged",
    "cia":"A dying CIA agent confessed","turbines":"Wind turbines cause cancer",
    "soros":"George Soros is secretly working"}
num=lambda k: {o["key"]:o for o in G["outcomes"]}[k]
acc={o["key"]:[0.0,0.0] for o in G["outcomes"]}
for w in sorted(wave_rule.MODEL_WAVES,key=float):
    f=os.path.join(D,f"CSP_W{w}.csv")
    if not os.path.exists(f): continue
    h=set(pd.read_csv(f,nrows=0).columns)
    if "pol_news1_5" not in h: continue
    fnmap={k:next((c for c,l in FL.labels().get(str(w),{}).items() if v.lower() in l.lower()),None)
           for k,v in FN.items()}
    want=[v for v in VAR.values() if v in h]+[c for c in fnmap.values() if c and c in h]
    if not want: continue
    d=pd.read_csv(f,usecols=sorted(set(want+["weight","party7"])),low_memory=False)
    p7=pd.to_numeric(d["party7"],errors="coerce")
    dr=p7.isin([1,2,3,5,6,7])
    wt=pd.to_numeric(d["weight"],errors="coerce").fillna(0)
    for k,o in ((o["key"],o) for o in G["outcomes"]):
        col = VAR.get(k) if k in VAR else fnmap.get(k)
        if not col or col not in d: continue
        v=CC.num(d[col])
        y = (v==1) if k in FN else ((v>=4) if col in ("trump_win",) else (v>=3))
        m = dr & v.notna()
        acc[k][0]+= float((wt[m]*y[m]).sum()); acc[k][1]+= float(wt[m].sum())
for o in G["outcomes"]:
    s,t=acc[o["key"]]
    o["prev"]=round(100*s/t,1) if t else None
json.dump(G,open(os.path.join(P,"gap_data.json"),"w"),separators=(",",":"))
for o in G["outcomes"]: print(f"  {o['key']:<12}{o['prev']}%   {o['label']}")
