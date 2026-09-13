"""Payload for dashboard 4 — what each news source's coefficient actually tracks.

Reads the fourteen aggregate cell files produced by paper3/data/chip50_derived/
(pvt_expanded_gradient.py, pvt_attachment_ladder.py, regime_ladder.py) and emits one small
JSON. Nothing respondent-level is read or written: every input row is already a fitted
coefficient or a survey-weighted share over thousands of people.

Three quantities can each make a position "widely held", and they are near-orthogonal across
these cells, so one model per source separates them:

    log OR = a + b_pop*pop + b_gap*gap + b_lean*lean

    pop   (own + other)/2      how common the position is overall
    gap    own - other         how much it is the RESPONDENT'S OWN side's position
    lean   Dem base - Rep base which side of politics the position sits on, absolutely

`own` is pop + gap/2, so a source that tracks its user's own party shows up as equal-signed
loadings on pop and gap in a 2:1 ratio with nothing on lean. That case is detected explicitly
rather than being read off the largest t.

Usage:  python3 build_quantities_data.py   ->  quantities.json
"""
import pandas as pd, numpy as np, statsmodels.api as sm, json, os, sys, datetime, warnings
from scipy import stats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
CELLS = os.path.abspath(os.path.join(HERE, "..", "paper3", "data", "chip50_derived"))
OUT = os.path.join(HERE, "quantities.json")

REGIMES = [
    ("PVT", "Private messaging", "group chats, WhatsApp, Messenger, texts", 7.3),
    ("DEC", "Podcasts", "podcast apps and feeds", 11.9),
    ("PB", "Partisan broadcast", "cable opinion shows, talk radio, late-night comedy", None),
    ("JS", "Mainstream news", "network and local TV news, newspapers and news sites", None),
    ("VLP", "Big social platforms", "Facebook, X, Instagram, TikTok, YouTube", 33.9),
    ("SRCH", "Search engines", "Google, Bing", None),
    ("INT", "People you know", "friends, family, coworkers", None),
]

QUANTS = [
    ("pop", "How common it is overall",
     "How many people believe it or trust them, counting everybody.",
     "A source that tracks this one goes with positions that are rare everywhere — and stops "
     "mattering once a position is something most of the country holds."),
    ("gap", "How much it is your own side's position",
     "How much more common the position is among people who share your politics than among "
     "people who don't. Measured from where the person answering stands, so the same position "
     "is 'my side's' for one party and 'their side's' for the other.",
     "A source that tracks this one goes with the positions that separate the parties. Positive "
     "means its users hold their own team's distinctive positions; negative means its users hold "
     "the positions their own team mostly doesn't."),
    ("lean", "Which side of politics it belongs to",
     "How much more common the position is among Democrats than among Republicans, regardless of "
     "who is answering. This is a fact about the position, not about the person.",
     "A source that tracks this one pulls in one political direction for everybody who uses it, "
     "Democrats and Republicans alike. That is a different thing from making people more partisan."),
]

BELIEF_LABEL = {
    "denial": "Donald Trump actually won the 2020 election",
    "FN_gmo": "Genetically modified foods have harmful effects",
    "FN_machines": "Voting machines in the 2020 election were rigged",
    "FN_cia": "A dying CIA agent confessed to a political assassination",
    "FN_turbines": "Wind turbines cause cancer",
    "FN_soros": "George Soros is secretly working against the country",
    # Two health positions rather than beliefs about a claim, but they share the shape: the
    # respondent's own position, coded 1 for the pro-vaccination answer. Listed here so the
    # label is used verbatim instead of being prefixed with "Trusts".
    "vaccine": "Has had a COVID-19 vaccine",
    "mmr": "Approves the childhood MMR mandate",
}
TRUST_LABEL = {
    "science": "scientists and researchers", "doctors": "hospitals and doctors",
    "cdc": "the CDC", "fda": "the FDA", "pharma": "pharmaceutical companies",
    "fauci": "Anthony Fauci", "trump": "Donald Trump", "biden": "Joe Biden",
    "harris": "Kamala Harris", "whitehouse": "the White House",
    "scotus": "the US Supreme Court", "musk": "Elon Musk", "fbi": "the FBI",
    "justice": "the criminal justice system", "election": "the US election system",
    "media": "the news media", "social": "social media companies", "congress": "Congress",
    "police": "the police", "military": "the military", "banks": "banks",
    "city": "your city government", "state": "your state government",
    "religion": "organized religion", "education": "colleges and universities",
}
# 2-4 waves; shown but marked. `mmr` is the extreme case -- ONE wave (W35), so its cell
# carries no wave fixed effect at all and its interval is not comparable with the rest.
THIN = {"harris", "musk", "mmr"}

