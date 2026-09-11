"""Precompute every estimate the dashboard shows, as aggregates only.

NO ROW-LEVEL DATA LEAVES THIS SCRIPT. The output is odds ratios, intervals, sample sizes
and weighted prevalences. The dashboard reads that JSON and never sees microdata, which is
the condition for sharing it with anyone outside this machine.

One model per (outcome, predictor-level). Every regime (or every channel) is entered
JOINTLY in a single model, adjusted for party7, education, age, income, gender and wave
fixed effects. Toggling predictors in the UI therefore FILTERS THE DISPLAY of one fitted
model -- it does not re-fit. The UI says so.

The conspiracy scale is not used as a control anywhere here: it is an outcome in its own
right (conspiracy_1-4), and conditioning on it would be circular for those rows and would
cut the wave list from 15 to 11 for the others.
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os, json, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper2", "eda"))
import wave_rule, chip50_clean as CC
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
REGIMES = ["JS","PB","VLP","DEC","PVT","INT","SRCH","AICH"]
REGIME_LABEL = {"JS":"Journalistic Standard","PB":"Partisan Broadcast","VLP":"Very Large Platform",
                "DEC":"Decentralized","PVT":"Private Messaging","INT":"Interpersonal Ties",
                "SRCH":"Search Engine","AICH":"AI Chat"}
CONSP = ["conspiracy_1","conspiracy_2","conspiracy_3","conspiracy_4"]
CONSP_TEXT = {
 "conspiracy_1":"Even though we live in a democracy, a few people will always run things anyway",
 "conspiracy_2":"The people who really 'run' the country are not known to the voters",
 "conspiracy_3":"Big events like wars, recessions and election outcomes are controlled by small groups working in secret",
 "conspiracy_4":"Much of our lives are being controlled by plots hatched in secret places"}
EDU = {"Some High School or Less":1,"High School Graduate":2,"Some College":3,
       "College Degree":4,"Graduate Degree":5}

# outcome key -> (variable, group, label, direction) ; direction "trust" = higher is more trusting
OUTCOMES = [
 ("science","pol_trust_science","Trust in science","Trust in scientists and researchers","trust",True),
 ("cdc","pol_trust_cdc","Agencies","Trust in the CDC","trust",False),
 ("fda","pol_trust_fda","Agencies","Trust in the FDA","trust",False),
 ("doctors","pol_trust_doctors","Profession","Trust in hospitals and doctors","trust",False),
 ("pharma","pol_trust_pharma","Corporates","Trust in pharmaceutical companies","trust",False),
 ("fauci","pol_trust_fauci","Elites","Trust in Anthony Fauci","trust",False),
 ("rfk","pol_trust_rfk","Elites","Trust in Robert F. Kennedy Jr.","trust",False),
 ("musk","pol_trust_musk","Elites","Trust in Elon Musk","trust",False),
 ("consp1","conspiracy_1","Conspiracy","A few people always run things","belief",False),
 ("consp2","conspiracy_2","Conspiracy","Those who really run the country are unknown","belief",False),
 ("consp3","conspiracy_3","Conspiracy","Big events controlled by secret groups","belief",False),
 ("consp4","conspiracy_4","Conspiracy","Lives controlled by secret plots","belief",False),
 ("denial","trump_win","Election","Election denial — Trump won in 2020","belief",False),
]
NEED = sorted({v for _,v,_,_,_,_ in OUTCOMES})

print("loading waves...", flush=True)
fr=[]
for w in sorted(wave_rule.MODEL_WAVES, key=float):
    f=os.path.join(D,f"CSP_W{w}.csv")
    if not os.path.exists(f): continue
    h=set(pd.read_csv(f,nrows=0).columns)
    if "pol_news1_5" not in h: continue
    have=[c for c in CHAN if c in h]
    tg=[t for t in NEED if t in h]
    if not tg: continue
    cols=[c for c in have+tg+["weight","party7","education_cat","income_cat_5","age","male","female"] if c in h]
    d=pd.read_csv(f,usecols=cols,low_memory=False); d["wave"]=w
    for c in CHAN:
        d[c]=(pd.to_numeric(d[c],errors="coerce").fillna(0)>0).astype(float) if c in d else np.nan
    for rg in REGIMES:
        src=[c for c in have if CHAN[c][1]==rg]
        d[rg]=(d[src]>0).any(axis=1).astype(float) if src else np.nan
    for t in NEED:
        if t not in d: d[t]=np.nan
    for c in ["male","female"]:
        if c not in d: d[c]=np.nan
    fr.append(d[["wave","weight","party7","education_cat","income_cat_5","age","male","female"]
                +NEED+list(CHAN)+REGIMES])
d=pd.concat(fr,ignore_index=True)
d["edu"]=d["education_cat"].map(EDU)
for c in ["weight","party7","income_cat_5","age"]: d[c]=pd.to_numeric(d[c],errors="coerce")
d["male_c"]=CC.male_from(d)
CTRL=["party7","edu","age","income_cat_5","male_c"]
print(f"  loaded {len(d):,} rows, {d['wave'].nunique()} waves", flush=True)

def outcome_series(var):
    v=CC.num(d[var])
    if var=="trump_win": return (v>=4).astype(float).where(v.notna())
    if var.startswith("conspiracy"): return (v>=4).astype(float).where(v.notna())  # agree / strongly agree
    return (v>=3).astype(float).where(v.notna())                                    # a lot / some

def run(y, preds, label):
    sub=d.assign(y=y).dropna(subset=["y","weight"]+CTRL+preds)
    if len(sub)<2000: return None
    X=pd.get_dummies(sub["wave"].astype(str),prefix="w",drop_first=True).astype(float)
    for p in preds: X[p]=sub[p].values
    for c in CTRL: X[c]=sub[c].astype(float).values
    X=X.loc[:,X.std()>1e-9]
    m=sm.GLM(sub["y"].values,sm.add_constant(X.reset_index(drop=True)),
             family=sm.families.Binomial(),freq_weights=sub["weight"].values).fit()
    rows=[]
    for p in preds:
        if p not in m.params.index: continue
        b,se=m.params[p],m.bse[p]
        occ=sub[sub[p]==1]
        rows.append(dict(key=p, odds_ratio=float(np.exp(b)),
                         lo=float(np.exp(b-1.96*se)), hi=float(np.exp(b+1.96*se)),
                         p=float(m.pvalues[p]), n_occupying=int(sub[p].sum()),
                         pct_occupying=float(100*(occ["weight"].sum()/sub["weight"].sum()))))
    # control coefficients too, so the dashboard can print the whole fitted model rather
    # than only the terms drawn in the forest plot
    CTRL_LABEL={"party7":"Party identification (1 Strong Rep – 7 Strong Dem)",
                "edu":"Education (5-point)","age":"Age (years)",
                "income_cat_5":"Household income (5-point)","male_c":"Male"}
    ctrl_rows=[]
    for c in CTRL:
        if c not in m.params.index: continue
        b,se=m.params[c],m.bse[c]
        ctrl_rows.append(dict(key=c,label=CTRL_LABEL.get(c,c),odds_ratio=float(np.exp(b)),
                              lo=float(np.exp(b-1.96*se)),hi=float(np.exp(b+1.96*se)),
                              p=float(m.pvalues[c])))
    return dict(n=int(len(sub)), waves=sorted(sub["wave"].unique(), key=float),
                prevalence=float(100*(sub["y"]*sub["weight"]).sum()/sub["weight"].sum()),
                estimates=rows, controls=ctrl_rows,
                n_wave_dummies=int(sum(1 for c in X.columns if c.startswith("w_"))),
                llf=float(m.llf), df_model=int(m.df_model))

payload={"meta":{"built":pd.Timestamp.now().strftime("%Y-%m-%d"),
                 "source":"CHIP50 / Civic Health and Institutions Project",
                 "note":"Aggregated model output only. No respondent-level data is present in this file.",
                 "regimes":[{"key":k,"label":REGIME_LABEL[k],
                             "channels":[{"key":c,"label":CHAN[c][0]} for c in CHAN if CHAN[c][1]==k]}
                            for k in REGIMES],
                 "conspiracy_wording":CONSP_TEXT},
         "outcomes":[]}
for key,var,group,label,direction,default in OUTCOMES:
    y=outcome_series(var)
    if y.notna().sum()<2000: print(f"  skip {key}: unavailable"); continue
    # AI Chat is fielded in six waves only. Entering it in the joint model would restrict
    # EVERY outcome to those six waves (and drops Fauci entirely, whose waves predate it),
    # so the main model omits it and a supplementary model adds it on its own wave subset.
    main_reg=[r for r in REGIMES if r!="AICH" and d[r].notna().any()]
    main_chan=[c for c in CHAN if c!="pol_news1_17" and d[c].notna().any()]
    reg=run(y,main_reg,key)
    chan=run(y,main_chan,key)
    reg_ai=run(y,[r for r in REGIMES if d[r].notna().any()],key)
    chan_ai=run(y,[c for c in CHAN if d[c].notna().any()],key)
    if reg is None: print(f"  skip {key}: not estimable"); continue
    # splice the AI Chat estimate in, flagged with its own n and wave list
    for src,dst in ((reg_ai,reg),(chan_ai,chan)):
        if src is None or dst is None: continue
        for e in src["estimates"]:
            if e["key"] in ("AICH","pol_news1_17"):
                e=dict(e); e["restricted"]=True; e["n"]=src["n"]
                e["waves"]=src["waves"]; dst["estimates"].append(e)
    # which predictors to switch on by default: the most ADVERSE ones
    adverse = sorted(reg["estimates"], key=lambda r: r["odds_ratio"])
    worst = [r["key"] for r in (adverse[:3] if direction=="trust" else adverse[::-1][:3])]
    payload["outcomes"].append(dict(key=key,var=var,group=group,label=label,
                                    direction=direction,is_default=default,
                                    regime=reg,channel=chan,default_on=worst))
    print(f"  {key:<8} n={reg['n']:>7,}  prev={reg['prevalence']:5.1f}%  default_on={worst}", flush=True)

with open(os.path.join(OUT,"data.json"),"w") as f: json.dump(payload,f,indent=1)
print(f"\nwrote data.json: {len(payload['outcomes'])} outcomes, "
      f"{os.path.getsize(os.path.join(OUT,'data.json'))/1024:.0f} KB")
