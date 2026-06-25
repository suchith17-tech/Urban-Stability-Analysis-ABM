# Upcoming Project Roadmap — ABM Urban Stability (Karnataka)
**Date:** 2026-03-26  
**Goal:** Convert the current synthetic simulation into a real-world city stability model using empirical Karnataka data

---

## Vision Alignment

> **"How stable is a city when people, resources, and disasters interact?"**

| Dimension | Current State | Target State |
|---|---|---|
| Agents | Lognormal random income | Real Karnataka household income distribution |
| Resources | Fixed constant supply | City-specific, time-varying supply from data |
| Behaviour | Single demand formula | Income-group differentiated decision logic |
| Shocks | One abstract shock type | Flood, drought, trust-breakdown from policy data |
| Policies | 3 generic controls | Mapped to actual Karnataka schemes |
| Output | Synthetic USI curve | City-specific calibrated USI for 5 Karnataka cities |

---

## Phase 1 — Data Foundation (2–3 Weeks)

> [!IMPORTANT]
> This phase is a prerequisite for all subsequent phases. No model changes before this is done.

### 1.1 — Cleanup and Standardise Datasets
**Data Sources Used:** All files in DATASETS/  
**Outputs:** `data/processed/` folder with clean CSVs and JSON configs  

Tasks:
- [ ] Delete duplicate files (`per capita income final (1).xlsx`, `urban_households_full_dataset 2.csv`)
- [ ] Rename cryptic UUID-named CSVs
- [ ] Run processing scripts for Steps 1–7 from the Data Processing Plan
- [ ] Manually extract policy parameters from 4 scheme PDFs into `policy_parameters.json`
- [ ] Manually extract shock parameters from 2 disaster PDFs into `shock_parameters.json`
- [ ] Build `model_config_by_city.json` with 5 city configs

**Deliverable:** `data/processed/model_config_by_city.json` — ready to pass to `UrbanStabilityModel`

---

### 1.2 — Data Alignment Assessment

Using the available data, here is the alignment score with the 8-step roadmap:

| Roadmap Step | Available Data | Alignment |
|---|---|---|
| Step 1: Clean Data | All XLSX/CSV files | ✅ High — all data is present |
| Step 2: Real Agents | HCES 5.1M rows (percentiles) + Ration Cards | ✅ Very High — real within-city income distribution available |
| Step 3: Real Resources | Water/Electricity/Food with monthly multipliers | ✅ High — all 3 resources + seasonal variation modelled |
| Step 4: Real Behaviour + Interactions | HCES 5.1M rows + correlation analysis | ✅ Very High — resource coupling extractable from data |
| Step 5: Real Shocks | Flood Action Plan + DM Policy PDFs | ⚠️ Medium — magnitudes must be manually extracted from PDFs |
| Step 6: Real Policies | 4 scheme PDFs (Anna Bhagya, Gruha Jyothi etc.) | ✅ High — schemes are specific and numerical |
| Step 7: Calibration | HCES + supply data | ✅ High — enough to validate |
| Step 8: Validation | HCES + PCA | ✅ High — comparison possible against real distributions |

**Overall Alignment Score: 8/8 steps have necessary data. 5/8 are directly codeable. 3/8 require manual PDF extraction.**

---

## Phase 2 — Real Agent Population (Week 3–4)

### What Changes in Code:
**File:** `agents/urban_agent.py` and `model/urban_model.py`

### 2.1 — Introduce Income Groups from HCES Percentiles ⚡ FIXED

> [!IMPORTANT]
> **Do NOT use district-level Per Capita Income (PCI) to model agents.** PCI is a macro average — using it creates agents with near-identical incomes, making inequality dynamics fake. Instead, derive income distributions directly from HCES household expenditure percentiles.

The 3 income groups are defined by **within-city MPCE (Monthly Per Capita Expenditure) percentiles** from HCES:

```python
# From HCES data (processed in Step 2 of Data Processing Plan)
hces_urban = filter(State=29, Sector=Urban)
p30 = percentile(hces_urban['MPCE'], 30)  # lower income boundary
p70 = percentile(hces_urban['MPCE'], 70)  # upper income boundary

income_group_values = {
    "poor":   hces_urban[mpce <= p30],    # extreme_poor + BPL combined
    "middle": hces_urban[(p30 < mpce) & (mpce <= p70)],
    "rich":   hces_urban[mpce > p70]
}
```

For each group, fit a lognormal: `lognorm.fit(group['annual_income'])` → yields `(mean, sigma)` per group.

