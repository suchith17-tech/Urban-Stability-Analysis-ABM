# Project Status & Roadmap
## Multi-Agent Framework for Urban Socio-Economic Stability Evaluation
### Last Updated: 2026-03-27

---

## 🟢 COMPLETED

### Phase 1 — Foundational Data (100%)

| Step | Script | Output | Status |
|---|---|---|---|
| Step 0 | `00_setup.py` | Directory structure | ✅ Done |
| Step 1 | `01_process_pca.py` | `city_demographics.csv` | ✅ Done |
| Step 2 | `02_process_income.py` | `income_distribution.csv` | ✅ Done |
| Step 3 | `03_process_ration_cards.py` | `agent_class_proportions.csv` | ✅ Done |

**Key outcomes:**
- 5 cities profiled: Bengaluru, Mysuru, Mangaluru, Hubballi-Dharwad, Belagavi
- 3 income groups with real lognormal distributions (not flat PCI proxies)
- Agent class proportions from actual ration card data

---

### Phase 2 — Monthly Resource Supply System (100%)

| Step | Script | Output | Status |
|---|---|---|---|
| Step 4 | `04_process_water.py` | `water_supply_monthly.csv` | ✅ Done |
| Step 5 | `05_process_electricity.py` | `electricity_supply_monthly.csv` | ✅ Done |
| Step 6 | `06_process_food_ration.py` | `food_ration_supply.csv` | ✅ Done |

**Key outcomes:**
- Monthly timestep standardised across all resources
- City-specific seasonal water multipliers (hydrology-based, not uniform)
- Stochastic variability baked into electricity (±5-10%) and food (±10%)
- Per-HH unit columns for all 3 resources (verified against sanity ranges)
- Shock multiplier columns ready for ABM conditional application
- PDS food correctly parsed from col[9] (Quintals), core-taluk-only mapping

**Fixes applied during review:**
- Water: removed erroneous `/30` in per-HH calc
- Food: fixed column parsing (col[1]=shops ≠ quantity), core-taluk mapping, RC-based denominator
- Electricity: added seeded stochastic noise, shock_multiplier_base column

---

### Phase 3 — Demand Calibration & Resource Interactions (100%)

| Step | Script | Output | Status |
|---|---|---|---|
| Step 7 | `07_process_hces.py` | `demand_calibration.csv` | ✅ Done |
| Step 8 | `08_resource_interactions.py` | `resource_interaction_matrix.json` | ✅ Done |
| Step 9 | `09_compile_master.py` | `model_config_by_city.json` | ✅ Done |

**Key outcomes:**
- Per-group demand calibrated from real MPCE expenditure categories
- PDS share decomposition (60%/35%/10% for poor/BPL/non-poor)
- Resource interaction coefficients: water→food (0.715), elec→water (0.458), food→trust (0.638)
- Academic disclaimer on correlation ≠ causation included
- Master config JSON compiled — single file for ABM model ingestion

**Fixes applied during review:**
- Water demand: Housing water fraction 15% → 5% (rent dominates Housing MPCE)
- Food supply/demand: PDS supply is partial; added market supply decomposition

---

## 🟡 IN PROGRESS

### Phase 4 — PDF Shock/Policy Extraction (100%)

| Task | Description | Status |
|---|---|---|
| Complete `10_extract_pdf_params.py` | Extracted real policy/shock params with citations | ✅ Done |
| Update master config compiler | Handled city-specific shock objects w/ recovery | ✅ Done |
| Trust mechanics formalization | Defined thresholds, triggers for trust drops | ✅ Done |

---

### Phase 5 — Model Core Refactoring (100%)

| Task | Description | Status |
|---|---|---|
| `config_loader.py` | Load master JSON to simulation Engine | ✅ Done |
| Refactor `UrbanAgent` | Lognormal income, 3 resource demand, trust rules | ✅ Done |
| Refactor `ResourcePool` | Multi-pool allocation, interaction effects, PDS | ✅ Done |
| Refactor `ShockModule` | Recovery curves, correct step implementation | ✅ Done |
| Refactor `PolicyEngine` | Anna Bhagya, Gruha Jyothi, Gruha Lakshmi | ✅ Done |
| Refactor `urban_model.py` | Core step sequence perfection | ✅ Done |
| Refactor `main.py` | 5 city execution loop, CSV dumps | ✅ Done |

