# CHIP50 news-source dashboard

An interactive view of how political news source use predicts trust in science and health
institutions, conspiracy belief, and election denial. Built for collaborators who want to
explore the estimates without touching the underlying survey.

There are **five pages**:

| # | page | data | question it answers |
|---|---|---|---|
| **1** | `index.html` | `quantities.json` | **What each source actually tracks** — the landing page. A belief can be unusual in three ways that come apart here: rare everywhere, lopsided toward one party, or sitting on one side of politics. Static explanatory page for a general reader: per-regime occupancy small multiples, a coefficient grid, the flow map, four sets of small multiples (one panel per source, the party-split "scissors" test, the attachment ladder, the mirror pairs), a Simpson's-paradox panel, a 26-term plain-language glossary covering
all five pages, and a 31-entry bibliography. Opens with the flow map and a note placing it
in the two-step-flow tradition. Hover gives point identity; no other interaction. |
| **2** | `rankings.html` | `data.json` | For a given outcome, how do the news-source regimes rank? Forest plot, live multivariate model, party and diploma-divide subgroups. |
| **3** | `explorer.html` | `data.json` | How that ranking **changes with how widely the belief is held**. A prevalence-window explorer: pick outcomes, slide the window, watch the ranking change. |
| **4** | `gaps.html` | `gap_data.json` | **Who the gap belongs to.** The same associations as a difference between two groups of people, in percentage points — Democrats vs Republicans, graduates vs non-graduates, or users vs non-users of a source. |
| **5** | `gradient.html` | `data.json` | **One source at a time, against how common the position is.** A forest plot of all seventeen outcomes for a single news source, stacked rarest-first, every question shown as it was asked. Built around private messaging, whose odds ratios fall from 1.77 on the rarest position to 0.90 on the most widely held. Carries its own generality test and its own test of the mechanical alternative. |

**Navigation.** Every page opens with the same five-card `.dnav` strip, numbered 1 to 5, with the
current page marked and unlinked. The links are written at load rather than in the markup, because
each page ships served and self-contained and a link has to point at the sibling of the same kind:
`window.__linkPages()` reads whether this page's own `#payload` is inlined and appends
`_standalone` accordingly. Adding a sixth page means one `<a data-p="...">` in each of the others,
the grid column count, and the block itself on the new page — `gradient.html` keeps only the
`.dnav`, `a.xpage` and `a.chip50` rules from that block and drops its `footer.pgfoot` ones, which
it declares itself at a different size.

**Prose links between dashboards** carry `data-p` and class `xpage` rather than a literal `href`,
so the same resolver handles them and a reader who opened a standalone copy from Finder is not
sent to a page that cannot fetch its payload. Four point at dashboard 5, each from the passage it
actually follows from: `rankings.html` because it is the same forest plot with the outcome held
fixed instead of the source; `explorer.html` because it asks the same prevalence question with a
window instead of a fixed source; `index.html` from the mirror-pairs section, whose rule dashboard
5 generalises to all seventeen outcomes; and `gaps.html` because a percentage-point gap is bounded
by prevalence and an odds ratio is not.

`__linkPages` is **exposed and idempotent rather than a one-shot listener**, which `index.html`
requires: it writes its whole body from a template after `quantities.json` arrives, so a prose link
inside that template does not exist when `DOMContentLoaded` fires. It was shipping with no `href`
at all until the page called the resolver again after the injection. Any page that injects markup
containing a `[data-p]` has to do the same.

**Attribution and dating.** Every page carries a footer with the author and the date its payload
was built, read live from `meta.built` (or `built`) rather than hard-coded, so a rebuilt payload
updates the page without an HTML edit. Every visible mention of the Civic Health and Institutions
Project links to <https://www.chip50.org/>.

## Access word

All five pages sit behind a shared word. **This is a deterrent, not security.** The pages are
served from a public URL, the check runs in the reader's browser, and `data.json` and
`gap_data.json` can be requested directly without going through the dialog. It keeps unfinished
work from being stumbled on or indexed; it protects nothing. Real access control needs a server
that checks before it serves — Netlify or Vercel password protection, or Cloudflare Access.
Nothing served here is respondent-level, which is why a soft gate is adequate for now.