This directly replaces the single global `income_mean=2, income_sigma=1` with **3 per-group, empirically fitted lognormals**.

### 2.2 — Map Ration Cards → Group Fractions
Ration card proportions (from Step 3 of Data Processing) determine how many agents belong to each group:

```
AAY fraction            → extreme_poor group (sub-group of "poor")
PHH fraction            → bpl_poor group (rest of "poor")
NPHH fraction           → "middle" + "rich" split at P70
```

### 2.3 — New Agent Attributes:
```python
self.income_group       # "poor" | "middle" | "rich"
self.city               # "Bengaluru" | "Mysore" etc.
self.water_demand       # separate from generic demand
self.electricity_demand
self.food_demand
self.subsistence_level  # minimum need below which trust collapses
self.current_month      # tracks season for seasonal demand variation
```

### 2.4 — Agent Step Refinements:
- If `allocated < subsistence_level` → trigger rapid trust loss (not gradual)
- Rich agents (non-poor): extra hoarding factor on scarce resources
- Poor agents: demand reduction when price rises (inelastic food, elastic electricity)

**Deliverable:** Refactored `UrbanAgent` with HCES-percentile income distribution per group

---

## Phase 3 — Real Resource System with Monthly Timestep (Week 4–5) ⚡ FIXED

### What Changes in Code:
**File:** `model/resource_pool.py`, `model/urban_model.py`, `config.py`

> [!IMPORTANT]
> **Model timestep = 1 month.** This is the foundational design change. All resource supply values must be arrays of 12 monthly values, not single static numbers.

### 3.1 — Multi-Resource Architecture
Split the single `total_supply` into three independent resource pools:

```python
self.current_month = (self.current_step % 12)  # 0=Jan, 11=Dec
self.water_pool       = ResourcePool("water", config["supply_monthly"]["water_mld"][self.current_month])
self.electricity_pool = ResourcePool("electricity", config["supply_monthly"]["electricity_mu"][self.current_month])
self.food_pool        = ResourcePool("food", config["supply_monthly"]["food_kg"][self.current_month])
```

At the start of each step, each pool's `total_supply` is refreshed from the monthly schedule.

### 3.2 — City-Specific Monthly Supply (12-Value Arrays)
All values below are **monthly arrays** derived from seasonal multipliers applied to empirical baselines:

| City | Water Base (MLD) | Electricity Base (MU/yr) | Food Base (kg/month) |
|---|---|---|---|
| Bengaluru | ~1,450 | 14,560 | 1,160,084 |
| Mysuru | ~350 | 760 | 640,703 |
| Hubballi-Dharwad | ~480 | 980 | 728,095 |
| Mangaluru | ~300 | 533 | 169,922 |
| Belagavi | ~250 | 630 | 562,498 |

**Example monthly water array for Bengaluru (MLD):**
```python
# base = 1450 MLD, seasonal multipliers: winter=1.0, summer=0.65, monsoon=1.2, post=0.90
[1450, 1450, 943, 943, 943, 1740, 1740, 1740, 1740, 1305, 1305, 1305]
# Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
```

### 3.3 — Multi-Resource Interaction Logic ⚡ NEW

Resources are **not independent**. The following dependency rules are added to `ResourcePool.allocate()`:

```python
# After allocation — apply cross-resource effects
if water_supply < 0.5 * water_required:
    # Low water → food utilization drops (can't cook, hygiene fails)
    food_pool.effective_supply *= (1 - interaction["water_deficit_on_food_utilization"])

if electricity_supply < 0.4 * electricity_required:
    # Low electricity → water pumping capacity drops
    water_pool.total_supply *= (1 - interaction["electricity_deficit_on_water_pumping"])
```

The coefficients `water_deficit_on_food_utilization` and `electricity_deficit_on_water_pumping` are **not assumed** — they are extracted from HCES correlation analysis in Data Processing Step 7B.

This creates cascading failure dynamics:
```
Electricity drops → Water pumping drops → Water shortage → Food utilization drops → Trust collapse
```

**Deliverable:** `MultiResourcePool` with monthly supply schedule and interaction coupling

---

## Phase 4 — Real Behaviour Calibration (Week 5–6)

### What Changes in Code:
**File:** `agents/urban_agent.py`

### 4.1 — Income-Group Demand Logic
Derived from HCES calibration (demand_calibration.csv):

| Agent Group | Water Demand (LPCD) | Electricity Demand (kWh/month) | Food Demand (kg/month) |
|---|---|---|---|
| Extreme Poor | ~70 | ~40 | ~5 |
| BPL Poor | ~100 | ~80 | ~8 |
| Non-Poor | ~135+ | ~150+ | ~12 |

