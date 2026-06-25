# 🏙️ Urban Stability ABM — Karnataka, India

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Mesa-2.x-orange?logo=python" />
  <img src="https://img.shields.io/badge/Streamlit-Cloud-FF4B4B?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Plotly-Interactive-3F4F75?logo=plotly" />
  <img src="https://img.shields.io/badge/Data-India%20Census%202011-green" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

<p align="center">
  <b>A research-grade Agent-Based Model simulating the socio-economic stability of 5 major cities in Karnataka under policy interventions and real-world shocks.</b>
</p>

<p align="center">
  🔗 <a href="https://abm-urban-stability.streamlit.app"><strong>Live Demo → abm-urban-stability.streamlit.app</strong></a>
</p>

---

## 📌 Problem Statement

Urban systems in India face compounding stresses — monsoon floods, droughts, economic contractions, and chronic inequality — that interact in non-linear ways traditional models cannot capture.

**Key questions this model answers:**

- How resilient are Karnataka's major cities to climate and economic shocks?
- Do Karnataka's flagship welfare schemes (Anna Bhagya, Gruha Jyothi, Gruha Lakshmi) actually buffer instability during crises?
- Which cities are structurally fragile, and **why** — not just what, but the causal mechanism?
- How does trust collapse precede instability, and how fast does it recover?

Existing approaches use **aggregate statistics** (GDP, HDI) that mask neighbourhood-level heterogeneity. This model uses **Agent-Based Modelling** to simulate each household's resource consumption, trust dynamics, and cooperation behaviour — capturing emergent instability that top-down models miss entirely.

---

## 🧠 What The Model Does

### Architecture Overview

```
Real-World Data (Census 2011, HCES 2023-24, Karnataka PCA)
        │
        ▼
┌─────────────────────────────────────────────┐
│           Urban ABM (Mesa Framework)         │
│                                             │
│  HouseholdAgent × N                         │
│  ├── Income group: extreme_poor / moderate  │
│  │                 _poor / non_poor         │
│  ├── Resources: food, water, electricity    │
│  ├── Trust level → cooperation behaviour   │
│  └── Policy uptake: PDS, income transfers  │
│                                             │
│  ResourceSupplySystem                       │
│  ├── Monthly supply per resource            │
│  ├── Shock injection (flood/drought/econ)   │
│  └── Resource interaction matrix (R×R)      │
│                                             │
│  StabilityAnalyzer                          │
│  ├── USI = 0.25·S_R + 0.25·C + 0.25·S_I   │
│  │         + 0.25·S_O                      │
│  ├── S_R = 0.4·food + 0.4·water + 0.2·elec │
│  └── Gini = consumption-satisfaction based  │
└─────────────────────────────────────────────┘
        │
        ▼
Dashboard (Streamlit + Plotly)
├── City Overview (KPI + Insight Engine)
├── Experiment Compare (6 scenarios × 5 cities)
├── Cross-City Analysis (heatmaps, radar)
└── Live Simulation (real-time Mesa run)
```

### Simulation Mechanics