def prep(rg):
    f = os.path.join(CELLS, f"{rg.lower()}_expanded_cells.csv")
    E = pd.read_csv(f)
    E["gap"] = E.own - E.other
    E["pop"] = (E.own + E.other) / 2
    E["lean"] = np.where(E.party == "Dem", E.gap, -E.gap)
    return E

def wls(E, cols):
    X = sm.add_constant(pd.DataFrame({c: E[c].values for c in cols}))
    return sm.WLS(E.logOR.values, X.values,
                  weights=1.0 / np.maximum(E.se.values ** 2, 1e-8)).fit()

def r2_of(E, col):
    return float(wls(E, [col]).rsquared)

def classify(full, solo, weak):
    """Which quantity is this source answering to? own-party is a compound case."""
    tl = abs(full["lean"]["t"])
    tmax = max(abs(full[k]["t"]) for k in ("pop", "gap", "lean"))
    if tl >= 2 and tl >= tmax - 1e-9:
        return "lean"
    if solo["own"] >= max(solo["pop"], solo["gap"], solo["lean"]):
        return "own"
    return "gap" if solo["gap"] > solo["pop"] else "pop"

READING = {
 "own": ("their own side", "Its users hold the positions their own side mostly doesn't hold — "
         "whatever those positions are, and whichever side they are on."),
 "pop": ("how rare it is everywhere", "Its users hold the positions few people anywhere hold, and it "
         "stops distinguishing anyone once a position becomes common."),
 "gap": ("their own team's positions", "Its users hold the positions that separate the two parties, "
         "on their own party's side of the divide."),
 "lean": ("one political direction", "Its users lean one way politically — the same way whether "
          "they are Democrats or Republicans."),
}

MIRROR = ["trump", "police", "military", "education", "fauci", "scotus"]

def fitline(E, col):
    m = wls(E, [col])
    return {"a": float(m.params[0]), "b": float(m.params[1]),
            "t": float(m.tvalues[1]), "r2": float(m.rsquared)}

