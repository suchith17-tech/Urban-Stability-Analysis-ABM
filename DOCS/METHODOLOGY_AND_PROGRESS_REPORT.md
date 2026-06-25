# Urban Socio-Economic Stability Simulation
## **Project Progress & Methodology Report (Phases 1–5)**

**Project Goal:** To construct a highly realistic, data-driven Agent-Based Model (ABM) evaluating the Urban Stability Index (USI) of five representative Karnataka cities under various climatic and economic shocks, validating the protective efficacy of official government interventions.

This document summarizes the exact datasets, methodologies, and engineering architectures completed to date to bring the simulation to a fully production-ready, data-driven state.

---

### **1. Phase 1: Foundational Demographics & Income**
_Objective: Ground the ABM agents in real urban population statistics instead of synthetic assumptions._

*   **City Profiling:** Configured the environment for 5 major cities representing diverse geographic and economic profiles across Karnataka: **Bengaluru** (IT hub), **Mysuru** (Heritage/Tourism), **Mangaluru** (Coastal), **Hubballi-Dharwad** (Commercial/Semi-Arid), and **Belagavi** (Agrarian/Military).
*   **Demographic Sourcing:** Built automated extraction scripts (`01_process_pca.py`) parsing the 2011 Primary Census Abstract (PCA) to extract true baselines for population, total households, average household sizes, and literacy rates per city.
*   **Agent Stratification:** Processed historical state Ration Card distributions (`03_process_ration_cards.py`) to accurately segment the urban population into three specific agent tiers:
    1.  `extreme_poor` (AAY cardholders)
    2.  `bpl_poor` (BPL cardholders)
    3.  `non_poor` (APL cardholders / No card)
*   **Income Mechanics:** Abandoned flat per-capita income averages in favor of fitting rigorous **lognormal distributions** per class tier (`02_process_income.py`). This ensures accurate long-tail wealth inequality (Gini) representation natively at initialization.

---

### **2. Phase 2: Dynamic Resource Supply Processing**
_Objective: Convert abstract resource tokens into realistic monthly physical units (Litres, kWh, Kg)._

*   **Water Supply (`04_process_water.py`):** Derived base supply from official MLD (Million Litres per Day) benchmarks, then applied **Seasonal Hydrological Multipliers**. Instead of static supply, water dynamically dips during summer (Mar–May) and swells during monsoons, creating rolling baselines for the ABM.
*   **Electricity Supply (`05_process_electricity.py`):** Configured utility supply curves integrating random mathematical volatility (±5–10% stochastic noise) to mimic real-world grid intermittency and seasonal consumption surges.
*   **Food (PDS) Supply (`06_process_food_ration.py`):** Processed raw Public Distribution System (PDS) government allocation spreadsheets (Quintals/district) and mapped them cleanly via core-taluk conversions to represent guaranteed food density (Kg per household) within the urban centers.

---

### **3. Phase 3: Demand Calibration & Interaction Matrix**
_Objective: Move away from arbitrary demand functions by mapping agent logic to the Household Consumption Expenditure Survey (HCES)._

*   **Physical Demand Mapping:** Converted statistical MPCE (Monthly Per Capita Expenditure) percentiles into physical per-household units of consumption (`07_process_hces.py`).
    *   *Result:* Poor agents demand more PDS food; affluent agents register significantly higher electricity and water demand, matching real utility tiers.
*   **Resource Coupling Matrix (`08_resource_interactions.py`):** Formulated an advanced matrix to simulate cascading failures. Instead of independent shortages, resources impact each other:
    *   `water_deficit_on_food_utilization = 0.715` (Water scarcity limits cooking and sanitation)
    *   `electricity_deficit_on_water_pumping = 0.458` (Power cuts reduce overhead tank pumping)
    *   `food_deficit_on_trust_drop = 0.638` (Food insecurity acts as a direct vector for public trust collapse)

---

### **4. Phase 4: Policy & Shock Parameter Extraction**
_Objective: Eliminate all 'placeholder' parameters by extracting direct logic from official Government PDF documents._

*   **Data Extraction Scripts (`10_extract_pdf_params.py`):** Engineered logic to parse unalterable Karnataka state PDFs (e.g., Flood Risk Management, Economic Surveys, Gruha Jyothi/Lakshmi scheme GOs). Every applied value in the configuration JSON cites the exact PDF and section/page number.
*   **City-Specific Geography Shocks:** Uniform shock testing was completely redesigned. Vulnerability parameters reflect geological reality.
    *   *Mangaluru:* Assumes a severe 40% initial water hit from floods with a 5-month gradual recovery curve.
    *   *Hubballi-Dharwad:* Assumes high 50% drought exposure with protracted latency.
*   **Gradual Recovery Modeling:** Implemented temporal arrays (e.g., `[0.6, 0.7, 0.85, 1.0]`) allowing the simulation to model how a city slowly digs out of a crisis over multiple steps, rather than a jarring single-step binary reset.

---

### **5. Phase 5: Agent-Based Core Refactoring (Simulation Integration)**
_Objective: Overhaul the MESA `UrbanStabilityModel` codebase to flawlessly ingest and execute the data pipeline._

*   **`config_loader.py` Bridge:** Created a robust transformation layer linking the data-pipeline JSON strictly into pythonic objects required by the ABM engine.
*   **Smart `ResourcePool` Allocation:** Rewrote the allocation engine into a multi-pool system representing Water, Electricity, and Food. Embedded a priority distribution algorithm:
    *   *PDS Food gets assigned with priority targeted to `extreme_poor` and `bpl_poor`*.
    *   *Market allocations are distributed proportionally*.
    *   *Resource deficit cascading coefficients dynamically penalize secondary resources post-allocation*.
*   **Operational Policy Engine (`policy_engine.py`):** Programmed the operational business logic for actual safety nets:
    *   `Anna Bhagya`: BPL agents strictly receive a locked baseline food floor regardless of market failure.
    *   `Gruha Jyothi`: Agent electricity billing metrics drop to zero dynamically if usage remains ≤ 200 units, increasing agent trust loops.
    *   `Gruha Lakshmi`: Applies immediate monthly purchasing power inflation mimicking the ₹2000 DBT injection.
*   **Trust Mechanics & Stabilization Fixes:** Formalized a psychological Trust threshold system inside `UrbanAgent`. Trust relies mathematically on Resource Satisfaction + Peer Influence + Policy Access. Correctly fixed the Urban Stability Index (USI) formulations ensuring `S_R` (Resource Sufficiency) evaluates independently of inequality markers. 

---

### **Current Project Stage**
As of the current sprint, **the data acquisition, foundational pipeline, configuration structuring, and ABM model engineering are 100% complete, verified, and integrated.** The engine runs end-to-end natively without crashes while processing distinct socio-demographic inputs from the 5 respective cities.

**Next Immediate Stage:** *Phase 6 — Structured Experimentation and Results Analysis.*
We are now positioned to automate the execution of 6 separate shock and policy scenarios to harvest analytical output data (USI trajectories, Gini coefficients) required for the ultimate research report/thesis.