`explorer.html` orients every outcome to the **adverse direction** — believing the claim, or
*distrusting* the institution — and puts all eighteen on one axis, "% of the population in the
adverse state." That unification is an interpretive choice, not something the models assert, and
the page says so. It opens with a six-pane scrollytelling walkthrough of the two takeaways
(podcasts lead 15 of 18 outcomes; private messaging predicts low-prevalence claims while Very
Large Platform predicts high-prevalence ones), then hands over to free exploration: pick outcomes
individually or by family, drag a two-handled prevalence window, watch the ranking reorder.

**The slope readout switches off below five outcomes in the window.** With ten belief outcomes, a
user who narrows to three points would otherwise get a correlation near ±1 that means nothing.

`gradient.html` takes the same prevalence idea and holds the source fixed instead of the window.
One forest plot, seventeen rows, ordered by the share of adults in the position rather than by
effect size — so the ordering is imposed from outside the estimates and the staircase is something
the data either produce or do not. It also carries the two checks the claim needs, both computed
live from the same payload and both changing with the source and subgroup chosen:

- **The generality test.** The same prevalence-against-log-odds correlation for all seven sources.
  Private messaging is −0.71 against a median of −0.28, with Journalistic Standard (+0.77), Search
  Engine (+0.53) and Big social platforms (+0.26) running the other way — which is what rules out
  the odds scale, since an artifact of the scale would bend all seven the same way. Private
  messaging is **not** the steepest here: podcasts are, at −0.89.
- **The mechanical alternative.** An odds ratio has more room on a lopsided split, so a source
  could show a gradient without meaning anything. That story predicts *large* odds ratios at both
  ends, not a consistent decline in signed terms. Correlating |log OR| with distance from an even
  split gives **+0.06 for private messaging** against **+0.55 for podcasts** and +0.53 for
  interpersonal ties. This is the test that separates the two steepest slopes: podcasts are
  steeper and largely explained by lopsidedness, private messaging shallower and not explained by
  it at all. The quantity is invariant to reorientation — flipping `p → 100−p` leaves `|p−50|`
  alone and `OR → 1/OR` leaves `|log OR|` alone — so it is the one number on the page that does
  not move when the orientation button does.

The gradient holds in most subgroups but not all: −0.80 among Democrats, −0.70 among Republicans,
−0.88 among respondents with a high school education or less, and **+0.02 among graduate-degree
holders**, where it disappears. That last cell is the honest limit of the claim and the page shows
it without comment.

### Orientation

**The page shows every question as it was asked.** The percentage beside a row is the share who
gave that answer and the odds ratio is for giving it, so `Trust in Donald Trump` carries the 39.0%
who do. The cost is that the horizontal axis means "more likely to answer this way" rather than one
substantive thing, since the affirmative answer is agreement on a belief item and trust on a trust
item.

*Turned to the adverse side* is the alternative, and it is the convention `explorer.html` uses:
trust items face the same way as belief items, which buys a single-meaning axis at the price of an
interpretive choice the models do not make. Pressing it takes private messaging from −0.71 to
−0.83 and moves it from second-steepest to steepest, so **how much of the headline the orientation
is carrying is itself visible on the page**.

**Reversing an outcome renames its row**, which is where this page differs from `explorer.html`.
The explorer can keep the native name because its axis is labelled "% of the population in the
adverse state" and the number is never beside the label; a forest plot puts them on one line, so
"Trust in Donald Trump — 61.0%" reads as 61% trusting him when 39% do. `labelFor()` turns `Trust in
X` into `Distrust of X`, carries written-out labels for the two outcomes that are not
trust-in-a-target (`vaccine`, `mmr`), and prefixes anything that matches neither with
`[NOT REVERSED]` so a new trust outcome fails loudly rather than silently. `mmr` cannot be
shortened to "Opposes the childhood MMR mandate": `vac_mmr >= 4` is approve or strongly approve, so
its complement contains the neutral midpoint, and calling that opposition is the same error as
scoring "neither agree nor disagree" as election denial. The left gutter is sized for that label in
both orientations so the plot does not reflow when the button is pressed, and
`make_gradient_figure.py` carries the same map and the same fallback. That
button is not decoration: the correlation falls from −0.83 to −0.71 when the trust items face their
original way, so the orientation does part of the work and the page should let a reader see how
much.

## Running it

**Just open `index_standalone.html`** (or `explorer_standalone.html`, or `gaps_standalone.html`). It has the data built in, needs no server, and works
from a double-click or as an email attachment. That is the file to send to collaborators.