### 4.2 — New Demand Formula (Multi-Resource):
```
water_demand      = base_water_lpcd × household_size × price_factor
electricity_demand = base_kwh × income_elasticity × price_factor
food_demand       = base_food_kg × members × subsidy_factor
```

### 4.3 — Survival Threshold:
```
if allocated_water < 50 LPCD:
    trust -= 0.15  (survival crisis: trust loss is immediate and large)
if allocated_food < 3 kg/person:
    trust -= 0.10
```

**Deliverable:** HCES-calibrated demand curves per income group per resource

---

## Phase 5 — Real Shocks with Data-Derived Magnitudes (Week 6–7) ⚡ FIXED

### What Changes in Code:
**File:** `modules/shock_module.py`

> [!CAUTION]
> **All shock magnitudes must be extracted from PDF source documents.** Do NOT use assumed or invented percentages. The old values (35%, 50%, 20%) were placeholders — they must be replaced with real figures from the Flood Action Plan and State Water Policy before implementation.

### 5.1 — New Shock Types:

| Shock Name | Trigger | Effect | Magnitude Source |
|---|---|---|---|
| `flood` | Probabilistic, monsoon months (Jun–Sep) | Water supply × (1 − X%), Food supply × (1 − Y%), Trust × (1 − Z%) | **Flood Action Plan 2021 — Section on urban infrastructure impact** |
| `drought` | Probabilistic, summer months (Mar–May) | Water supply × (1 − W%) | **State Water Policy — reservoir depletion norms** |
| `economic_crisis` | USI < 0.3 for 2 steps | Bottom-group income − V% | **Economic Survey income volatility data** |
| `trust_breakdown` | External social event | All agent trust × (1 − 0.3) | Existing — retained |

### 5.2 — How to Extract Shock Magnitudes from PDFs:
For each PDF, extract:
- **% urban infrastructure damaged** in a moderate/historical event → `water_supply_reduction`
- **% population affected** → `trust_reduction`
- **% crop/food logistics disrupted** → `food_supply_reduction`
- **Typical event duration** → `persistence_months`

Document every extracted value with the source page number in `shock_parameters.json`:
```json
"shock_flood": {
  "water_supply_reduction": "[Fill from PDF]",
  "food_supply_reduction": "[Fill from PDF]",
  "trust_reduction": "[Fill from PDF]",
  "persistence_months": "[Fill from PDF]",
  "source": "Flood Action Plan 2021, Page XX"
}
```

### 5.3 — Probabilistic Shock Trigger:
```python
def apply_stochastic_shock(self, model):
    season = model.get_current_season()  # derived from current_month
    if season == "monsoon":
        if random() < self.flood_probability:
            model.water_pool.total_supply  *= (1 - self.shock_params["flood"]["water_supply_reduction"])
            model.food_pool.total_supply   *= (1 - self.shock_params["flood"]["food_supply_reduction"])
            for agent in model.agents_list:
                agent.trust *= (1 - self.shock_params["flood"]["trust_reduction"])
```

### 5.4 — Interaction Cascades During Shock:
Because of resource interactions (Phase 3.3), a flood shock amplifies automatically:
```
Flood → water_supply drops → electricity demand for pumping increases →
        electricity pool stressed → water pumping drops further → trust collapses
```
This emergent cascade does not require extra code — it flows from the interaction coefficients already configured.

**Deliverable:** Extended `ShockModule` with 4 shock types, data-derived magnitudes with citations, probabilistic seasonal triggers

---

## Phase 6 — Real Policy Mechanisms (Week 7–8)

### What Changes in Code:
**File:** `model/policy_engine.py`

### 6.1 — Karnataka Scheme Mapping:

| Scheme | Code Implementation |
|---|---|
| **Anna Bhagya** | BPL/AAY agents receive food allocation before proportional distribution (priority queue) |
| **Gruha Jyothi** | Agents with electricity demand ≤ 200 kWh/month pay zero price (price = 0) |
| **Gruha Lakshmi** | Women household head agents (+income boost: +₹2000/month) — increases demand stability |
| **Targeted Subsidy** | Existing subsidy mechanism for extreme_poor and bpl_poor enhanced |
| **Consumption Cap** | Adjust cap separately per resource (water: 135 LPCD, electricity: 300 kWh) |

### 6.2 — Policy Evaluation Scenarios to Test:

