# Data Processing Plan — ABM Urban Stability (Karnataka)
**Date:** 2026-03-26  
**Goal:** Transform raw DATASETS files into model-ready inputs for `UrbanStabilityModel`

---

## Overview

All processing outputs will be saved to a new folder: `ABM_us_exe/data/processed/`  
Processing scripts will live in: `ABM_us_exe/data/scripts/`

```
ABM_us_exe/
├── DATASETS/          ← raw data (read-only after this plan)
├── data/
│   ├── scripts/       ← processing Python scripts
│   └── processed/     ← clean, model-ready files
```

---

## Step 0 — Housekeeping (Do This First)

**Delete duplicate files:**
```powershell
Remove-Item "DATASETS\per capita income final (1).xlsx"
Remove-Item "DATASETS\urban_households_full_dataset 2.csv"
```

**Rename cryptic files for clarity:**
```powershell
Rename-Item "DATASETS\70d066f8-2145-4b98-9e94-d7657b8a04a0.csv" "karnataka_electricity_timeseries.csv"
Rename-Item "DATASETS\880d7e38-82e9-41f7-98b9-f92dea3ef0f0.csv" "bangalore_sewage_infrastructure.csv"
```

---

## Step 1 — Process PCA City Census Data
**Input:** 5 PCA CSV files (one per city)  
**Output:** `data/processed/city_demographics.csv`  
**Script:** `data/scripts/01_process_pca.py`

### What to do:
1. Read each PCA CSV, skipping the first 4 header rows
2. Strip commas from all numeric strings: `"21,01,831"` → `2101831`
3. Extract city name from row 3 of each file
4. Extract household count from row 4
5. Parse the 7 indicator rows into a clean dictionary
6. Combine all 5 cities into a single master DataFrame

### Output Schema:
```
city | households | population | workers | non_workers | literate | illiterate | sc_pop | st_pop
```

### Calculations to compute:
- `worker_ratio = workers / population`
- `literacy_rate = literate / population`
- `sc_fraction = sc_pop / population`
- `avg_household_size = population / households`

---

## Step 2 — Process Agent Income Distribution from HCES
**Input:** `urban_households_full_dataset.csv` (5.1M rows — HCES 2023-24)  
**Input (secondary reference):** `per capita income final.xlsx` (district-level PCI — for context only)  
**Output:** `data/processed/income_distribution.csv`  
**Script:** `data/scripts/02_process_income.py`

> [!IMPORTANT]
> **Do NOT use per-capita income (PCI) to fit agent incomes.** PCI is a macro-economic average — it hides the within-city inequality that the model is designed to study. Using PCI produces fake agents with near-identical incomes. Instead, use **HCES micro-level household expenditure** as a proxy for income.

### What to do:
1. Load HCES data in chunks, filter `State == 29` (Karnataka), `Sector == 2` (Urban)
2. Identify the per-capita monthly expenditure column (MPCE — Monthly Per Capita Expenditure)
3. For each of the 5 target cities (filter by District code), compute **percentile breakpoints**:
   - P30 = 30th percentile of MPCE → upper bound of `extreme_poor`
   - P70 = 70th percentile of MPCE → upper bound of `bpl_poor`
4. Compute descriptive stats per group:
   - `poor` = MPCE ≤ P30
   - `middle` = P30 < MPCE ≤ P70
   - `rich` = MPCE > P70
5. For each group, compute `mean_mpce` and `std_mpce`
6. Convert MPCE → annual income: `annual_income = MPCE × 12 × household_size`
7. Fit a lognormal to annual income **within each group separately** using `scipy.stats.lognorm.fit`

### Output Schema:
```
city | income_group | p_lower | p_upper | mean_mpce | std_mpce | lognorm_mean | lognorm_sigma | group_fraction
```

### Why This Matters:
```python
# WRONG (old): fitting PCI across only 5 city means — produces fake homogeneity
income_sigma = np.std([pci_city1, pci_city2, ...])

# CORRECT (new): within-group distribution from 5.1M households
poor_agents  = hces_df[hces_df['mpce'] <= p30]
poor_mean, poor_sigma = lognorm.fit(poor_agents['annual_income'])
```

> **PCI file retained** as a macro sanity-check only: confirm that `mean_hces_income ≈ PCI` within ±20%. If not, flag as a data discrepancy.

---

## Step 3 — Process Ration Card Data (Agent Class Proportions)
**Input:** `karnataka ration cards.xlsx`  
**Output:** `data/processed/agent_class_proportions.csv`  
**Script:** `data/scripts/03_process_ration_cards.py`