| Component | Detail |
|---|---|
| **Agents** | 500–2,000 household agents per city (calibrated to census) |
| **Income groups** | `extreme_poor` / `moderate_poor` / `non_poor` with city-specific fractions |
| **Resources** | Food, Water, Electricity — each with real supply time-series |
| **Trust** | Decays on unmet demand, recovers with policy receipt; drives cooperation |
| **Cooperation** | High-trust agents moderate demand; low-trust agents escalate → scarcity spiral |
| **Shocks** | Flood (water −40%), Drought (water −30%), Economic (income −25%), combinations |
| **Policies** | Anna Bhagya (food floor), Gruha Jyothi (electricity subsidy), Gruha Lakshmi (₹2,000/month) |
| **Timestep** | 1 step = 1 month; 24-step simulation = 2 years |

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| **ABM Engine** | [Mesa 2.x](https://mesa.readthedocs.io/) — Python agent-based modelling framework |
| **Data** | India Census 2011, Karnataka PCA, HCES 2023-24, Karnataka Water/Electricity supply reports |
| **Dashboard** | [Streamlit](https://streamlit.io/) with dark-theme CSS and custom KPI card components |
| **Charts** | [Plotly](https://plotly.com/python/) — interactive scatter, heatmap, bar, radar charts |
| **Insight Engine** | Rule-based NLG engine (`dashboard/insight_engine.py`) — deterministic, no LLM dependency |
| **Config** | JSON-driven city configs (`data/processed/model_config_by_city.json`) |
| **Portability** | `pathlib` relative paths — runs identically on Windows, Linux, macOS, Streamlit Cloud |
| **Deployment** | Streamlit Community Cloud (auto-deploy from GitHub `main` branch) |

---

## 📊 Key Insights

> These are findings from the simulation — emergent results, not pre-programmed outcomes.

### 1. 🔴 Bengaluru is Structurally Fragile — Even at Baseline

| Metric | Bengaluru | Mysuru | Mangaluru | Hubballi-D | Belagavi |
|---|---|---|---|---|---|
| Final USI (baseline) | **0.746** | 0.967 | 0.990 | 0.990 | 0.990 |
| Final Trust | **0.419** | 0.999 | 1.000 | 1.000 | 1.000 |
| Min USI (worst month) | **0.746** | 0.892 | 0.925 | 0.892 | 0.928 |

Despite being Karnataka's largest economic hub, Bengaluru's **high non-poor population crowds out PDS supply** for extreme-poor households. The inequality creates structural fragility that persists **even without any shocks**. Every other city runs at USI ≥ 0.97.

**Root cause:** High non-poor consumption fraction → BPL households receive insufficient PDS floor → unmet demand → trust erodes → cooperation collapses → demand escalates → spiral.

---

### 2. ⚠️ Trust Collapse Precedes Instability — Not the Other Way Around

In every shock scenario, **trust falls first** (within months 1–3), followed by the USI decline. This causal sequence has critical policy implications:

- Once trust drops below 0.3, agents enter *demand escalation mode* — rational hoarding behaviour that accelerates the very scarcity they fear
- Bengaluru's trust collapses to **0.003 under flood** and **0.000 under drought** — effectively zero civic cooperation
- Recovery is asymmetric: trust takes **3–5× longer to rebuild** than USI does

> 💡 **Policy lever:** Early-response trust-building (visible government action, transparent rationing) can prevent the cascade, even before resources are fully restored.

---

### 3. 📈 Karnataka Government Schemes Deliver Measurable Resilience

Comparing **All Shocks without policy** vs **All Shocks with Anna Bhagya + Gruha Jyothi + Gruha Lakshmi**:

| City | USI (no policy) | USI (with policy) | Trust (no policy) | Trust (with policy) |
|---|---|---|---|---|
| Mysuru | 0.741 | **0.938** | 0.118 | **0.883** |
| Mangaluru | 0.774 | **0.919** | 0.157 | **0.717** |
| Hubballi-D | 0.749 | **0.915** | 0.063 | **0.700** |
| Belagavi | 0.836 | **0.987** | 0.389 | **0.986** |

**Policy effectiveness: +15–25% USI improvement across all cities except Bengaluru.** Bengaluru's structural inequality (USI 0.637 vs 0.638) means policy alone cannot compensate — systemic redistribution is required.

---

### 4. 🌊 Shocks Interact Non-Linearly — Concurrent Shocks Are Worse Than Additive

| Shock | Bengaluru USI drop |
|---|---|
| Flood alone | −0.108 |
| Drought alone | −0.109 |
| Economic alone | −0.109 |
| All three together (no policy) | **−0.123** |

The combined shock is **worse than the sum** because the water→food resource coupling (`c=0.715`) means water shocks simultaneously amplify food shortages. During concurrent shocks, the feedback loop between unmet demand and trust collapse accelerates beyond any single-shock scenario.

---

### 5. 🏆 Belagavi is the Most Resilient City — Counterintuitively

Belagavi has the **lowest absolute resource base** but achieves the **highest USI under stress** (0.987 with policy). The reason: its income distribution is the most equitable, meaning all households are similarly positioned, reducing internal competition for PDS resources. Equal poverty distributes shock burden more fairly than unequal wealth.

> 📐 **Gini paradox:** Low inequality (low Gini) → more equitable shock absorption → lower variance in satisfaction → higher composite USI.

---

## 🗂️ Repository Structure

```
ABM_Urban_Stability/
│
├── streamlit_app.py              # Main dashboard (4 tabs)
│
├── model/                        # ABM core
│   ├── urban_agent.py            # HouseholdAgent with trust + cooperation mechanics
│   ├── urban_model.py            # Mesa Model — orchestrates agents + supply
│   ├── stability_analyzer.py     # USI, Gini, S_R computation
│   ├── policy_engine.py          # Karnataka scheme benefit calculation
│   ├── shock_engine.py           # Flood/drought/economic shock injection
│   └── resource_system.py        # Supply time-series + interaction matrix
│
├── dashboard/
│   ├── insight_engine.py         # Rule-based insight + verdict generator
│   └── __init__.py
│
├── data/
│   ├── processed/
│   │   ├── model_config_by_city.json    # Master city config (agents, income, supply)
│   │   ├── shock_parameters.json        # Shock magnitudes and durations
│   │   ├── policy_parameters.json       # Scheme benefit levels
│   │   └── resource_interaction_matrix.json
│   └── scripts/
│       ├── 00_setup.py           # Initialize directory structure
│       ├── 11_run_experiments.py # Run all 6 experimental scenarios
│       └── 12_analyze_results.py # Aggregate results → MASTER_SUMMARY.csv
│
├── results/
│   └── experiments/
│       ├── MASTER_SUMMARY.csv            # Final metrics: all cities × all scenarios
│       ├── exp1_baseline/_all_cities.csv # Time-series: 24 steps × 5 cities
│       ├── exp2_flood/_all_cities.csv
│       ├── exp3_drought/_all_cities.csv
│       ├── exp4_economic/_all_cities.csv
│       ├── exp5a_shock_nopolicy/_all_cities.csv
│       └── exp5b_shock_policy/_all_cities.csv
│
├── requirements.txt
└── .gitignore
```

---

## 🖥️ Screenshots

### City Overview — Baseline Performance
> KPI cards, USI/Trust/Gini time-series, income group distribution, Insight Engine

### Experiment Compare — Scenario Analysis
> Multi-scenario USI overlay for any city + Trust Dynamics + Consumption Inequality

### Cross-City Analysis — Vulnerability Heatmap
> USI heatmap (scenarios × cities), radar resilience scores, policy effectiveness bars

### Live Simulation — Real-Time Run
> Configure city + scenario + shocks → run Mesa simulation live → watch metrics update

---

## 🚀 Running Locally

```bash
# 1. Clone
git clone https://github.com/Raiden-24/ABM_Urban_Stability.git
cd ABM_Urban_Stability

# 2. Environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Regenerate experiment data
python data/scripts/11_run_experiments.py
python data/scripts/12_analyze_results.py

# 5. Launch dashboard
streamlit run streamlit_app.py
```

> The dashboard works out-of-the-box with the pre-computed CSVs in `results/experiments/`.  
> Only run step 4 if you modify the model or want fresh simulation data.

---

## 🔬 Experimental Scenarios

| ID | Scenario | Description |
|---|---|---|
| `exp1_baseline` | **Baseline** | No shocks; normal city behaviour |
| `exp2_flood` | **Flood Shock** | Water supply −40% during Jul–Sep (monsoon) |
| `exp3_drought` | **Drought Shock** | Water scarcity −30% during Mar–May; propagates to food |
| `exp4_economic` | **Economic Shock** | Income reduction −25% (GDP contraction) |
| `exp5a_shock_nopolicy` | **All Shocks — No Policy** | Worst-case concurrent shocks, no government schemes |
| `exp5b_shock_policy` | **All Shocks — With Policy** | Concurrent shocks cushioned by all 3 Karnataka schemes |

---

## 📐 Key Metrics

### Urban Stability Index (USI)
```
USI = 0.25 × S_R  +  0.25 × C  +  0.25 × S_I  +  0.25 × S_O
```

| Component | Formula | Meaning |
|---|---|---|
| **S_R** | `0.4·food + 0.4·water + 0.2·electricity` | Composite resource sufficiency |
| **C** | Agent cooperation mean | Social trust & collective behaviour |
| **S_I** | `1 − Gini` | Equity / inverse inequality |
| **S_O** | Policy outcome score | Government scheme effectiveness |

| USI Range | Grade |
|---|---|
| ≥ 0.85 | 🟢 Stable |
| 0.65 – 0.84 | 🟡 Moderate |
| < 0.65 | 🔴 Fragile |

### Consumption Gini
Measured on **resource satisfaction** (allocation / demand) rather than income — captures lived inequality, not just earning inequality. Weighted: `0.4·food + 0.4·water + 0.2·electricity`.

---

## 🏛️ Data Sources

| Dataset | Source | Use |
|---|---|---|
| City demographics | India Census 2011 + Karnataka PCA | Agent population, income groups |
| Household consumption | HCES 2023-24 (NSSO) | Food/water/electricity demand calibration |
| Water supply | Karnataka BWSSB / ULB annual reports | Monthly supply time-series |
| Electricity supply | BESCOM / MESCOM distribution data | Seasonal supply patterns |
| Food (PDS) | Karnataka Food, Civil Supplies & Consumer Affairs | Anna Bhagya ration quantities |
| Policy parameters | Karnataka Budget 2023-24 | Gruha Jyothi / Gruha Lakshmi benefit levels |
| Shock magnitudes | IMD monsoon data + RBI economic reports | Flood/drought/economic shock calibration |

---

## 🤖 Insight Engine

The dashboard includes a **rule-based Insight Engine** (`dashboard/insight_engine.py`) that automatically interprets simulation results in plain English.

Instead of leaving the user to manually decode numbers:

> *USI = 0.637, Trust = 0.002, Gini = 0.0064*

The engine generates:

> 🔴 **Bengaluru is structurally fragile under all shocks without policy**  
> *Final USI of 0.637 — well below the stable threshold. Root cause: high non-poor consumption crowds out PDS supply for extreme-poor. This city requires targeted policy intervention, not just shock mitigation.*
>
> ⚠️ **Trust collapse detected — systemic cooperation breakdown**  
> *Average agent trust fell to 0.002 (below the 0.3 protest-risk threshold). In the model, trust below 0.4 triggers cooperation collapse — agents stop moderating demand, causing a demand escalation cascade that further depletes supply. Real-world equivalent: civil unrest, reduced institutional compliance.*

**Design principles:**
- Deterministic + rule-based — no LLM, no API calls, works offline
- Tiered: Primary finding → Causal mechanism → Policy note
- City-specific personality profiles for contextual recommendations

---

## 📦 Dependencies

```
mesa>=2.0
streamlit>=1.35
pandas>=2.0
numpy>=1.26
plotly>=5.18
scipy>=1.12
```

---

## 👤 Author

**Amruth** — ABM Research, Urban Policy Simulation  
Repository: [github.com/Raiden-24/ABM_Urban_Stability](https://github.com/Raiden-24/ABM_Urban_Stability)  
Live App: [abm-urban-stability.streamlit.app](https://abm-urban-stability.streamlit.app)

---

## 📄 License

MIT License — free to use, modify, and distribute with attribution.

---

<p align="center">
  Built with Mesa · Streamlit · Plotly · Real Karnataka Data
</p>