def build():
    regimes, cells, outmeta = [], [], {}
    for rg, label, examples, occ in REGIMES:
        E = prep(rg)
        full = wls(E, ["pop", "gap", "lean"])
        coef = {}
        for i, k in enumerate(["pop", "gap", "lean"], start=1):
            coef[k] = {"b": float(full.params[i]), "se": float(full.bse[i]),
                       "t": float(full.tvalues[i]), "p": float(full.pvalues[i])}
        solo = {k: r2_of(E, k) for k in ("own", "pop", "gap", "lean")}
        tmax = max(abs(coef[k]["t"]) for k in coef)
        weak = bool(full.rsquared < 0.25 and tmax < 3.5)
        dom = classify(coef, solo, weak)

        # does the own-minus-other slope flip sign between the parties?
        md = wls(E[E.party == "Dem"], ["gap"]); mr = wls(E[E.party == "Rep"], ["gap"])
        s = E.copy(); s["rep"] = (s.party == "Rep").astype(float); s["ix"] = s.gap * s.rep
        mi = wls(s, ["gap", "rep", "ix"])
        pflip = float(mi.pvalues[3])
        dslope, rslope = float(md.params[1]), float(mr.params[1])
        flip = bool(pflip < 0.05 and np.sign(dslope) != np.sign(rslope))

        # lines the panels draw: the source against the quantity it answers to, and
        # the same source against the party gap once per party (the scissors test)
        E["own"] = E.own
        fit = fitline(E, "own" if dom == "own" else dom)
        pooled = fitline(E, "gap")
        fdem = fitline(E[E.party == "Dem"], "gap")
        frep = fitline(E[E.party == "Rep"], "gap")
        regimes.append(dict(id=rg, label=label, examples=examples, occupancy=occ,
            coef=coef, r2=float(full.rsquared), solo_r2=solo, dominant=dom, weak=weak,
            reading=READING[dom][0], sentence=READING[dom][1],
            fit=fit, fit_q=("own" if dom == "own" else dom),
            pooled_gap=pooled, fit_dem=fdem, fit_rep=frep,
            flip=dict(dem=dslope, rep=rslope, p=pflip, differs=flip,
                      t_dem=float(md.tvalues[1]), t_rep=float(mr.tvalues[1])),
            cells=int(len(E))))
        for _, r in E.iterrows():
            cells.append(dict(rg=rg, o=r.outcome, party=r.party,
                              lor=round(float(r.logOR), 5), se=round(float(r.se), 5),
                              own=round(float(r.own), 2), other=round(float(r.other), 2),
                              n=int(r.n)))
            if r.outcome not in outmeta:
                k = r.outcome
                lab = BELIEF_LABEL.get(k) or ("Trusts " + TRUST_LABEL.get(k, k))
                outmeta[k] = dict(id=k, label=lab, family=r.family, eco=r.eco,
                                  lean=round(float(r.lean), 1), thin=bool(k in THIN))

    # attachment ladder: same four rungs for every source
    ladder = []
    for rg, label, _, _ in REGIMES:
        f = os.path.join(CELLS, f"{rg.lower()}_ladder_cells.csv")
        if not os.path.exists(f): continue
        L = pd.read_csv(f)
        keep = [o for o in L.outcome.unique() if L[L.outcome == o].rung.nunique() == 4]
        Q = L[L.outcome.isin(keep)].copy()
        rungs = {}
        for rung in ("STRONG", "WEAK", "LEAN", "PURE"):
            sub = Q[Q.rung == rung]
            if len(sub) < 6: continue
            m = sm.WLS(sub.logOR.values, sm.add_constant(sub[["base"]].values),
                       weights=1.0 / np.maximum(sub.se.values ** 2, 1e-8)).fit()
            rungs[rung] = {"b": float(m.params[1]), "se": float(m.bse[1]),
                           "t": float(m.tvalues[1]), "k": int(len(sub))}
        Q["pure"] = (Q.rung == "PURE").astype(float); Q["ix"] = Q.base * Q.pure
        m = sm.WLS(Q.logOR.values, sm.add_constant(Q[["base", "pure", "ix"]].values),
                   weights=1.0 / np.maximum(Q.se.values ** 2, 1e-8)).fit()
        ladder.append(dict(id=rg, rungs=rungs, partisan=float(m.params[1]),
                           pure=float(m.params[1] + m.params[3]),
                           diff=float(m.params[3]), p=float(m.pvalues[3])))

    # `prep` output is reused by the mirror pairs below
    caseE = {rg: prep(rg) for rg, *_ in REGIMES}

    # ---- mirror pairs: private messaging, same target, two parties ----------------------
    P = caseE["PVT"]; mirror = []
    for k in MIRROR:
        sub = P[P.outcome == k]
        if len(sub) != 2: continue
        row = {"id": k, "label": (BELIEF_LABEL.get(k) or TRUST_LABEL.get(k, k))}
        for _, r in sub.iterrows():
            row[r.party] = {"base": round(float(r.own), 1),
                            "or": round(float(np.exp(r.logOR)), 3)}
        mirror.append(row)

    doc = dict(
        built=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        source="CHIP50, 15 waves carrying the news-source battery, June 2022 – May 2026",
        sample_battery="Democrats and Republicans only, leaners folded toward the side they lean to",
        sample_ladder="all respondents, split by strength of party attachment",
        quantities=[dict(id=i, label=l, what=w, means=m) for i, l, w, m in QUANTS],
        regimes=regimes, outcomes=sorted(outmeta.values(), key=lambda d: d["lean"]),
        cells=cells, ladder=ladder, mirror=mirror)
    with open(OUT, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    kb = os.path.getsize(OUT) / 1024
    print(f"wrote quantities.json  {kb:.0f} KB  "
          f"{len(regimes)} sources, {len(outmeta)} outcomes, {len(cells)} cells, {len(ladder)} ladders, "
          f"{len(mirror)} mirror pairs\n")
    print(f"  {'source':<22}{'runs on':<26}{'R2':>6}{'pop t':>9}{'gap t':>9}{'lean t':>9}  flip?")
    for r in regimes:
        fl = "yes" if r["flip"]["differs"] else "no"
        print(f"  {r['label']:<22}{READING[r['dominant']][0]:<26}{r['r2']:>6.2f}"
              f"{r['coef']['pop']['t']:>9.2f}{r['coef']['gap']['t']:>9.2f}{r['coef']['lean']['t']:>9.2f}"
              f"  {fl}{'   (weak)' if r['weak'] else ''}")

if __name__ == "__main__":
    build()
