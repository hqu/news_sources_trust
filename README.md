# CHIP50 news-source dashboard

An interactive view of how political news source use predicts trust in science and health
institutions, conspiracy belief, and election denial. Built for collaborators who want to
explore the estimates without touching the underlying survey.

## Running it

**Just open `index_standalone.html`.** It has the data built in, needs no server, and works
from a double-click or as an email attachment. That is the file to send to collaborators.

`index.html` + `data.json` is the version to use while iterating — it reads the JSON at load
time, so rebuilding the data does not require re-embedding. It needs a server, because
browsers block a `file://` page from reading a sibling file:

    python3 -m http.server 8000

After rebuilding `data.json`, regenerate the shareable copy:

    python3 embed_data.py

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
- **AI Chat is fielded in six waves only.** Including it in the main model would restrict
  every outcome to those six waves, so it is estimated separately and marked `6 waves`.
- Trust outcomes are coded "a lot" or "some"; conspiracy items "agree" or "strongly agree";
  election denial is agreement that Trump would have won a fairly counted 2020 election.
- These are **cross-sectional associations confounded with selective exposure by
  construction**. They fix the ordering of predictors, not transmission rates, and nothing
  here identifies a causal effect of using a channel.

## Defaults

On load the outcome is trust in scientists, with the three regimes predicting the *lowest*
trust switched on. Selecting any further outcome switches on its three most adverse
regimes — lowest odds for a trust outcome, highest for conspiracy and denial.

## Regimes

| | |
|---|---|
| Journalistic Standard | network and local TV, print, news sites, community papers |
| Partisan Broadcast | cable news, talk radio, late-night comedy |
| Very Large Platform | social media |
| Decentralized | podcasts |
| Private Messaging | messaging apps |
| Interpersonal Ties | friends and family |
| Search Engine | search |
| AI Chat | AI chatbots (six waves) |

Semi-Public Messaging and Crowdsourced are in the taxonomy but are not fielded in the
24-hour battery, so they cannot appear here.

## Rebuilding

    python3 build_dashboard_data.py

Reads `~/CHIP50_restricted/`, writes `data.json`. Requires the analysis helpers in
`../paper2/eda/` (`wave_rule.py`, `chip50_clean.py`).