| Scenario | Description |
|---|---|
| Baseline | No policies |
| Water Policy Only | 135 LPCD minimum allocation guaranteed |
| Food Policy Only | Anna Bhagya for BPL/AAY agents |
| All Schemes Active | Anna Bhagya + Gruha Jyothi + Gruha Lakshmi |
| Shock + No Policy | Flood event with no government intervention |
| Shock + Full Policy | Flood event with all schemes active → measure recovery |

**Deliverable:** Policy engine with 3 real Karnataka schemes as toggleable modules

---

## Phase 7 — Calibration and Tuning (Week 8–9)

**Goal:** Ensure simulation output matches known empirical outcomes

### 7.1 — Calibration Targets:

| Metric | Empirical Benchmark | Source |
|---|---|---|
| Gini Coefficient (Bangalore) | 0.35–0.42 | HCES 2023-24 |
| Average per capita water | 135 LPCD (urban target) | State Water Policy |
| % below subsistence | ~12% (AAY cardholder fraction) | Ration Cards |
| Trust at collapse | USI < 0.30 |  Execution Plan |

### 7.2 — Tuning Variables:
- `trust_weight_personal` (α): currently 0.7 — test range [0.5, 0.85]
- `usi_weights`: test both equal-weight and empirically-derived weights
- **Income lognormal params per group**: fit to HCES percentile data (not PCI)
- `resource_interaction_coefficients`: fine-tune based on observed USI behaviour
- `seasonal_multipliers`: adjust water/food factors if USI oscillates unrealistically
- `avg_degree` in network: test scale-free vs random

### 7.3 — Validation Method:
1. Run baseline model with all 5 city configs
2. Extract Gini, average trust, supply/demand ratio
3. Compare against HCES 2023-24 empirical values
4. Adjust parameters until model outputs match within ±10%

---

## Phase 8 — Final Validation and Outputs (Week 9–10)

### 8.1 — City-Level USI Comparison:
Run simulations for all 5 cities under identical shock and policy conditions. Compare USI trajectories:
- Is Bangalore more resilient? (larger economy, more resources)
- Is Belagavi more vulnerable? (lower supply, higher poverty proportion)

### 8.2 — Policy Effectiveness Report:
For each of the 6 policy scenarios defined in Phase 6:
- Final USI score
- Recovery time after shock (USI return to >0.6)
- Gini index trend
- Population % meeting minimum needs

### 8.3 — Dashboard Updates:
Extend `streamlit_app.py` to:
- Allow city selection (5 cities)
- Allow policy scenario selection
- Show multi-resource breakdown (not just single supply)
- Show shock event timeline overlay

---

## Milestone Summary

| Milestone | Target | Deliverable |
|---|---|---|
| M1: Data Foundation | Week 3 | `model_config_by_city.json` |
| M2: Real Agents | Week 4 | Refactored `UrbanAgent` |
| M3: Real Resources | Week 5 | `MultiResourcePool` |
| M4: Real Behaviour | Week 6 | HCES-calibrated demand curves |
| M5: Real Shocks | Week 7 | 4 shock types in `ShockModule` |
| M6: Real Policies | Week 8 | 3 Karnataka schemes in `PolicyEngine` |
| M7: Calibration | Week 9 | Tuned model matching HCES benchmarks |
| M8: Validation | Week 10 | City comparison report + updated dashboard |

---

## What This Model Will Be Able to Answer (After Phase 8)

1. **Which Karnataka city is most resilient to a flood shock?**
2. **Does Anna Bhagya food ration prevent system collapse during drought?**
3. **How long does it take for trust to recover after an economic crisis?**
4. **Which income group suffers first when supply drops?**
5. **Which combination of policies maximizes USI while minimizing cost?**
6. **In which month does Bengaluru face peak water-electricity-food stress simultaneously?**
7. **Does an electricity outage cascade into a food crisis through the water pumping dependency?**

---

## Summary of Critical Plan Fixes

| Issue | Old Plan | Fixed Plan |
|---|---|---|
| **Income modelling** | Fit lognormal from 5 PCI city averages | Fit 3 per-group lognormals from 5.1M HCES household percentiles |
| **Time dimension** | Static annual supply snapshots | Monthly timestep with seasonal multipliers for water, food, electricity |
| **Resource independence** | Water, food, electricity modelled separately | Interaction coefficients couple electricity→water→food→trust |
| **Shock calibration** | Assumed values (35%, 50%, 20%) | Extracted from Flood Action Plan + Water Policy PDFs with page citations |
