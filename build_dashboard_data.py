"""Precompute every estimate the dashboard shows, as aggregates only.

NO ROW-LEVEL DATA LEAVES THIS SCRIPT. The output is odds ratios, intervals, sample sizes
and weighted prevalences. The dashboard reads that JSON and never sees microdata, which is
the condition for sharing it with anyone outside this machine.

One model per (outcome, predictor-level). Every regime (or every channel) is entered
JOINTLY in a single model, adjusted for party7, education, age, income, gender and wave
fixed effects. Toggling predictors in the UI therefore FILTERS THE DISPLAY of one fitted
model -- it does not re-fit. The UI says so.

The four conspiracy items are CONTROLS in every model and are no longer outcomes. That
removes the circularity that kept them out before, and it costs wave coverage: the battery
runs in 11 of the 15 model waves, so every estimate here is fitted on those 11.
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os, json, sys, warnings
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
# Display order, used by the selector and the forest plot: the editorially filtered and
# retrieval regimes first, then the platform and closed-channel ones, with the
# single-channel Decentralized regime last.
REGIMES = ["JS","PB","SRCH","AICH","VLP","PVT","INT","DEC"]
# Platform-level detail, from the pol_news2 battery. Fielded in six waves only
# (W23, 26, 27, 28, 35, 35.1), so these are estimated in their own model and must
# never be read alongside the 15-wave regime estimates as if they were nested.
# SLOT NUMBERS, NOT QUESTIONNAIRE ORDER. The questionnaire text lists this block in
# DISPLAY order, which changes between waves; the microdata use stable Qualtrics choice IDs,
# which do not. Harmonising on the questionnaire label puts "None of the above" (slot 11)
# into the Very Large Platform roll-up. Authoritative map, with three independent
# confirmations: paper3/data/chip50/pol_news2_data_slot_map.csv, and OUTLINE §"open
# problems" point 8. Slot 11 (None of the above) and slot 12 (Truth Social, unassigned in
# regime_taxonomy_v2) are deliberately excluded.
PLAT = {"pol_news2_1":("Facebook","VLP"), "pol_news2_2":("Twitter / X","VLP"),
        "pol_news2_3":("YouTube","VLP"),  "pol_news2_5":("Instagram","VLP"),
        "pol_news2_6":("Snapchat","PVT"), "pol_news2_10":("TikTok","VLP"),
        "pol_news2_4":("Reddit","CRW"),   "pol_news2_7":("Wikipedia","CRW"),
        "pol_news2_8":("Facebook Messenger","PVT"), "pol_news2_9":("WhatsApp","PVT")}
# Snapchat is PVT, not VLP: regime_taxonomy_v2.csv lists it under Private Messaging
# ("Mobile instant message app; Facebook Messenger; WhatsApp; Snapchat"), as do
# paper3/data/README.md and MODEL_NOTES sec.18. It moved with the 2026-09-06 PVT split,
# This file was the only place still calling it VLP.
REGIME_LABEL = {"JS":"Journalistic Standard","PB":"Partisan Broadcast","VLP":"Very Large Platform",
                # The regime is operationally one channel, podcasts, and the taxonomy name
                # carries a claim -- no platform gatekeeper -- that one item cannot test. The
                # pages are read by people who did not write the taxonomy, so the payload says
                # what was measured; regime_taxonomy_v2.csv keeps the taxonomy name.
                "DEC":"Podcasts","PVT":"Private Messaging","INT":"Interpersonal Ties",
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
 ("trump","pol_trust_trump","Government","Trust in Donald Trump","trust",False),
 ("whitehouse","pol_trust_white_house","Government","Trust in the White House","trust",False),
 ("scotus","pol_trust_court","Government","Trust in the US Supreme Court","trust",False),
 ("denial","trump_win","Election","Election denial — Trump won in 2020","belief",False),
 # Two health POSITIONS rather than trust targets, added 2026-09-13. Both are coded so that
 # 1 is the pro-vaccination answer, which is what `direction="trust"` means everywhere in this
 # payload: higher y is the non-adverse side, and the pages invert it to face the same way as
 # the belief items. The coding is taken from paper2/eda/diploma_divide.py unchanged --
 # vaccine_get 1,2,4,5 = "yes, n doses" (3 = No, and the codes are NOT ordinal), vac_mmr >= 4 =
 # approve or strongly approve on a 1-5 disapprove-to-approve scale.
 ("vaccine","vaccine_get","Health","Has had a COVID-19 vaccine","trust",False),
 # SINGLE WAVE (W35). It cannot carry a wave fixed effect and no wave dummy is fitted for it;
 # `n_wave_dummies` on the row is 0 and the pages print it. Marked thin the way Harris and Musk
 # are on dashboard 1.
 ("mmr","vac_mmr","Health","Approves the childhood MMR mandate","trust",False),
]
# key, claim text (matched against the codebook label), group, label, direction, default
FN_OUTCOMES = [
 ("gmo","Genetically modified foods have harmful effects","Misinformation",
  "GM foods have hidden harmful effects","belief",False),
 ("machines","Voting machines in the 2020 election were rigged","Misinformation",
  "2020 voting machines were rigged","belief",False),
 ("cia","A dying CIA agent confessed","Misinformation",
  "US agencies were behind 9/11","belief",False),
 ("turbines","Wind turbines cause cancer","Misinformation",
  "Wind turbines cause cancer","belief",False),
 ("soros","George Soros is secretly working","Misinformation",
  "Soros is destabilising the US","belief",False),
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
    fnmap={}
    for key,claim,_,_,_,_ in FN_OUTCOMES:
        # fn_labels exposes waves_with(); resolve by substring against this wave's labels
        col=next((c for c,l in FL.labels().get(str(w),{}).items()
                  if claim.lower() in l.lower()), None)
        if col and col in h: fnmap[key]=col
    havep=[c for c in PLAT if c in h]
    cols=[c for c in have+tg+list(fnmap.values())+havep+CONSP
          +["weight","party7","education_cat","income_cat_5","age","male","female"] if c in h]
    d=pd.read_csv(f,usecols=sorted(set(cols)),low_memory=False); d["wave"]=w
    for key,_,_,_,_,_ in FN_OUTCOMES:
        d["FN_"+key]=d[fnmap[key]] if key in fnmap else np.nan
    for c in PLAT:
        d[c]=(pd.to_numeric(d[c],errors="coerce").fillna(0)>0).astype(float) if c in d else np.nan
    for c in CHAN:
        d[c]=(pd.to_numeric(d[c],errors="coerce").fillna(0)>0).astype(float) if c in d else np.nan
    for rg in REGIMES:
        src=[c for c in have if CHAN[c][1]==rg]
        d[rg]=(d[src]>0).any(axis=1).astype(float) if src else np.nan
    for t in NEED:
        if t not in d: d[t]=np.nan
    for c in ["male","female"]:
        if c not in d: d[c]=np.nan
    for c in CONSP:
        if c not in d: d[c]=np.nan
    fr.append(d[["wave","weight","party7","education_cat","income_cat_5","age","male","female"]
                +CONSP+NEED+["FN_"+k for k,_,_,_,_,_ in FN_OUTCOMES]+list(CHAN)+list(PLAT)+REGIMES])
d=pd.concat(fr,ignore_index=True)
d["edu"]=d["education_cat"].map(EDU)
for c in ["weight","party7","income_cat_5","age"]: d[c]=pd.to_numeric(d[c],errors="coerce")
d["male_c"]=CC.male_from(d)
for c in CONSP: d["C_"+c]=CC.num(d[c])
CC_COLS=["C_"+c for c in CONSP]
BASE_CTRL=["party7","edu","age","income_cat_5","male_c"]
CTRL=BASE_CTRL+CC_COLS

def consp_viable(y):
    """Can this outcome afford the conspiracy controls?

    The battery runs in 11 of the 15 model waves, so conditioning on it trims most outcomes
    and DESTROYS any whose own waves barely overlap it -- trust in RFK Jr. is asked in W35,
    35.1 and 36 against a battery that stops at W35, and what survives is not a sample. Rather
    than let such an outcome vanish, it keeps the uncontrolled specification and says so on
    the row. Decided once per outcome from row counts, not per model, so a subgroup never ends
    up on a different specification from the outcome it belongs to."""
    ok = y.notna() & d["weight"].notna()
    both = (ok & d[CC_COLS].notna().all(axis=1)).sum()
    return bool(both >= 2000 and both >= 0.4*ok.sum())

# Subgroups. party7 runs 1 Strong Republican .. 7 Strong Democrat, so leaners (3 and 5)
# fold into the party they lean toward; only pure independents (4) stay Independent.
d["party3"]=np.where(d["party7"].isin([1,2,3]),"Republican",
             np.where(d["party7"].isin([5,6,7]),"Democrat",
             np.where(d["party7"]==4,"Independent",None)))
EDU4={1:"High school or less",2:"High school or less",3:"Some college",
      4:"College degree",5:"Graduate degree"}
d["edu4"]=d["edu"].map(EDU4)
STRATA=[("all","All respondents",None,None)]
for g in ["Democrat","Independent","Republican"]: STRATA.append(("party_"+g,g,"party3",g))
EDU_LEVELS=["High school or less","Some college","College degree","Graduate degree"]
for g in EDU_LEVELS:
    STRATA.append(("edu_"+g.replace(" ","_"),g,"edu4",g))
# Crossed cells: every party by education. Paper 2 §6b turns on the education gradient
# *inside* a party and on how it differs between them, so crossing only one party would
# show a gradient with nothing to compare it against. Encoded as a combined column so
# run() can filter on a single equality like every other stratum.
d["party_edu"]=np.where(d["party3"].notna()&d["edu4"].notna(),
                        d["party3"].astype(str)+" | "+d["edu4"].astype(str), None)
PARTY_ABBR={"Democrat":"dem","Independent":"ind","Republican":"rep"}
for pty,ab in PARTY_ABBR.items():
    for g in EDU_LEVELS:
        STRATA.append((f"x_{ab}_"+g.replace(" ","_"), f"{pty} · {g}", "party_edu", f"{pty} | {g}"))
print("strata:",[k for k,_,_,_ in STRATA],flush=True)
print(f"  loaded {len(d):,} rows, {d['wave'].nunique()} waves", flush=True)

def fn_series(key):
    v=CC.num(d["FN_"+key])
    return (v==1).astype(float).where(v.notna())      # rated the statement "Accurate"

def outcome_series(var):
    v=CC.num(d[var])
    if var=="trump_win": return (v>=4).astype(float).where(v.notna())
    # vaccine_get is not an ordinal scale: 1 = one dose, 2 = two doses, 4 = three, 5 = four or
    # more, and 3 = No. A >= threshold would score "No" as vaccinated, so it is membership.
    if var=="vaccine_get": return v.isin([1,2,4,5]).astype(float).where(v.notna())
    if var=="vac_mmr": return (v>=4).astype(float).where(v.notna())    # approve / strongly approve
    if var.startswith("conspiracy"): return (v>=4).astype(float).where(v.notna())  # agree / strongly agree
    return (v>=3).astype(float).where(v.notna())                                    # a lot / some

def run(y, preds, label, col=None, val=None, ctrl_set=None):
    ctrl=[c for c in (ctrl_set or CTRL)
          if not (col in ("party3","party_edu") and c=="party7")
          and not (col in ("edu4","party_edu") and c=="edu")]
    frame=d if col is None else d[d[col]==val]
    sub=frame.assign(y=(y if col is None else y[frame.index])).dropna(subset=["y","weight"]+ctrl+preds)
    if len(sub)<2000: return None
    X=pd.get_dummies(sub["wave"].astype(str),prefix="w",drop_first=True).astype(float)
    for p in preds: X[p]=sub[p].values
    for c in ctrl: X[c]=sub[c].astype(float).values
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
                "income_cat_5":"Household income (5-point)","male_c":"Male",
                "C_conspiracy_1":"Conspiracy: a few people always run things",
                "C_conspiracy_2":"Conspiracy: those who run the country are unknown",
                "C_conspiracy_3":"Conspiracy: big events controlled by secret groups",
                "C_conspiracy_4":"Conspiracy: lives controlled by secret plots"}
    ctrl_rows=[]
    for c in ctrl:
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

def build_all(y,key,ctrl_set=None):
    main_reg=[r for r in REGIMES if r!="AICH" and d[r].notna().any()]
    main_chan=[c for c in CHAN if c!="pol_news1_17" and d[c].notna().any()]
    plats=[c for c in PLAT if d[c].notna().any()]
    out={}
    for skey,slabel,col,val in STRATA:
        reg=run(y,main_reg,key,col,val,ctrl_set)
        if reg is None: continue
        chan=run(y,main_chan,key,col,val,ctrl_set); plat=run(y,plats,key,col,val,ctrl_set)
        reg_ai=run(y,[r for r in REGIMES if d[r].notna().any()],key,col,val,ctrl_set)
        chan_ai=run(y,[c for c in CHAN if d[c].notna().any()],key,col,val,ctrl_set)
        for src,dst in ((reg_ai,reg),(chan_ai,chan)):
            if src is None or dst is None: continue
            for e in src["estimates"]:
                if e["key"] in ("AICH","pol_news1_17"):
                    e=dict(e); e["restricted"]=True; e["n"]=src["n"]; e["waves"]=src["waves"]
                    dst["estimates"].append(e)
        out[skey]={"label":slabel,"regime":reg,"channel":chan,"platform":plat}
    return out

payload={"meta":{"built":pd.Timestamp.now().strftime("%Y-%m-%d"),
                 "source":"CHIP50 / Civic Health and Institutions Project",
                 "note":"Aggregated model output only. No respondent-level data is present in this file.",
                 "regimes":[{"key":k,"label":REGIME_LABEL[k],
                             "channels":[{"key":c,"label":CHAN[c][0]} for c in CHAN if CHAN[c][1]==k]}
                            for k in REGIMES],
                 "conspiracy_wording":CONSP_TEXT,
                 "platforms":[{"key":k,"label":v[0],"parent":v[1]} for k,v in PLAT.items()],
                 "strata":[{"key":k,"label":l,
                            "kind":("all" if c is None else ("party" if c=="party3" else ("cross" if c=="party_edu" else "edu")))}
                           for k,l,c,_ in STRATA]},
         "outcomes":[]}
for key,var,group,label,direction,default in OUTCOMES:
    y=outcome_series(var)
    if y.notna().sum()<2000: print(f"  skip {key}: unavailable"); continue
    cc=consp_viable(y); ctrl_set=CTRL if cc else BASE_CTRL
    # AI Chat is fielded in six waves only. Entering it in the joint model would restrict
    # EVERY outcome to those six waves (and drops Fauci entirely, whose waves predate it),
    # so the main model omits it and a supplementary model adds it on its own wave subset.
    models=build_all(y,key,ctrl_set)
    reg=models.get("all",{}).get("regime")
    if reg is None: print(f"  skip {key}: not estimable"); continue
    chan=models.get("all",{}).get("channel"); plat=models.get("all",{}).get("platform")
    # The dashboard switches on every estimable regime, so no default list is emitted.
    # Kept here in comment form because the ordering is still useful when reading output:
    #   sorted(reg["estimates"], key=lambda r: r["odds_ratio"])
    worst = []
    payload["outcomes"].append(dict(key=key,var=var,group=group,label=label,
                                    direction=direction,is_default=default,consp_control=cc,
                                    regime=reg,channel=chan,platform=plat,models=models,default_on=worst))
    print(f"  {key:<8} n={reg['n']:>7,}  prev={reg['prevalence']:5.1f}%  "
          f"conspiracy control={'yes' if cc else 'NO (exempt)'}", flush=True)

for key,claim,group,label,direction,default in FN_OUTCOMES:
    y=fn_series(key)
    if y.notna().sum()<2000: print(f"  skip {key}: unavailable"); continue
    cc=consp_viable(y); ctrl_set=CTRL if cc else BASE_CTRL
    models=build_all(y,key,ctrl_set)
    reg=models.get("all",{}).get("regime")
    if reg is None: print(f"  skip {key}: not estimable"); continue
    chan=models.get("all",{}).get("channel"); plat=models.get("all",{}).get("platform")
    worst=[]   # see the note above: the dashboard checks every estimable regime
    payload["outcomes"].append(dict(key=key,var="FN_"+key,group=group,label=label,
                                    direction=direction,is_default=default,consp_control=cc,
                                    claim_text=claim,regime=reg,channel=chan,platform=plat,
                                    models=models,default_on=worst))
    print(f"  {key:<9} n={reg['n']:>7,}  prev={reg['prevalence']:5.1f}%  "
          f"{len(reg['waves'])} waves  default_on={worst}", flush=True)

with open(os.path.join(OUT,"data.json"),"w") as f: json.dump(payload,f,indent=1)
print(f"\nwrote data.json: {len(payload['outcomes'])} outcomes, "
      f"{os.path.getsize(os.path.join(OUT,'data.json'))/1024:.0f} KB")
