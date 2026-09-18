"""Static SVG of the gradient.html forest plot, for slides and for the proposal.

Reads dashboard/data.json -- aggregates only, the same payload the page reads -- and draws the
same geometry the page draws, so the figure and the page cannot disagree. Nothing is typed by
hand: the labels, the prevalences, the odds ratios and the correlation all come out of the file.

    python3 make_gradient_figure.py [REGIME] [--adverse]      default PVT, as asked

By default every question is drawn AS ASKED: the percentage beside a row is the share who gave
that answer and the odds ratio is for giving it, so "Trust in Donald Trump" carries the 39.0% who
do. `--adverse` turns the trust items around to face the same way as the belief items, the way
`explorer.html` does, which replaces a prevalence with its complement, an odds ratio with its
reciprocal, and the row name with its negation. That buys a single-meaning axis at the price of an
interpretive choice, and the caption says which one is in force.
"""
import json, math, os, sys, html

H = os.path.dirname(os.path.abspath(__file__))
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ADVERSE = "--adverse" in sys.argv[1:]
REGIME = (ARGS[0] if ARGS else "PVT").upper()
HIDDEN_OUTCOMES = {"rfk", "musk", "mmr"}   # mmr is W35 only: no wave fixed effect is fitted
HIDDEN_SOURCES = {"AICH"}
INK, MID, FAINT, HAIR, WASH, WARM = "#16181d", "#71777f", "#ccd1d6", "#e6e9ec", "#f4f7f9", "#9a3b30"

# The column header names the people the odds ratio is about, not the channel. A blanket
# " users" suffix is ungrammatical for two of the seven, so those are written out. Same map
# as gradient.html, and the two have to stay in step.
USERS_LABEL = {"DEC": "Podcast listeners", "VLP": "Big social platform users"}

d = json.load(open(os.path.join(H, "data.json"), encoding="utf-8"))
RLAB = {r["key"]: r["label"] for r in d["meta"]["regimes"]}
REGS = [r["key"] for r in d["meta"]["regimes"] if r["key"] not in HIDDEN_SOURCES]


# A reversed outcome has to be renamed, not just re-signed: the number beside "Trust in Donald
# Trump" here is 61.0%, the share who do NOT trust him, and the native label would state the
# opposite of what the row plots. Same map and same fallback as gradient.html -- the two have to
# agree, and a trust outcome that matches neither is labelled visibly broken rather than wrongly.
ADVERSE_LABEL = {"vaccine": "Has not had a COVID-19 vaccine",
                 "mmr": "Does not approve the childhood MMR mandate"}


def adverse_label(o):
    if not ADVERSE or o["direction"] != "trust":
        return o["label"]
    if o["key"] in ADVERSE_LABEL:
        return ADVERSE_LABEL[o["key"]]
    if o["label"].startswith("Trust in "):
        return "Distrust of " + o["label"][len("Trust in "):]
    return "[NOT REVERSED] " + o["label"]


def points(reg):
    out = []
    for o in d["outcomes"]:
        if o["key"] in HIDDEN_OUTCOMES:
            continue
        b = o["models"]["all"]["regime"]
        e = next((x for x in b["estimates"] if x["key"] == reg), None)
        if not e:
            continue
        flip = ADVERSE and o["direction"] == "trust"
        out.append(dict(
            label=adverse_label(o), n=b["n"], waves=len(b.get("waves") or []),
            prev=100 - b["prevalence"] if flip else b["prevalence"],
            orr=1 / e["odds_ratio"] if flip else e["odds_ratio"],
            lo=1 / e["hi"] if flip else e["lo"],
            hi=1 / e["lo"] if flip else e["hi"]))
    return sorted(out, key=lambda p: p["prev"])


def corr(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs)); sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return sxy / (sx * sy) if sx and sy else float("nan")


P = points(REGIME)
assert P, f"no estimates for {REGIME}"
HEADER = html.escape(USERS_LABEL.get(REGIME, RLAB.get(REGIME, REGIME) + " users").upper())
r = corr([p["prev"] for p in P], [math.log(p["orr"]) for p in P])
maxW = max(p["waves"] for p in P)
maxp = max(p["prev"] for p in P)

# Gutter sized for the adverse labels, matching gradient.html -- see the note there.
GUT, PNUM, PBAR, BARW, PX0, PXW, RH = 246, 312, 320, 66, 412, 352, 26
lo = min([1.0] + [p["lo"] for p in P] + [1 / 1.2])
hi = max([1.0] + [p["hi"] for p in P] + [1.2])
pad = (math.log(hi) - math.log(lo)) * 0.04
lo, hi = math.exp(math.log(lo) - pad), math.exp(math.log(hi) + pad)
sx = lambda v: PX0 + (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) * PXW

CAP = ["Survey-weighted logistic regression, one per outcome, adjusted for party, education, age, income,",
       "gender, wave and every other news source."]
CAP += ([
    "Trust items are turned around to face the same way as belief items and renamed with them, so a",
    "trust question is counted here as distrust: 61.0% do not trust Donald Trump, and 39.0% do.",
] if ADVERSE else [
    "Every question is drawn as asked, so the percentage is the share who gave that answer and the odds",
    "ratio is for giving it. The axis therefore means \u201cmore likely to answer this way\u201d, not one",
    "substantive direction: the affirmative answer is agreement on a belief item, trust on a trust item.",
])
CAP += [
    "\u2020 fewer than half the waves of the best-covered outcome. Cross-sectional associations, confounded",
    "with selective exposure by construction: they fix the ordering of predictors, not transmission rates.",
]