`index.html` + `data.json` is the version to use while iterating — it reads the JSON at load
time, so rebuilding the data does not require re-embedding. It needs a server, because
browsers block a `file://` page from reading a sibling file:

    python3 -m http.server 8000

After rebuilding a payload, regenerate the shareable copies:

    python3 embed_data.py       # index_standalone.html
    python3 embed_explorer.py   # explorer_standalone.html
    python3 embed_gaps.py       # gaps_standalone.html
    python3 embed_gradient.py   # gradient_standalone.html

`gap_data.json` comes from its own build, which fits one model per outcome-by-source rather than
one per outcome, and takes about ten minutes:

    python3 build_gap_data.py

No external dependencies, no CDN, no build step beyond that.

## What is in data.json

**Aggregated model output only.** No respondent-level data is present in this file, and none
is required to run the dashboard. That is a hard condition of sharing it: the CHIP50
microdata never leaves the analysis machine.

Each outcome carries two fitted models — one with the eight news-source **regimes** entered
jointly, one with the fourteen individual **channels** entered jointly — plus, for each
predictor, an odds ratio, a 95% interval, a p-value, an unweighted occupancy count and a
weighted occupancy share.

## Reading it correctly

- **Toggling a source filters the display of an already-fitted model. It does not re-fit.**
  Every predictor at the chosen level was in the model whether or not it is shown.
- Models are survey-weighted logistic regressions adjusted for party identification,
  education, age, household income, gender and wave fixed effects.
- **Two things rest on 6 of the 15 waves**, and both are marked in the plot. The named
  platforms — Facebook, Reddit, WhatsApp and the rest — because only 6 waves list platforms
  individually; the other 9 offer just the generic category "a social media website or app".
  And AI Chat, because that item was added to the questionnaire partway through the series.
  Putting either in the main model would drag every outcome down to those 6 waves, so each is
  fitted separately. Of the two, only the named platforms are currently drawn: see *Hidden
  sources* below.
- Trust outcomes are coded "a lot" or "some"; conspiracy items "agree" or "strongly agree";
  election denial is agreement that Trump would have won a fairly counted 2020 election.
- Two **health positions** were added 2026-09-13, coded exactly as `paper2/eda/diploma_divide.py`
  codes them. `vaccine` is `vaccine_get` in {1, 2, 4, 5} — at least one dose of a COVID-19
  vaccine. The codes are *not* ordinal: 3 is "No" and sits between "two doses" and "three
  doses", so this is set membership and a `>=` threshold would be wrong. 13 waves. `mmr` is
  `vac_mmr >= 4` — approve or strongly approve of the childhood MMR mandate, on a 1-5
  disapprove-to-approve scale. **W35 only**, so its model carries no wave fixed effect; the
  page prints "0 wave dummies" on the row rather than hiding it. Both are `direction: "trust"`,
  which in this payload means only that 1 is the non-adverse answer.
- These are **cross-sectional associations confounded with selective exposure by
  construction**. They fix the ordering of predictors, not transmission rates, and nothing
  here identifies a causal effect of using a channel.

## Subgroups

Subgroups are chosen from a 4 x 5 grid: party down the side, education across the top.
Every cell is one click.

|  | All education | HS or less | Some college | College | Graduate |
|---|---|---|---|---|---|
| **All parties** | everyone | education alone | | | |
| **Democrat** | party alone | crossed | crossed | crossed | crossed |
| **Independent** | party alone | crossed | crossed | crossed | crossed |
| **Republican** | party alone | crossed | crossed | crossed | crossed |

The top-left cell is every respondent, the top row is education on its own, the left column
is party on its own, and the twelve interior cells cross the two. Leaners fold into the
party they lean toward; only pure independents are Independent.

One cell is active at a time, so there is always exactly one forest plot. Cells thin out
toward the bottom right — Independents holding a graduate degree is the smallest at about
6,000 against 177,000 for Democrats overall — and the count is printed on every cell.

Every subgroup is its own fitted model rather than an interaction term, and the variables
defining it leave the control set inside it: a party model drops party, an education model
drops education, a crossed model drops both.

## Defaults

On load the outcome is trust in scientists, with the three regimes predicting the *lowest*
trust switched on. Selecting any further outcome switches on its three most adverse
regimes — lowest odds for a trust outcome, highest for conspiracy and denial.

## Regimes

