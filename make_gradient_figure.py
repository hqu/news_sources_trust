"""Static SVG of the gradient.html forest plot, for slides and for the proposal.

Reads dashboard/data.json -- aggregates only, the same payload the page reads -- and draws the
same geometry the page draws, so the figure and the page cannot disagree. Nothing is typed by
hand: the labels, the prevalences, the odds ratios and the correlation all come out of the file.

    python3 make_gradient_figure.py [REGIME]      default PVT

Everything is oriented to the ADVERSE side, as `explorer.html` and `gradient.html` are: a trust
outcome is turned around to face the same way as a belief outcome, which replaces its prevalence
with the complement and its odds ratio with the reciprocal. That is an interpretive choice and the
caption says so.
"""
import json, math, os, sys, html

H = os.path.dirname(os.path.abspath(__file__))
REGIME = (sys.argv[1] if len(sys.argv) > 1 else "PVT").upper()
HIDDEN_OUTCOMES = {"rfk", "musk"}
HIDDEN_SOURCES = {"AICH"}
INK, MID, FAINT, HAIR, WASH, WARM = "#16181d", "#71777f", "#ccd1d6", "#e6e9ec", "#f4f7f9", "#9a3b30"

d = json.load(open(os.path.join(H, "data.json"), encoding="utf-8"))
RLAB = {r["key"]: r["label"] for r in d["meta"]["regimes"]}
REGS = [r["key"] for r in d["meta"]["regimes"] if r["key"] not in HIDDEN_SOURCES]


def points(reg):
    out = []
    for o in d["outcomes"]:
        if o["key"] in HIDDEN_OUTCOMES:
            continue
        b = o["models"]["all"]["regime"]
        e = next((x for x in b["estimates"] if x["key"] == reg), None)
        if not e:
            continue
        flip = o["direction"] == "trust"
        out.append(dict(
            label=o["label"], n=b["n"], waves=len(b.get("waves") or []),
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
r = corr([p["prev"] for p in P], [math.log(p["orr"]) for p in P])
maxW = max(p["waves"] for p in P)
maxp = max(p["prev"] for p in P)

GUT, PNUM, PBAR, BARW, PX0, PXW, RH = 246, 292, 300, 66, 392, 352, 26
lo = min([1.0] + [p["lo"] for p in P] + [1 / 1.2])
hi = max([1.0] + [p["hi"] for p in P] + [1.2])
pad = (math.log(hi) - math.log(lo)) * 0.04
lo, hi = math.exp(math.log(lo) - pad), math.exp(math.log(hi) + pad)
sx = lambda v: PX0 + (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) * PXW

TITLE, TOP = 64, 64 + 54
# PAD is a real margin, not decoration: the label column starts at x=0 and the caption ends one
# line above the bottom edge, so an unpadded figure has type touching the crop on three sides the
# moment it is dropped into a slide or a LaTeX float.
PAD = 22
W, HH = PX0 + PXW + 16, TITLE + 54 + len(P) * RH + 52 + 58
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
         f'correlation between prevalence and the log odds ratio {"+" if r >= 0 else "−"}{abs(r):.2f}</text>')
s.append(f'<text x="0" y="{TITLE + 16}" fill="{MID}" font-size="9.6" font-weight="700" letter-spacing="1.4">OUTCOME</text>')
s.append(f'<text x="{PBAR + BARW}" y="{TITLE + 16}" fill="{MID}" font-size="9.6" font-weight="700" '
         f'letter-spacing="1.4" text-anchor="end">% WHO HOLD IT</text>')
s.append(f'<text x="{PX0 + PXW / 2}" y="{TITLE + 16}" fill="{MID}" font-size="9.6" font-weight="700" '
         f'letter-spacing="1.4" text-anchor="middle">ODDS RATIO</text>')
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
s.append(f'<text x="{PX0}" y="{yb}" fill="{MID}" font-size="10.4" font-weight="600">← less likely to hold it</text>')
s.append(f'<text x="{PX0 + PXW}" y="{yb}" fill="{MID}" font-size="10.4" font-weight="600" text-anchor="end">more likely to hold it →</text>')
cap = [
    "Survey-weighted logistic regression, one per outcome, adjusted for party, education, age, income,",
    "gender, wave and every other news source. Trust items are turned around to face the same way as",
    "belief items, so “hold it” means believing the claim or distrusting the institution. † fewer than",
    "half the waves of the best-covered outcome. Cross-sectional associations, confounded with selective",
    "exposure by construction: they fix the ordering of predictors, not transmission rates.",
]
for j, line in enumerate(cap):
    s.append(f'<text x="0" y="{yb + 20 + j * 12}" fill="{MID}" font-size="9.4">{e(line)}</text>')
s.append("</g></svg>")

out = os.path.join(H, "figures", f"gradient_{REGIME.lower()}.svg")
open(out, "w", encoding="utf-8").write("\n".join(s))
print(f"wrote {os.path.relpath(out, H)}  ({len(P)} outcomes, r={r:+.3f})")