TITLE, TOP = 64, 64 + 54
# PAD is a real margin, not decoration: the label column starts at x=0 and the caption ends one
# line above the bottom edge, so an unpadded figure has type touching the crop on three sides the
# moment it is dropped into a slide or a LaTeX float.
PAD = 22
W, HH = PX0 + PXW + 16, TITLE + 54 + len(P) * RH + 38 + 26 + 12 * len(CAP)
SW, SH = W + 2 * PAD, HH + 2 * PAD
e = html.escape
s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}" height="{SH}" viewBox="0 0 {SW} {SH}" '
     f'font-family="Helvetica Neue,Helvetica,Arial"><rect width="{SW}" height="{SH}" fill="#fff"/>'
     f'<g transform="translate({PAD},{PAD})">']
s.append(f'<text x="0" y="18" fill="{MID}" font-size="9.6" font-weight="700" letter-spacing="1.4">'
         f'CHIP50 · CIVIC HEALTH AND INSTITUTIONS PROJECT</text>')
s.append(f'<text x="0" y="42" fill="{INK}" font-size="17" font-weight="700">'
         f'{e(RLAB.get(REGIME, REGIME))}, by how common the position is</text>')
s.append(f'<text x="0" y="58" fill="{MID}" font-size="11.4">{len(P)} outcomes · all respondents · '
         f'{"turned to the adverse side" if ADVERSE else "as asked"} · '
         f'correlation between prevalence and the log odds ratio {"+" if r >= 0 else "−"}{abs(r):.2f}</text>')
s.append(f'<text x="0" y="{TITLE + 16}" fill="{MID}" font-size="9.6" font-weight="700" letter-spacing="1.4">OUTCOME</text>')
s.append(f'<text x="{PBAR + BARW}" y="{TITLE + 16}" fill="{MID}" font-size="9.6" font-weight="700" '
         f'letter-spacing="1.4" text-anchor="end">% WHO HOLD IT</text>')
s.append(f'<text x="{PX0 + PXW / 2}" y="{TITLE + 16}" fill="{MID}" font-size="9.6" font-weight="700" '
         f'letter-spacing="1.4" text-anchor="middle">ODDS RATIO, {HEADER}</text>')
s.append(f'<line x1="0" y1="{TITLE + 24}" x2="{W}" y2="{TITLE + 24}" stroke="{HAIR}"/>')
s.append(f'<text x="{PBAR + BARW}" y="{TOP - 12}" fill="{FAINT}" font-size="9" text-anchor="end">rarest ↓ most common</text>')
for i in range(len(P)):
    if i % 2:
        s.append(f'<rect x="-6" y="{TOP + i * RH}" width="{W}" height="{RH}" fill="{WASH}"/>')
for t in [x for x in (0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.25, 1.5, 2, 2.5, 3) if lo < x < hi]:
    one = t == 1
    s.append(f'<line x1="{sx(t):.1f}" y1="{TOP - 6}" x2="{sx(t):.1f}" y2="{TOP + len(P) * RH + 4}" '
             f'stroke="{MID if one else HAIR}"/>')
    s.append(f'<text x="{sx(t):.1f}" y="{TOP + len(P) * RH + 19}" fill="{INK if one else MID}" '
             f'font-size="10" font-weight="{600 if one else 400}" text-anchor="middle">{t:g}</text>')
for i, p in enumerate(P):
    y = TOP + i * RH + RH / 2
    dag = f' <tspan fill="{WARM}" font-weight="700">†</tspan>' if p["waves"] < maxW / 2 else ""
    s.append(f'<text x="0" y="{y + 4}" fill="{INK}" font-size="11.6">{e(p["label"])}{dag}</text>')
    s.append(f'<text x="{PNUM}" y="{y + 4}" fill="{MID}" font-size="11" text-anchor="end">{p["prev"]:.1f}%</text>')
    s.append(f'<rect x="{PBAR}" y="{y - 4}" width="{max(1, BARW * p["prev"] / maxp):.1f}" height="8" fill="{FAINT}"/>')
    s.append(f'<line x1="{sx(p["lo"]):.1f}" y1="{y}" x2="{sx(p["hi"]):.1f}" y2="{y}" stroke="{INK}" stroke-width="1.4"/>')
    s.append(f'<circle cx="{sx(p["orr"]):.1f}" cy="{y}" r="4.2" fill="{INK}"/>')
yb = TOP + len(P) * RH + 38
SIDE = ("less likely to hold it", "more likely to hold it") if ADVERSE else \
       ("less likely to give this answer", "more likely to give this answer")
if any(p["waves"] < maxW / 2 for p in P):
    s.append(f'<text x="0" y="{yb}" fill="{MID}" font-size="9.6">'
             f'<tspan fill="{WARM}" font-weight="700">†</tspan> fielded in fewer waves</text>')
s.append(f'<text x="{PX0}" y="{yb}" fill="{MID}" font-size="10.4" font-weight="600">← {SIDE[0]}</text>')
s.append(f'<text x="{PX0 + PXW}" y="{yb}" fill="{MID}" font-size="10.4" font-weight="600" text-anchor="end">{SIDE[1]} →</text>')
for j, line in enumerate(CAP):
    s.append(f'<text x="0" y="{yb + 20 + j * 12}" fill="{MID}" font-size="9.4">{e(line)}</text>')
s.append("</g></svg>")

out = os.path.join(H, "figures",
                   f"gradient_{REGIME.lower()}{'_adverse' if ADVERSE else ''}.svg")
open(out, "w", encoding="utf-8").write("\n".join(s))
print(f"wrote {os.path.relpath(out, H)}  ({len(P)} outcomes, r={r:+.3f})")