| | |
|---|---|
| Journalistic Standard | network and local TV, print, news sites, community papers |
| Partisan Broadcast | cable news, talk radio, late-night comedy |
| Big social platforms | social media |
| Decentralized | podcasts |
| Private Messaging | messaging apps |
| Interpersonal Ties | friends and family |
| Search Engine | search |
| AI Chat | AI chatbots (asked in 6 of the 15 waves) — **hidden, see below** |

Semi-Public Messaging and Crowdsourced are in the taxonomy but are not fielded in the
24-hour battery, so they cannot appear here.

### Hidden sources

AI Chat is estimated and kept in every payload, and hidden from all five pages at the
rendering layer. Each page declares a `HIDDEN_SOURCES` array of regime keys next to its
existing `HIDDEN_OUTCOMES` array and filters the loaded data through it once, before any
surface reads it — `rankings.html` also strips the regime's channel out of the question
list, `explorer.html` drops it from `REG`, `gaps.html` from `meta.sources` and
`meta.regimes`. `index.html` never carried it: `quantities.json` has seven regimes. Figure 1
forks the same way, through the `dashboard` variant of `paper3/figures/make_flow_map.py`,
which names the lane Search Engine alone where the proposal names it Search Engine · AI
Chat.

Emptying the arrays brings the regime back everywhere. The prose counts are the one thing
that does not follow automatically: "all seven news-source regimes" in `rankings.html`,
"7 kinds of news source" in `explorer.html`, "two of the seven" and "the other six" in
`gradient.html`, and the one-versus-two short-wave sentence in the `rankings.html` footnote all
go back to their eight-regime wording. `gradient.html` reads `HIDDEN_SOURCES` in one place, where
it builds `REG` from `meta.regimes`, and every chip, table row and median on the page follows from
that array.

## Rebuilding

    python3 build_dashboard_data.py

Reads `~/CHIP50_restricted/`, writes `data.json`. Requires the analysis helpers in
`../paper2/eda/` (`wave_rule.py`, `chip50_clean.py`).

Renamed 2026-09-13: the page that was `quantities.html` is now `index.html` and is the default
landing page; the forest plot that was `index.html` is now `rankings.html`. `embed_data.py` became
`embed_rankings.py` and `embed_quantities.py` became `embed_index.py`. Payload filenames are
unchanged, so `index.html` still fetches `quantities.json`.

    python3 build_quantities_data.py

Different input: this one reads **no microdata at all**. It takes the fourteen already-aggregated
cell files in `../paper3/data/chip50_derived/` (`*_expanded_cells.csv`, `*_ladder_cells.csv`,
produced there by `regime_ladder.py`) and writes `quantities.json` — seven sources, 32
outcomes, 448 fitted cells. **`mmr` is not among them.** W35 is its only wave and W35 carries
`conspiracy_1`-`conspiracy_4` as columns that are 100% null, so the conspiracy controls in
`regime_ladder.py` drop every row. That file has no conspiracy-exempt path the way
`build_dashboard_data.py` and `build_gap_data.py` do, and adding one would pool a
differently-controlled cell into a second stage where nothing else is — so `mmr` appears on
dashboards 2, 3 and 4 and not on dashboard 1. Every number on `quantities.html` is generated from that file; none is
typed by hand.

    python3 embed_quantities.py

Inlines the payload into `index_standalone.html`, and base64-inlines
`figures/information_flow_map_dashboard.png` so the standalone copy carries the figure too.

    python3 make_gradient_figure.py [REGIME] [--adverse]

Reads `data.json` and writes `figures/gradient_<regime>[_adverse].svg` — a static, self-contained
copy of dashboard 5's forest plot for slides and for the proposal, defaulting to `PVT` as asked. It
redraws the page's geometry from the same payload rather than screenshotting it, so the figure and
the page cannot drift apart, and every label, prevalence, odds ratio and correlation in it is read
from the file. Four are checked in: `gradient_pvt.svg` (as asked, r = −0.71), `gradient_dec.svg`
(−0.89, steeper but explained by lopsidedness), `gradient_srch.svg` (+0.53, the clearest
counter-example) and `gradient_pvt_adverse.svg` (−0.83, the same source under the other
orientation).

That file is the **dashboard variant** of figure 1. One source,
`../paper3/figures/make_flow_map.py`, emits two PNGs: run it bare for the proposal's
`information_flow_map.png`, which says *Very Large Platform*, and with the argument
`dashboard` for this one, which says *Big social platforms*. The term is a DSA designation
in the proposal and jargon here; other lanes can be forked the same way by adding a key
to `LBL` in that script.