---

## 🟡 IN PROGRESS

### Phase 6 — Experiment Execution

| Task | Description | Status |
|---|---|---|
| Script `11_run_experiments.py` | Automate all 6 scenarios across 5 cities | ⬜ Pending |
| EXP 1: Baseline | Normal behaviour, no shocks, policies OFF vs ON | ⬜ Pending |
| EXP 2: Flood Shock | Test climate cascade (July-Sep) | ⬜ Pending |
| EXP 3: Drought Shock | Test water scarcity (Mar-May) | ⬜ Pending |
| EXP 4: Economic Shock | Test income reduction impact | ⬜ Pending |
| EXP 5: Policy Effectiveness | Shocks ON/Policies OFF vs Shocks ON/Policies ON | ⬜ Pending |
| EXP 6: Combined Scenario | Flood + Drought + Economic + Policies ON | ⬜ Pending |

---

## 🔴 NOT YET STARTED

### Phase 7 — Analysis & Validation

| Task | Description | Status |
|---|---|---|
| Script `12_analyze_results.py` | Generate comparative charts and data tables | ⬜ Pending |
| Visualizations | USI vs Time, Trust vs Time, Gini vs Time | ⬜ Pending |
| Cross-City Comparison | Identify most/least stable cities and why | ⬜ Pending |
| Extract Insights | Document the 'Why' behind the charts | ⬜ Pending |
| Validation Checks | Confirm logical behaviour, poor suffering first | ⬜ Pending |

### Phase 8 — Documentation & Dashboard

| Task | Description | Status |
|---|---|---|
| Research Paper / Report | Write Methodology, Experiments, Results, Conclusion | ⬜ Pending |
| Update Web Dashboard | Update Streamlit to load experiment results interactively | ⬜ Pending |

---

## File Inventory

### Raw Data (`DATASETS/`)
```
Census PCA files (5 cities)
consumer details per capita.xlsx
karnataka districts urban.csv
water supply data.xlsx
electricity consumption data.xlsx
karnataka_electricity_timeseries.csv
feb -apr 2025 (Rice/Wheat/Dal).xlsx
9 PDF documents (flood, water policy, economic survey, schemes)
```

### Processing Scripts (`data/scripts/`)
```
00_setup.py          → directory structure
01_process_pca.py    → demographics
02_process_income.py → income distributions
03_process_ration_cards.py → agent classes
04_process_water.py  → monthly water supply
05_process_electricity.py → monthly electricity supply
06_process_food_ration.py → monthly food ration
07_process_hces.py   → demand calibration
08_resource_interactions.py → coupling coefficients
09_compile_master.py → master config JSON
_verify_income.py    → income verification
_verify_units.py     → unit sanity checks
_verify_phase3.py    → phase 3 verification
```

### Processed Outputs (`data/processed/`)
```
city_demographics.csv          (5 rows)
income_distribution.csv        (15 rows)
agent_class_proportions.csv    (7 rows)
water_supply_monthly.csv       (60 rows)
electricity_supply_monthly.csv (60 rows)
food_ration_supply.csv         (60 rows)
demand_calibration.csv         (15 rows)
resource_interaction_matrix.json
model_config_by_city.json      ← THE MASTER FILE (24.8 KB)
```

---

## Immediate Next Steps (Priority Order)

1. **Complete Phase 4**: Extract shock/policy parameters from PDFs with source citations
2. **Refactor model core**: Make `UrbanAgent` and `ResourcePool` consume `model_config_by_city.json`
3. **Run baseline simulation**: 5 cities × 12 months → verify USI behaviour
4. **Apply shock scenarios**: Test flood, drought, economic crisis
5. **Update dashboard**: City selector, monthly timeline, data-driven parameters

---

## Architecture Overview

```
DATASETS/ (raw)
    ↓
data/scripts/ (processing pipeline: 01-09)
    ↓
data/processed/ (clean outputs)
    ↓
model_config_by_city.json (master config)
    ↓
model/ (UrbanStabilityModel ← reads config)
    ↓
visualization/ (Streamlit dashboard)
```

**Current state**: Pipeline complete through config generation. Model core still uses synthetic/hardcoded parameters — refactoring to consume the new data-driven configs is the critical next step after Phase 4.