### What to do:
1. Read the Excel file
2. Remove blank/separator rows (where `Taluk Name` is NaN or "TOTAL")
3. Keep only Karnataka urban taluks within the 5 target cities
4. Aggregate cards by category:
   - `AAY` = Extreme Poor
   - `PHH(NK) + PHH(K)` = BPL Poor  
   - `NPHH(NK) + NPHH(K)` = Non-Poor (Middle/Rich)
5. Compute percentage proportions for each category per city

### Output Schema:
```
city | extreme_poor_pct | bpl_poor_pct | non_poor_pct | total_ration_holders
```

### Usage in model:
These percentages directly set the proportions of agent income groups during model initialization.

---

## Step 4 — Process Water Supply Data with Monthly Seasonal Multipliers
**Input:** `water supply data.xlsx`  
**Output:** `data/processed/water_supply_monthly.csv`  
**Script:** `data/scripts/04_process_water.py`

> [!IMPORTANT]
> **Model timestep = 1 month.** All resource supply values must be expressed as monthly quantities, not annual averages or static snapshots.

### What to do:
1. Read XLSX — 5 rows × 3 columns (City, Population, Estimated Supply)
2. Confirm/convert units to MLD (Million Litres/Day) → convert to **monthly litres**: `monthly_L = MLD × 30 × 10^6`
3. Apply State Water Policy standard: 135 LPCD minimum
4. Compute `required_supply_monthly_L = Population × 135 × 30`
5. Compute `base_supply_deficit_ratio = actual_supply / required_supply`
6. **Apply seasonal multipliers** to generate 12 monthly supply values:

| Month | Season | Water Multiplier | Rationale |
|---|---|---|---|
| Jan–Feb | Winter | 1.00 | Baseline |
| Mar–May | Summer | 0.65 | Reservoir depletion, high evaporation |
| Jun–Sep | Monsoon | 1.20 | Rainfall recharge, river flow |
| Oct–Dec | Post-monsoon | 0.90 | Receding supply |

```python
monthly_supply[month] = base_mld × seasonal_multiplier[month]
```

### Output Schema:
```
city | month | season | base_mld | seasonal_multiplier | effective_mld | supply_deficit_ratio
```

---

## Step 5 — Process Electricity Supply Data with Monthly Time Series
**Input:** `electricity consumption data.xlsx`, `karnataka_electricity_timeseries.csv`  
**Output:** `data/processed/electricity_supply_monthly.csv`  
**Script:** `data/scripts/05_process_electricity.py`

> [!IMPORTANT]
> Electricity is the **only resource with a real time-series (2010–2023)**. This must be exploited to make all resource supplies consistent on a monthly basis.

### What to do:

**From time-series CSV:**
1. Parse FY year: `"2010-11"` → `2011`
2. Clean numeric columns (strip commas)
3. Compute `monthly_mu_per_city = annual_metered_MU / 12`
4. Compute YoY growth rate: use as `supply_growth_rate per month = annual_growth / 12`

**From XLSX (city snapshot):**
1. Extract Annual MU per city
2. Divide by households and 12 → `monthly_kwh_per_hh`
3. Apply monthly multipliers (demand peaks June–August due to cooling):

| Month | Electricity Demand Multiplier |
|---|---|
| Jan–Feb | 0.95 |
| Mar–May | 1.10 (cooling demand rises) |
| Jun–Sep | 1.05 (monsoon, less cooling but pumping) |
| Oct–Dec | 0.90 |

4. Each simulation month → look up `supply_for_that_month = base_supply × monthly_factor × (1 + growth_rate)^year`

### Output Schema:
```
city | year | month | base_annual_mu | monthly_mu | monthly_kwh_per_hh | demand_multiplier | supply_growth_rate
```

---

## Step 6 — Process Food Ration Data with Monthly Ration Cycle
**Input:** `feb -apr 2025 (Rice).xlsx`, `feb -apr 2025 (Wheat).xlsx`, `feb -apr 2025 (Dal).xlsx`  
**Output:** `data/processed/food_ration_supply.csv`  
**Script:** `data/scripts/06_process_food_ration.py`

> [!NOTE]
> Food ration data covers Feb–Apr 2025 (3 months). These 3 months form the **calibration base**. For all other months, apply a ration cycle model to extrapolate.

### What to do:
1. Parse each XLSX — skip first 2 rows (merged headers); manually assign column names:
   `Taluk | Feb_qty | Feb_cards | Mar_qty | Mar_cards | Apr_qty | Apr_cards`
2. Convert quantities: MT → KG (`× 1000`)
3. Group by city (aggregate taluks)
4. Combine all 3 commodities into a single food supply table
5. Compute `monthly_avg_per_commodity_per_city` from the 3 available months
6. **Extrapolate to full 12-month cycle** using a seasonal food multiplier:

| Month | Food Supply Multiplier | Reason |
|---|---|---|
| Jan–Mar | 1.00 | Normal ration cycle |
| Apr–Jun | 0.90 | Supply chain stress, summer |
| Jul–Sep | 0.85 | Monsoon disruption to logistics |
| Oct–Dec | 1.05 | Post-harvest surplus |

7. Apply Anna Bhagya norm as a floor: `rice_supply_poor ≥ 5 kg × ration_card_holders`
8. Flag any city-month combination where actual supply < Anna Bhagya floor as a **policy gap**

### Output Schema:
```
city | month | season | rice_kg | wheat_kg | dal_kg | total_food_kg | anna_bhagya_floor_kg | policy_gap_flag
```

---

## Step 7 — Process HCES: Demand Calibration + Resource Interaction Coefficients
**Input:** `urban_households_full_dataset.csv` (5.1M rows), `karnataka districts urban.csv` (43 MB)  
**Output:** `data/processed/demand_calibration.csv`, `data/processed/resource_interaction_matrix.json`  
**Script:** `data/scripts/07_process_hces.py`

> [!IMPORTANT]
> Do NOT load these files fully into memory. Always use chunked reading:
> ```python
> for chunk in pd.read_csv(path, chunksize=50000):
>     karnataka = chunk[chunk['State'] == 29]
> ```

### Sub-task A — Demand Calibration (as before)
1. Filter `State == 29` (Karnataka), `Sector == 2` (Urban)
2. Extract: household ID, district, MPCE, expenditure columns by category
3. Compute P30 and P70 percentiles of MPCE → define 3 income groups (feeds directly into Step 2 output)
4. For each group, compute **mean and std of demand** per resource:
   - Water: monthly water charge expenditure → convert to litres using ₹/litre rate
   - Electricity: monthly electricity expenditure → convert to kWh using ₹/unit rate
   - Food: sum of cereal + pulse + dairy expenditure columns

### Sub-task B — Resource Interaction Coefficient Extraction ⚡ NEW
Real-world water, electricity, and food are **not independent** — HCES data can reveal their coupling:

1. **Water–Food coupling**: Segment households by water expenditure quintile. Compute `mean_food_expenditure` per quintile. The correlation coefficient `r(water, food)` reveals how strongly water access drives food consumption.

2. **Electricity–Water coupling**: In households with below-median electricity spending, compute the fraction reporting low water access. This estimates the fraction of water supply that depends on electric pumping.

3. **Compute Resource Interaction Matrix**:
```python
interaction_coefficients = {
    "water_deficit_on_food":        r(water_shortfall, food_deficit),
    "electricity_deficit_on_water": fraction(low_elec → low_water),
    "food_deficit_on_trust":        rate(food_deficit → trust_drop)
}
```

### Output Schema A — Demand Calibration:
```
city | income_group | mean_water_demand_lpcd | std_water | mean_electricity_kwh | std_electricity | mean_food_kg | std_food
```

### Output Schema B — Resource Interaction Matrix:
```json
{
  "water_deficit_on_food_utilization": 0.XX,
  "electricity_deficit_on_water_pumping": 0.XX,
  "food_deficit_on_trust_drop_rate": 0.XX
}
```

> These coefficients directly parameterize the interaction logic in `ResourcePool` and `urban_agent.py` — they are data-grounded, not assumed.

---

## Step 8 — Extract Policy AND Shock Parameters from PDFs (Manual Step)
**Input:** 9 PDF documents  
**Output:** `data/processed/policy_parameters.json`, `data/processed/shock_parameters.json`  
**Method:** Manual reading + structured extraction  

### 8A — Policy Parameters to Extract:

| Policy | Parameter to Extract | Source PDF |
|---|---|---|
| Water norm | 135 LPCD minimum | StateWaterPolicy |
| Anna Bhagya | 5 kg rice/person/month for BPL | anna_bhagya_scheme |
| Gruha Jyothi | Free if usage ≤ 200 units/month | gruha_jyothi_scheme |
| Gruha Lakshmi | ₹2000/month transfer to women HoH | Gruha-Lakshmi |
| FHTC coverage | % households without tap → water access gap | FHTCDataTable |
| DM Response | Emergency supply release thresholds | Policy_Revision_DM2020 |

---

### 8B — Shock Parameters: Data-Derived, NOT Assumed ⚡ CRITICAL FIX

> [!CAUTION]
> **Do NOT assume shock magnitudes.** Values like `shock_flood_supply_reduction = 0.35` were previously invented. All shock parameters must be extracted from actual PDF data.

For each shock type, read the source PDF and extract the following:

