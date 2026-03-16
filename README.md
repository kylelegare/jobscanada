# AI Exposure of the Canadian Job Market

Interactive treemap visualization of AI exposure across 516 Canadian occupations.

**[View the live site](https://kylelegare.github.io/jobscanada/)**

Inspired by [Andrej Karpathy's US version](https://karpathy.github.io/jobs/), adapted for Canada using the National Occupational Classification (NOC 2021).

## Disclaimer

"Exposure" measures how digital or automatable an occupation's core work is, as scored by an LLM. **This says nothing about what will actually happen to these occupations.** Whether jobs grow, shrink, or transform depends on demand elasticity, regulation, complementarity between human and AI work, how quickly organizations adapt, and much more. Many highly "exposed" occupations may see productivity gains rather than job losses — and some may grow as a result. Working on a computer is not inherently a risk. High exposure ≠ job loss.

## What's here

Canada's NOC 2021 classification covers 516 unit-group occupations spanning every sector of the economy. We scraped occupation profiles from Employment and Social Development Canada's OaSIS system, scored each occupation's AI exposure using an LLM, and built an interactive treemap visualization sized by employment.

## Data pipeline

1. **Scrape hierarchy** (`scrape_hierarchy.py`) — Extracts all 516 five-digit NOC unit groups from the [OaSIS hierarchy](https://noc.esdc.gc.ca/OaSIS/OaSISHierarchy), capturing NOC code, title, broad category, and TEER level.

2. **Scrape profiles** (`scrape_profiles.py`) — Downloads the full OaSIS profile for each occupation (main duties, core competencies, employment requirements) and saves as clean Markdown files in `pages/`.

3. **Download data** (`download_data.py`) — Pulls wage data from Open Canada and employment counts from StatsCan Table 14-10-0416-01.

4. **Score** (`score.py`) — Sends each occupation's Markdown description to Gemini Flash (via OpenRouter) with a scoring rubric. Each occupation gets an AI Exposure score from 0–10 with a rationale. Results cached to `scores.json`.

5. **Build site data** (`build_site_data.py`) — Merges wage stats, employment counts, and AI exposure scores into `site/data.json` for the frontend.

6. **Website** (`site/index.html`) — Interactive treemap where area = employment and color = AI exposure (green → red). Click any sector to drill down into individual occupations.

## Key files

| File | Description |
|------|-------------|
| `occupations.json` | Master list of 516 NOC occupations with code, title, category, TEER, slug |
| `occupations.csv` | Structured stats: median pay (hourly/annual), TEER level, category |
| `scores.json` | AI exposure scores (0–10) with rationales for all 516 occupations |
| `pages/` | Clean Markdown profiles for each occupation (from OaSIS) |
| `site/` | Static website (treemap visualization + data) |

## AI exposure scoring

Each occupation is scored on a single AI Exposure axis from 0 to 10, measuring how much AI could reshape that occupation's core work. The score considers both direct automation (AI performing the work) and indirect effects (AI making workers so productive that fewer may be needed).

A key signal is whether the job's work product is fundamentally digital — if the work can be done entirely from a home office on a computer, AI exposure is inherently high. Conversely, jobs requiring physical presence, manual dexterity, or real-time human interaction have a natural barrier.

| Score | Meaning | Examples |
|-------|---------|----------|
| 0–1 | Minimal | Underground miners, landscape labourers |
| 2–3 | Low | Electricians, plumbers, firefighters |
| 4–5 | Moderate | Registered nurses, retail workers, police officers |
| 6–7 | High | Teachers, managers, accountants, engineers |
| 8–9 | Very high | Software developers, paralegals, data analysts |
| 10 | Maximum | Medical transcriptionists |

Employment-weighted average exposure across all 516 occupations: **4.8/10**.

## Visualization

The main visualization is an interactive treemap where:

- **Area** of each rectangle is proportional to employment (number of jobs), sqrt-scaled
- **Color** indicates AI exposure on a green (low) to red (high) scale
- **Layout** groups occupations by NOC broad category (10 sectors)
- **Click** any sector to drill down into individual occupations
- **Hover** shows detailed tooltip with pay, employment, NOC code, TEER level, exposure score, and LLM rationale
- **Sidebar** shows total jobs, total wages, employment-weighted exposure, distribution histogram, and breakdowns by pay bracket and education level

## Data sources

- [NOC/OaSIS](https://noc.esdc.gc.ca/) — Occupation profiles and classification (ESDC)
- [Open Canada](https://open.canada.ca/) — Wage data by occupation
- [StatsCan Table 14-10-0416-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410041601) — Employment by detailed occupation
- AI scoring via [Gemini Flash](https://ai.google.dev/) through [OpenRouter](https://openrouter.ai/)
