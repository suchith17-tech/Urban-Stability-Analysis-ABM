# Data Audit Report — ABM Urban Stability (Karnataka)
**Date:** 2026-03-26  
**Audited Folder:** `ABM_us_exe/DATASETS/`  
**Total Files Found:** 30

---

## Summary Table

| # | File | Type | Size | Role in Model | Quality | Action |
|---|------|------|------|---------------|---------|--------|
| 1 | `PCA_29_572_99999_803162(Banglore).csv` | CSV | 625 B | Agent init — demographics | ⚠️ Minimal | Keep & Merge |
| 2 | `PCA_29_555_5438_803033(Belagavi).csv` | CSV | 561 B | Agent init — demographics | ⚠️ Minimal | Keep & Merge |
| 3 | `PCA_29_562_99999_803083(Hubballi-Dharvad).csv` | CSV | 646 B | Agent init — demographics | ⚠️ Minimal | Keep & Merge |
| 4 | `PCA_29_575_5561_803181(Manglaore).csv` | CSV | 573 B | Agent init — demographics | ⚠️ Minimal | Keep & Merge |
| 5 | `PCA_29_577_5572_803194(Mysore).csv` | CSV | 566 B | Agent init — demographics | ⚠️ Minimal | Keep & Merge |
| 6 | `karnataka ration cards.xlsx` | XLSX | 12 KB | Agent class: Poor group | ✅ Good | Keep & Process |
| 7 | `per capita income final.xlsx` | XLSX | 11 KB | Agent income distribution | ✅ Good | Keep & Process |
| 8 | `per capita income final (1).xlsx` | XLSX | 11 KB | Duplicate of #7 | ❌ Duplicate | **DELETE** |
| 9 | `water supply data.xlsx` | XLSX | 9 KB | Resource: water supply | ✅ Good | Keep & Process |
| 10 | `electricity consumption data.xlsx` | XLSX | 10 KB | Resource: electricity supply | ✅ Good | Keep & Process |
| 11 | `consumer details per capita.xlsx` | XLSX | 35 KB | Resource: per-capita consumption | ✅ Good | Keep & Process |
| 12 | `feb -apr 2025 (Rice).xlsx` | XLSX | 32 KB | Food resource: ration volume | ✅ Good | Keep & Process |
| 13 | `feb -apr 2025 (Wheat).xlsx` | XLSX | 31 KB | Food resource: ration volume | ✅ Good | Keep & Process |
| 14 | `feb -apr 2025 (Dal).xlsx` | XLSX | 31 KB | Food resource: ration volume | ✅ Good | Keep & Process |
| 15 | `urban_households_full_dataset.csv` | CSV | 1.4 MB | Agent consumption behaviour | ✅ Rich | Keep & Process |
| 16 | `urban_households_full_dataset 2.csv` | CSV | 1.4 MB | Duplicate of #15 | ❌ Duplicate | **DELETE** |
| 17 | `karnataka districts urban.csv` | CSV | 43 MB | HCES micro-level consumption | ✅ Very Rich | Keep & Sample |
| 18 | `supply_data.csv` | CSV | 204 B | Derived supply: energy + food | ⚠️ Pre-compiled | Keep (auto-gen) |
| 19 | `RS_Session_260_AU_1773_1.csv` | CSV | 1 KB | National ration allocation (state-level) | ⚠️ Macro-level | Keep (reference) |
| 20 | `70d066f8-2145-4b98-9e94-d7657b8a04a0.csv` | CSV | 667 B | Karnataka electricity time-series (2010–22) | ✅ Good | Keep & Process |
| 21 | `880d7e38-82e9-41f7-98b9-f92dea3ef0f0.csv` | CSV | 514 B | Bangalore sewage/infrastructure stats | ⚠️ Static | Keep (reference) |
| 22 | `ActionplanforFloodriskmanagement2021.pdf` | PDF | 15 MB | Shock config: flood magnitude, zones | ✅ Key | Extract parameters |
| 23 | `Economic_Survey_2025-26_English_FinalMpdf.pdf` | PDF | 15 MB | Macro context, income trends | ✅ Good | Extract parameters |
| 24 | `FHTCDataTable.pdf` | PDF | 114 KB | FHTC water connections data | ✅ Good | Extract parameters |
| 25 | `Gruha-Lakshmi scheme_document.pdf` | PDF | 614 KB | Policy: women household subsidy | ✅ Key | Extract policy rules |
| 26 | `HCES FactSheet 2023-24.pdf` | PDF | 2.6 MB | Consumption benchmarks (national) | ✅ Good | Extract parameters |
| 27 | `Policy Revision DM2020.pdf` | PDF | 2 MB | Shock response policies | ✅ Key | Extract parameters |
| 28 | `StateWaterPolicy-English.pdf` | PDF | 15 MB | Water policy: allocation targets (135 LPCD) | ✅ Key | Extract parameters |
| 29 | `anna_bhagya_scheme_document.pdf` | PDF | 252 KB | Policy: free rice ration scheme karnataka | ✅ Key | Extract policy rules |
| 30 | `gruha_jyothi_scheeme_document.pdf` | PDF | 631 KB | Policy: free electricity scheme (200 units) | ✅ Key | Extract policy rules |