#### Flood Shock (`ActionplanforFloodriskmanagement2021.pdf`)
Extract from the document:
- `% of urban infrastructure affected in moderate flood` → maps to `water_supply_reduction`
- `% of crop/food supply disrupted` → maps to `food_supply_reduction`
- `% of affected population` → maps to `trust_reduction` (fraction of city experiencing trauma)
- `duration of typical flood event (weeks)` → maps to `shock_persistence_steps`

**Template to fill after reading:**
```json
"shock_flood": {
  "water_supply_reduction": "[X]% — extracted from Section Y of flood report",
  "food_supply_reduction":  "[X]% — from crop loss table",
  "trust_reduction":        "[X]% — from affected population %",
  "persistence_months":     "[N] — from typical event duration",
  "source_page":            "Page [N], ActionPlan_Flood"
}
```

#### Drought Shock (`StateWaterPolicy-English.pdf`)
- `% reduction in reservoir storage in drought year` → maps to `water_supply_reduction`
- Seasonal drought definition → maps to `trigger_months`

#### Economic Crisis Shock (`Economic_Survey_2025-26_English_FinalMpdf.pdf`)
- Income growth rate volatility between years → maps to `income_shock_magnitude`

> **No placeholder value is acceptable in `shock_parameters.json`.** Every number must have a source page cited.

---

## Step 9 — Build Master Config Table
**Input:** Outputs from Steps 1–8  
**Output:** `data/processed/model_config_by_city.json`  
**Script:** `data/scripts/09_build_master_config.py`

### What to do:
For each of the 5 cities, produce one config dict ready to pass to `UrbanStabilityModel(config=...)`.  
The schema now contains: income **per group** from HCES (not single lognormal), **monthly** supply series, **interaction coefficients**, and **cited shock magnitudes**.

```json
{
  "Bengaluru": {
    "num_agents": 500,
    "timestep": "month",
    "agent_groups": {
      "extreme_poor": {"fraction": 0.12, "lognorm_mean": X, "lognorm_sigma": X},
      "bpl_poor":     {"fraction": 0.43, "lognorm_mean": X, "lognorm_sigma": X},
      "non_poor":     {"fraction": 0.45, "lognorm_mean": X, "lognorm_sigma": X}
    },
    "supply_monthly": {
      "water_mld":       [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec],
      "electricity_mu":  [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec],
      "food_kg":         [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
    },
    "resource_interactions": {
      "water_deficit_on_food_utilization": X,
      "electricity_deficit_on_water_pumping": X
    },
    "policy": { ... },
    "shock": {
      "flood": {"water_reduction": X, "food_reduction": X, "source": "Page N, FloodReport"}
    }
  }
}
```

---

## Processing Priority Order

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1 (Immediate — Foundational)                          │
│   Step 0: Cleanup duplicates & rename files                 │
│   Step 1: PCA demographics → city_demographics.csv         │
│   Step 2: HCES income percentiles → income_distribution.csv│  ← FIXED: not PCI lognormal
│   Step 3: Ration cards → agent_class_proportions.csv       │
├─────────────────────────────────────────────────────────────┤
│ PHASE 2 (Monthly Resource System)                           │
│   Step 4: Water + seasonal multipliers → water_monthly.csv │  ← NEW: timestep=month
│   Step 5: Electricity monthly time-series                   │  ← NEW: monthly series
│   Step 6: Food ration + ration cycle model                  │  ← NEW: 12-month extrapolation
├─────────────────────────────────────────────────────────────┤
│ PHASE 3 (Behaviour + Interaction Calibration)               │
│   Step 7A: HCES demand calibration (large files)            │
│   Step 7B: Resource interaction coefficients extraction     │  ← NEW: coupling matrix
├─────────────────────────────────────────────────────────────┤
│ PHASE 4 (Policy + Shock Config Assembly)                    │
│   Step 8A: PDF policy extraction (manual)                   │
│   Step 8B: Shock magnitude extraction w/ source citations  │  ← FIXED: no assumed values
│   Step 9: Master config builder (monthly + grouped income)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Tools and Libraries Required

```text
pandas >= 2.0
openpyxl          (Excel reading)
numpy
scipy             (lognormal fitting per group: scipy.stats.lognorm.fit)
json
pathlib
```

All are already available or can be added to `requirements.txt`.

---

## Summary of Fixes Applied

| Issue | Old Approach | Fixed Approach |
|---|---|---|
| Income modelling | Fit lognormal from 5 PCI averages | Fit lognormal per group from 5.1M HCES households |
| Time dimension | Static annual snapshots | Monthly timestep with seasonal multipliers for all 3 resources |
| Resource interactions | Independent pools | Coupling coefficients extracted from HCES correlation analysis |
| Shock magnitudes | Assumed (e.g. 35%) | Extracted from Flood Report + Water Policy PDFs with source pages cited |
