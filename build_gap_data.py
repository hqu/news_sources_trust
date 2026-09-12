"""Precompute the gap dashboard: predicted probabilities and percentage-point gaps.

WHY A SEPARATE BUILD. The forest-plot payload reports odds ratios per stratum. This dashboard's
estimand is different and cannot be recovered from it: predicted probabilities for users and
non-users, and a contrast between two such gaps. That needs predicted probabilities, an
interval on a DIFFERENCE, and a difference-in-differences, none of which data.json carries.

THE MODEL, per (outcome, source). Survey-weighted logistic regression on the sample of
Democrats and Republicans (leaners folded by lean; pure independents are excluded so that
every cell is a subset of one sample and the pooled row is not made of people who appear in
no panel):

    logit P(Y) = a + S + R + E + S:R + S:E + R:E + S:R:E
                 + age + income + male + every OTHER source + wave fixed effects

S = uses this source for political news, R = Republican, E = college degree or higher.
The three-way interaction is what makes the gap-of-gaps an estimate rather than a comparison
of two separately fitted numbers.

THE QUANTITIES are computed by g-computation: predict every respondent in a cell under S=1
and under S=0, average with survey weights, difference. Intervals come from the delta method
on the same fitted covariance, so a gap, a gap-of-gaps and a party contrast are all linear
combinations of the same gradient vectors and their intervals are mutually consistent.

AGGREGATES ONLY. The output is probabilities, differences, intervals and counts. No
respondent-level data is written.
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os, json, sys, time, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper2", "eda"))
import wave_rule, chip50_clean as CC, fn_labels as FL
D = "/Users/hongqu/CHIP50_restricted"
OUT = os.path.dirname(os.path.abspath(__file__))

CHAN = {"pol_news1_5":("Network TV","JS"),   "pol_news1_4":("Local TV","JS"),
        "pol_news1_8":("Print newspapers","JS"), "pol_news1_9":("News site or app","JS"),
        "pol_news1_16":("Community newspaper","JS"),
        "pol_news1_6":("Cable TV","PB"), "pol_news1_2":("Radio news","PB"),
        "pol_news1_7":("Late-night comedy","PB"),
        "pol_news1_14":("Social media","VLP"), "pol_news1_3":("Podcasts","DEC"),
        "pol_news1_15":("Messaging app","PVT"), "pol_news1_1":("Friends and family","INT"),
        "pol_news1_13":("Search engine","SRCH"), "pol_news1_17":("AI chatbot","AICH")}
REGIMES = ["JS","PB","SRCH","AICH","VLP","PVT","INT","DEC"]
REGIME_LABEL = {"JS":"Journalistic Standard","PB":"Partisan Broadcast","VLP":"Very Large Platform",
                "DEC":"Podcasts","PVT":"Private Messaging","INT":"Interpersonal Ties",
                "SRCH":"Search Engine","AICH":"AI Chat"}
EDU = {"Some High School or Less":1,"High School Graduate":2,"Some College":3,
       "College Degree":4,"Graduate Degree":5}
OUTCOMES = [
 ("science","pol_trust_science","Trust","Trust in scientists and researchers","trust"),
 ("doctors","pol_trust_doctors","Trust","Trust in hospitals and doctors","trust"),
 ("cdc","pol_trust_cdc","Trust","Trust in the CDC","trust"),
 ("fda","pol_trust_fda","Trust","Trust in the FDA","trust"),
 ("pharma","pol_trust_pharma","Trust","Trust in pharmaceutical companies","trust"),
 ("fauci","pol_trust_fauci","Trust","Trust in Anthony Fauci","trust"),
 ("denial","trump_win","Conspiracy","Election denial — Trump won in 2020","belief"),
 ("rfk","pol_trust_rfk","Outlier","Trust in Robert F. Kennedy Jr.","trust"),
 ("musk","pol_trust_musk","Outlier","Trust in Elon Musk","trust"),
 ("trump","pol_trust_trump","Government","Trust in Donald Trump","trust"),
 ("whitehouse","pol_trust_white_house","Government","Trust in the White House","trust"),
 ("scotus","pol_trust_court","Government","Trust in the US Supreme Court","trust"),
]
FN_OUTCOMES = [
 ("gmo","Genetically modified foods have harmful effects","Conspiracy","GM foods have hidden harmful effects"),
 ("machines","Voting machines in the 2020 election were rigged","Conspiracy","2020 voting machines were rigged"),
 ("cia","A dying CIA agent confessed","Conspiracy","US agencies were behind 9/11"),
 ("turbines","Wind turbines cause cancer","Conspiracy","Wind turbines cause cancer"),
 ("soros","George Soros is secretly working","Conspiracy","Soros is destabilising the US"),
]
CONSP=["conspiracy_1","conspiracy_2","conspiracy_3","conspiracy_4"]
NEED = sorted({v for _,v,_,_,_ in OUTCOMES} | set(CONSP))

print("loading waves...", flush=True)
fr=[]
for w in sorted(wave_rule.MODEL_WAVES, key=float):
    f=os.path.join(D,f"CSP_W{w}.csv")
    if not os.path.exists(f): continue
    h=set(pd.read_csv(f,nrows=0).columns)
    if "pol_news1_5" not in h: continue
    have=[c for c in CHAN if c in h]
    tg=[t for t in NEED if t in h]
    fnmap={}
    for key,claim,_,_ in FN_OUTCOMES:
        col=next((c for c,l in FL.labels().get(str(w),{}).items()
                  if claim.lower() in l.lower()), None)
        if col and col in h: fnmap[key]=col
    if not tg and not fnmap: continue
    cols=[c for c in have+tg+list(fnmap.values())
          +["weight","party7","education_cat","income_cat_5","age","male","female"] if c in h]
    d=pd.read_csv(f,usecols=sorted(set(cols)),low_memory=False); d["wave"]=w
    for key,_,_,_ in FN_OUTCOMES: d["FN_"+key]=d[fnmap[key]] if key in fnmap else np.nan
    for c in CHAN:
        d[c]=(pd.to_numeric(d[c],errors="coerce").fillna(0)>0).astype(float) if c in d else np.nan
    for rg in REGIMES:
        src=[c for c in have if CHAN[c][1]==rg]
        d[rg]=(d[src]>0).any(axis=1).astype(float) if src else np.nan
    for t in NEED+["male","female"]:
        if t not in d: d[t]=np.nan
    fr.append(d[["wave","weight","party7","education_cat","income_cat_5","age","male","female"]
                +NEED+["FN_"+k for k,_,_,_ in FN_OUTCOMES]+list(CHAN)+REGIMES])
d=pd.concat(fr,ignore_index=True)
d["edu"]=d["education_cat"].map(EDU)
for c in ["weight","party7","income_cat_5","age"]: d[c]=pd.to_numeric(d[c],errors="coerce")
d["male_c"]=CC.male_from(d)
# party7 runs 1 Strong Republican .. 7 Strong Democrat; leaners (3,5) fold toward their lean.
d["R"]=np.where(d["party7"].isin([1,2,3]),1.0,np.where(d["party7"].isin([5,6,7]),0.0,np.nan))
d["E"]=np.where(d["edu"]>=4,1.0,np.where(d["edu"].notna(),0.0,np.nan))   # college degree or higher
d=d[d["R"].notna()&d["E"].notna()].copy()
print(f"  {len(d):,} rows (Democrats and Republicans), {d['wave'].nunique()} waves", flush=True)

def question_text(var, Q):
    """Verbatim wording for an outcome: the battery stem plus the item, where there is a stem.

    Trust and conspiracy items read as a bare target or statement on their own ("Scientists
    and researchers"), so the stem is what makes them a question."""
    ent = Q.get("outcome", {})
    e = ent.get(var)
    if not e: return None
    item = e["text"] if isinstance(e, dict) else e
    stem = None
    for pre in ("conspiracy", "fn", "pol_trust"):
        if var.lower().startswith(pre) and "__stem_" + pre in ent:
            stem = ent["__stem_" + pre]["text"]; break
    if not stem: return item
    return stem.rstrip(" -\u2014 ").rstrip() + " \u2014 " + item

def y_of(var):
    v=CC.num(d[var])
    if var.startswith("FN_"): return (v==1).astype(float).where(v.notna())
    if var=="trump_win" or var.startswith("conspiracy"): return (v>=4).astype(float).where(v.notna())
    return (v>=3).astype(float).where(v.notna())

for c in CONSP: d["C_"+c]=CC.num(d[c])
CC_COLS=["C_"+c for c in CONSP]
# The four conspiracy items are controls rather than outcomes, which is what lets them be
# controls at all. It costs wave coverage -- the battery runs in 11 of the 15 model waves --
# and for an outcome whose own waves barely overlap it, what survives is not a sample. Those
# outcomes keep the uncontrolled specification and the payload records which ones.
BASE_CTRL=["age","income_cat_5","male_c"]
BASE=BASE_CTRL+CC_COLS

def consp_viable(y):
    ok = y.notna() & d["weight"].notna()
    both = (ok & d[CC_COLS].notna().all(axis=1)).sum()
    return bool(both >= 2000 and both >= 0.4*ok.sum())
SOURCES=([(rg,REGIME_LABEL[rg],"regime",None) for rg in REGIMES]
        +[(c,CHAN[c][0],"channel",CHAN[c][1]) for c in CHAN])

def fit_one(y, skey, others, base=None):
    """One model; returns a closure that evaluates any contrast of predicted probabilities."""
    base = BASE if base is None else base
    keep=["weight","wave","R","E",skey]+base+others
    sub=d.assign(y=y).dropna(subset=["y"]+keep)
    if len(sub)<3000: return None
    S=sub[skey].values; R=sub["R"].values; E=sub["E"].values
    W=pd.get_dummies(sub["wave"].astype(str),prefix="w",drop_first=True).astype(float).values
    O=sub[others].values if others else np.zeros((len(sub),0))
    ctrl=np.column_stack([sub[c].astype(float).values for c in base]+[O,W])
    # column block order: 1, S, R, E, S:R, S:E, R:E, S:R:E, ctrl...
    def design(s):
        s=np.full_like(S,s,dtype=float) if np.isscalar(s) else s
        return np.column_stack([np.ones_like(S), s, R, E, s*R, s*E, R*E, s*R*E, ctrl])
    X=design(S)
    keepcol=X.std(axis=0)>1e-9; keepcol[0]=True
    X=X[:,keepcol]
    wt=sub["weight"].values
    try:
        m=sm.GLM(sub["y"].values, X, family=sm.families.Binomial(), freq_weights=wt).fit()
    except Exception:
        return None
    V=np.asarray(m.cov_params()); b=np.asarray(m.params)
    def pp(mask, s):
        """weighted mean predicted probability over `mask` with the source set to `s`;
        returns (value, gradient) so any linear combination has a delta-method variance."""
        if mask.sum()==0: return (np.nan, np.zeros_like(b))
        Xs=design(s)[:,keepcol][mask]; ws=wt[mask]; ws=ws/ws.sum()
        eta=Xs@b; p=1/(1+np.exp(-eta))
        return (float(ws@p), (ws*p*(1-p))@Xs)
    def ci(val, grad):
        se=float(np.sqrt(max(grad@V@grad,0)))
        return (float(val), float(val-1.96*se), float(val+1.96*se))
    return dict(sub=sub, S=S, R=R, E=E, wt=wt, pp=pp, ci=ci, n=len(sub),
                waves=sorted(sub["wave"].unique(), key=float),
                beta_S=float(b[1]) if keepcol[1] else np.nan,
                se_S=float(np.sqrt(V[1,1])) if keepcol[1] else np.nan)


# ---------------------------------------------------------------- contrast grammar
# Three binary splits. Any one of them can be the COMPARISON (the two ends of the gap);
# the others either define panels or are pooled over. Every quantity below is a difference
# of two weighted mean predicted probabilities, so one helper covers all of them and their
# intervals come from the same covariance.
def mask_from(Rv, Ev, **fix):
    """`fix` uses the keys "R" and "E", so the positional args must not share those names."""
    m=np.ones(len(Rv),bool)
    if "R" in fix: m &= (Rv==fix["R"])
    if "E" in fix: m &= (Ev==fix["E"])
    return m

# panel definitions: compare dimension -> list of (panelKey, fixed levels, source setting)
def panels_for(compare):
    out=[]
    if compare=="source":
        out.append(("", {}))
        for k,f in [("dem",{"R":0}),("rep",{"R":1}),("deg",{"E":1}),("nodeg",{"E":0}),
                    ("dem_deg",{"R":0,"E":1}),("dem_nodeg",{"R":0,"E":0}),
                    ("rep_deg",{"R":1,"E":1}),("rep_nodeg",{"R":1,"E":0})]:
            out.append((k,f))
    elif compare=="party":
        for s in (0,1):
            out.append((f"s{s}", {"_s":s}))
            out.append((f"s{s}_deg", {"_s":s,"E":1}))
            out.append((f"s{s}_nodeg", {"_s":s,"E":0}))
    else:  # diploma
        for s in (0,1):
            out.append((f"s{s}", {"_s":s}))
            out.append((f"s{s}_dem", {"_s":s,"R":0}))
            out.append((f"s{s}_rep", {"_s":s,"R":1}))
    return out

# which pair of (mask, source-setting) the two ends of the gap are, for a given panel
def ends_for(compare, fix, R, E):
    f={k:v for k,v in fix.items() if k in ("R","E")}
    if compare=="source":
        m=mask_from(R,E,**f); return (m,1.0),(m,0.0)          # user minus non-user
    s=float(fix["_s"])
    if compare=="party":
        return (mask_from(R,E,**{**f,"R":0}),s),(mask_from(R,E,**{**f,"R":1}),s)  # Dem minus Rep
    return (mask_from(R,E,**{**f,"E":1}),s),(mask_from(R,E,**{**f,"E":0}),s)      # degree minus not

# gap-of-gaps: which two panels to difference, per comparison
DIDS={"source":[("party","dem","rep"),("diploma","deg","nodeg")],
      "party":[("source","s1","s0"),("diploma","s1_deg","s1_nodeg")],
      "diploma":[("source","s1","s0"),("party","s1_dem","s1_rep")]}

payload={"meta":{"built":pd.Timestamp.now().strftime("%Y-%m-%d"),
                 "source":"CHIP50 / Civic Health and Institutions Project",
                 "note":"Aggregated model output only. No respondent-level data is present.",
                 "sample":"Democrats and Republicans, leaners folded by lean; pure independents excluded.",
                 "regimes":[{"key":k,"label":REGIME_LABEL[k]} for k in REGIMES],
                 "sources":[{"key":k,"label":l,"kind":t,"parent":p} for k,l,t,p in SOURCES]},
         "outcomes":[], "cells":{}}
QTXT=json.load(open(os.path.join(OUT,"questions.json"),encoding="utf-8"))
for k,v,g,lab,dirn in OUTCOMES:
    payload["outcomes"].append(dict(key=k,label=lab,group=g,direction=dirn,q=question_text(v,QTXT)))
for k,_,g,lab in FN_OUTCOMES:
    payload["outcomes"].append(dict(key=k,label=lab,group=g,direction="belief",
                                    q=question_text("FN_"+k,QTXT)))
VARS={k:v for k,v,_,_,_ in OUTCOMES}; VARS.update({k:"FN_"+k for k,_,_,_ in FN_OUTCOMES})

t0=time.time(); done=0; total=len(payload["outcomes"])*len(SOURCES)
for o in payload["outcomes"]:
    y=y_of(VARS[o["key"]])
    o["consp_control"]=consp_viable(y)
    dr=d["weight"].notna() & y.notna()
    o["prev"]=round(float(100*(d["weight"][dr]*y[dr]).sum()/d["weight"][dr].sum()),1)
    base = BASE if o["consp_control"] else BASE_CTRL
    print(f"  {o['key']:<10}conspiracy control="
          f"{'yes' if o['consp_control'] else 'NO (exempt)'}",flush=True)
    for skey,slab,kind,parent in SOURCES:
        done+=1
        if d[skey].notna().sum()==0: continue
        AI={"AICH","pol_news1_17"}
        others=[x for x,_,k2,_ in SOURCES
                if k2==kind and x!=skey and x not in AI and d[x].notna().any()]
        M=fit_one(y,skey,others,base)
        if M is None: continue
        R,E,S,wt=M["R"],M["E"],M["S"],M["wt"]; yv=M["sub"]["y"].values
        G={}
        for compare in ("source","party","diploma"):
            for pkey,fix in panels_for(compare):
                (ma,sa),(mb,sb)=ends_for(compare,fix,R,E)
                if ma.sum()<50 or mb.sum()<50: continue
                pa,ga=M["pp"](ma,sa); pb,gb=M["pp"](mb,sb)
                if not (np.isfinite(pa) and np.isfinite(pb)): continue
                gap,lo,hi=M["ci"](pa-pb, ga-gb)
                def arm(mask, s_state):
                    """Observed rate and count among the people the panel is about.

                    The predicted probability is a g-computation and averages over the whole
                    group; the count reported beside it is the number actually in that state."""
                    sel = mask & (S == s_state)
                    n=int(sel.sum())
                    if n==0: return None,0
                    w=wt[sel]; return float(100*(w*yv[sel]).sum()/w.sum()), n
                ra,na=arm(ma,sa); rb,nb=arm(mb,sb)
                G[f"{compare}|{pkey}"]=dict(
                    pa=round(100*pa,2), pb=round(100*pb,2),
                    gap=round(100*gap,2), lo=round(100*lo,2), hi=round(100*hi,2),
                    na=na, nb=nb,
                    ra=round(ra,2) if ra is not None else None,
                    rb=round(rb,2) if rb is not None else None)
        DID={}
        for compare,pairs in DIDS.items():
            for dim,ka,kb in pairs:
                if f"{compare}|{ka}" not in G or f"{compare}|{kb}" not in G: continue
                def grad_of(pk):
                    fix=dict(panels_for(compare))[pk]
                    (ma,sa),(mb,sb)=ends_for(compare,fix,R,E)
                    va,ga=M["pp"](ma,sa); vb,gb=M["pp"](mb,sb)
                    return va-vb, ga-gb
                va,ga=grad_of(ka); vb,gb=grad_of(kb)
                e,lo,hi=M["ci"](va-vb, ga-gb)
                DID[f"{compare}|{dim}"]=dict(est=round(100*e,2),lo=round(100*lo,2),
                                             hi=round(100*hi,2),a=ka,b=kb)
        payload["cells"][f"{o['key']}|{skey}"]=dict(
            n=M["n"], waves=len(M["waves"]), g=G, did=DID,
            or_=round(float(np.exp(M["beta_S"])),4) if np.isfinite(M["beta_S"]) else None,
            or_lo=round(float(np.exp(M["beta_S"]-1.96*M["se_S"])),4) if np.isfinite(M["beta_S"]) else None,
            or_hi=round(float(np.exp(M["beta_S"]+1.96*M["se_S"])),4) if np.isfinite(M["beta_S"]) else None)
        if done%25==0:
            el=time.time()-t0
            print(f"  {done}/{total}  {el:5.0f}s  eta {el/done*(total-done):5.0f}s  {o['key']}|{skey}", flush=True)

p=os.path.join(OUT,"gap_data.json")
json.dump(payload,open(p,"w"),separators=(",",":"))
print(f"\nwrote gap_data.json: {len(payload['cells'])} outcome-by-source models, "
      f"{os.path.getsize(p)//1024} KB, {time.time()-t0:.0f}s")