---

## Duplicate Files to Delete

> [!CAUTION]
> The following files are exact-size duplicates. They must be deleted before processing to avoid double-counting.

| File to Delete | Duplicate Of |
|---|---|
| `per capita income final (1).xlsx` | `per capita income final.xlsx` |
| `urban_households_full_dataset 2.csv` | `urban_households_full_dataset.csv` |

---

## Detailed File Profiles

### GROUP 1: Agent Initialization — Demographics (Census PCA 2011)
**Files:** 5 PCA CSVs (one per city)

| Field | Value |
|---|---|
| Source | Census of India 2011 — Primary Census Abstract |
| Cities Covered | Bangalore, Belagavi, Hubballi-Dharwad, Mangalore, Mysore |
| Indicators | Population, Child Population, SC, ST, Literate, Workers |
| Households Data | Yes — # households per city embedded in file header |
| Format Issues | Header rows not uniform; comma-formatted numbers (`"21,01,831"` → needs stripping) |
| Temporal Coverage | Point-in-time (2011 census) |
| Missing | No income data, no resource consumption data — only headcounts |

**Key extracted values:**

| City | Households | Population | Workers |
|---|---|---|---|
| Bangalore | 21,01,831 | 84,43,675 | 36,92,394 |
| Belagavi | 1,11,436 | 4,88,157 | 1,70,748 |
| Hubballi-Dharwad | 2,00,418 | 9,43,788 | 3,34,037 |
| Mangalore | 1,12,444 | 4,88,968 | 2,03,396 |
| Mysore | 2,09,650 | 8,93,062 | 3,38,424 |

---

### GROUP 2: Agent Income Distribution
**File:** `per capita income final.xlsx`

| Field | Value |
|---|---|
| Shape | 32 rows × 10 columns |
| Coverage | Karnataka districts — per capita income across multiple years |
| Columns | District, Per Capita Income (multiple years) |
| Format Issues | Multi-year columns with year names as headers; some missing values |
| Use | Calibrate lognormal income distribution parameters by district |

---

### GROUP 3: Agent Class (Poor Group) — Ration Cards
**File:** `karnataka ration cards.xlsx`

| Field | Value |
|---|---|
| Shape | 45 rows × 7 columns |
| Columns | Taluk Name, AAY RCs, PHH(NK) RCs, PHH(K) RCs, NPHH(NK) RCs, NPHH(K) RCs, TOTAL |
| Key Information | Ration card counts by category (AAY = poorest, PHH = poor, NPHH = non-poor) |
| Format Issues | Multiple tables stacked in one sheet; mixed row types |
| Use | Define income group proportions (AAY=extreme poor, PHH=poor, NPHH=middle class) |

**Ration Card Categories:**
- **AAY (Antyodaya Anna Yojana):** Extreme poor → maps to "Low Income" agents  
- **PHH (Priority Household):** Below poverty line → maps to "Low-Middle" agents  
- **NPHH (Non-Priority Household):** Above poverty line → maps to "Middle-High" agents  

---

### GROUP 4: Resource Supply — Water
**File:** `water supply data.xlsx`

| Field | Value |
|---|---|
| Shape | 5 rows × 3 columns |
| Columns | City, Population, Estimated Water Supply |
| Cities | Bengaluru, Mysuru, Mangaluru, Hubballi-Dharwad, Belagavi |
| Format Issues | Units need confirmation (likely MLD — Million Litres per Day) |
| Missing | No temporal variation — single snapshot |

---

### GROUP 5: Resource Supply — Electricity
**File:** `electricity consumption data.xlsx`  
**File:** `70d066f8-2145-4b98-9e94-d7657b8a04a0.csv`

| Field | Value |
|---|---|
| Shape (XLS) | 5 rows × 5 columns |
| Columns (XLS) | City, Annual MU, Monthly kWh per consumer |
| Time Series CSV | FY 2010-11 to FY 2022-23 (13 years) |
| Time Series Cols | Year, Demand (Rs Cr), Collection (Rs Cr), Consumers (lakhs), Metered Consumption (MU), Energy Input (MU) |
| Format Issues | Unnamed columns in XLSX; units mixed (MU, Rs Cr, Lakhs) |
| Use | Set dynamic electricity supply per timestep; model yearly variance |

---

### GROUP 6: Resource Supply — Food (Ration System)
**Files:** `feb -apr 2025 (Rice).xlsx`, `feb -apr 2025 (Wheat).xlsx`, `feb -apr 2025 (Dal).xlsx`

| Field | Value |
|---|---|
| Shape | Each ~5 rows (summary) × 15 columns |
| Content | Ration distribution by taluk for 3 months (Feb–Apr 2025) |
| Format Issues | Non-standard headers (`February :`, `Unnamed: 1` etc.); multi-period merged cells |
| Use | Set food supply per timestep; calibrate poor-household food allocation volume |

---

### GROUP 7: Consumer Behaviour
**File:** `consumer details per capita.xlsx`

| Field | Value |
|---|---|
| Shape | 784 rows × 5 columns |
| Columns | District, Group, Sub Group, [consumption metrics] |
| Content | Per capita consumption broken down by district and population group |
| Format Issues | Stacked sub-groups require pivoting; missing values present |
| Use | Set demand baselines per income group per resource type |

---

### GROUP 8: Micro Household Survey (HCES)
**Files:** `urban_households_full_dataset.csv`, `karnataka districts urban.csv`

| Field | Value |
|---|---|
| Shape (urban_households) | ~5.1M rows × 100+ columns |
| Shape (karnataka urban) | Large — HCES district-level micro-data |
| Source | HCES (Household Consumer Expenditure Survey) 2023-24 |
| Key Columns | Survey_Name, Year, FSU_Serial_No, Sector, State, District, Stratum, Sub_Stratum, household expenditure by item categories |
| Format Issues | 579K null values; UUID-style file names; high memory requirement |
| Use | Gold-standard ground truth for consumption calibration; validate agent demand curves |

> [!WARNING]
> `karnataka districts urban.csv` is 43 MB. Do NOT load entirely into memory in one shot — always use chunked reading (`chunksize=10000`) or filter by State=29 (Karnataka) upfront.

---

### GROUP 9: Policy Documents (PDFs — Parameter Extraction Required)

| PDF | Key Parameters to Extract |
|---|---|
| `StateWaterPolicy-English.pdf` | 135 LPCD minimum standard, water allocation norms |
| `anna_bhagya_scheme_document.pdf` | 5 kg rice/person/month free; eligibility criteria |
| `gruha_jyothi_scheeme_document.pdf` | 200 units/month free electricity for households ≤ 200 units usage |
| `Gruha-Lakshmi scheme_document.pdf` | ₹2000/month cash transfer to women head-of-household |
| `ActionplanforFloodriskmanagement2021.pdf` | Flood risk zones, infrastructure reduction %, recovery timeline |
| `Policy Revision DM2020.pdf` | Disaster response thresholds, emergency supply protocols |
| `Economic_Survey_2025-26_English_FinalMpdf.pdf` | State GDP, income growth rates, inflation context |
| `FHTCDataTable.pdf` | Functional household tap connections %, coverage inequity |
| `HCES FactSheet 2023-24.pdf` | National per-capita consumption benchmarks |

---

### GROUP 10: Pre-Compiled / Auxiliary Data

| File | Content | Issue |
|---|---|---|
| `supply_data.csv` | Pre-aggregated energy + food supply per city | Auto-generated — will be regenerated by processing pipeline |
| `RS_Session_260_AU_1773_1.csv` | Parliamentary ration allocation by state, 3 years | India-level, only Karnataka row useful |
| `880d7e38-82e9-41f7-98b9-f92dea3ef0f0.csv` | Bangalore sewage infrastructure stats | Static reference, not for dynamic modelling |

---

## Files to Delete

Run this to clean duplicates:

```bash
# In DATASETS folder
del "per capita income final (1).xlsx"
del "urban_households_full_dataset 2.csv"
```

---

## Overall Data Assessment

| Dimension | Status |
|---|---|
| Demographic anchoring | ✅ PCA 2011 covers all 5 target cities |
| Income distribution | ✅ Per-capita district income available |
| Agent class structure | ✅ Ration cards define poor / BPL / APL split |
| Water supply | ✅ City-level snapshot; needs temporal extension |
| Electricity supply | ✅ 13-year time-series and city snapshots available |
| Food/ration supply | ✅ Recent (2025) taluk-level distribution data |
| Household behaviour | ✅ HCES 5.1M rows — strong calibration base |
| Shock parameters | ✅ Flood action plan and DM policy PDFs |
| Policy parameters | ✅ 4 scheme documents cover subsidy rules |
| Temporal dynamics | ⚠️ Mostly point-in-time; electricity has time-series |
| Urban district granularity | ✅ Available down to Taluk level |
