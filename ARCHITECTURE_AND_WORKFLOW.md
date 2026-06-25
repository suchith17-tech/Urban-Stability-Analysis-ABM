# Urban Stability Simulation: Architecture and Workflow

This document provides a comprehensive overview of the Mesa-based Multi-Agent Framework for Urban Socio-Economic Stability Evaluation. It details the internal workings, agent distribution, resource allocation, policy dynamics, and systemic coordination, serving as a blueprint for understanding the current state and scaling it to incorporate real-world empirical data.

---

## 1. System Architecture
The system is built on the **Mesa Agent-Based Modeling (ABM) framework** in Python. The architecture emphasizes modularity, separating the core simulation from distinct functionalities like shock injection, policy enforcement, and stability calculation.

### Core Modules
1. **`UrbanStabilityModel` (`model/urban_model.py`)**: The central engine orchestrating time steps, managing the agent list, collecting data, and tracking system collapse.
2. **`UrbanAgent` (`agents/urban_agent.py`)**: Represents individual household entities, managing their personal income, trust, demand computation, and trust updates.
3. **`ResourcePool` (`model/resource_pool.py`)**: Manages the global resource supply and executes the allocation algorithms based on aggregate demand.
4. **`PolicyEngine` (`model/policy_engine.py`)**: Responsible for altering economic conditions (pricing) and enforcing regulatory limits (caps) dynamically.
5. **`ShockModule` (`modules/shock_module.py`)**: Introduces configurable external stressors to evaluate system resilience.
6. **`StabilityAnalyzer` (`modules/stability_analyzer.py`)**: Calculates the composite **Urban Stability Index (USI)** and its sub-components evaluating resource sufficiency, cooperation, inequality, and oscillation.
7. **`Interaction Network` (`modules/interaction_network.py`)**: Manages the social topology of the city via a connected mathematical graph.

---

## 2. Agent Composition & Distribution

The system features generic `UrbanAgent` entities, distributed with specific economic and social characteristics.

*   **Total Population**: Controlled by `num_agents` (default 100).
*   **Income Distribution**: 
    Each agent's income is initialized using a **lognormal distribution** (`mean=2`, `sigma=1`). This accurately mimics real-world wealth distribution where a majority have moderate incomes and a minority possess extreme wealth, resulting in a positively skewed distribution.
*   **Initial Trust**:
    Trust (representing an agent's likelihood to cooperate vs. hoard) is initialized via a **uniform distribution** across a specified range (e.g., bounds 0.3 to 0.9).
*   **Interaction Network Topology**:
    Agents are connected via an **Erdős–Rényi random graph** (`avg_degree=8`), ensuring the network forms a single large connected component. This simulates random social or geographical connections where agents influence each other's behaviour.

---

## 3. Step-by-Step Workflow & Coordination

Each tick of the simulation loop (`step()`) processes identical sequential logic to represent a single timeframe. The sequence guarantees causal consistency (e.g., policies affect prices before agents calculate demand, agents calculate demand before resources are allocated).

### The Execution Workflow
1.  **Apply Shock**: The `ShockModule` checks the current step against `t_shock`. If a shock is triggered, system macro-parameters (like total supply or global trust) are immediately reduced.
2.  **Determine Subsidy Eligibility**: The `PolicyEngine` evaluates all agent incomes and tags those in the lowest percentile (e.g., bottom 30%) for targeted subsidies.
3.  **Compute Agent Demand**: Agents calculate how much resource they *want*.
4.  **Allocate Resources**: `ResourcePool` takes all computed demands and distributes the hard supply accordingly.
5.  **Apply Consumption Cap**: `PolicyEngine` enforces maximum resource limits on the allocated amounts. If an agent received more than the cap, the excess is simply lost (not redistributed).
6.  **Update Agent Trust**: Agents evaluate how well the system served them and update their personal trust levels, smoothing it with peer influence.
7.  **Calculate System Stability (USI)**: `StabilityAnalyzer` assesses the outcomes of the allocations and outputs the systemic health index.
8.  **Collapse Detection**: The model evaluates if the USI has fallen below terminal thresholds for a consecutive number of steps, triggering simulation termination if so.
9.  **Data Collection**: The Mesa `DataCollector` captures all relevant metrics.

---

## 4. Mechanisms of Demand, Allocation & Consumption

### How Demand is Formulated
An agent's resource demand is an economic representation of purchasing power and psychological state.
`Demand = (Income * Trust) / Effective_Price`
*   **Higher Income**: Higher capacity to demand resources.
*   **Higher Trust**: Increased demand (acting here as a proxy for engagement with the system). 
*   **Effective Price**: Alters demand capability based on market or policy changes.

### How Resources are Allocated
Managed by the `ResourcePool`.
1.  **Case 1: Sufficiency.** If `Total Demand <= Total Supply`
    Every agent gets exactly what they demanded (`allocated = demand`).
2.  **Case 2: Scarcity.** If `Total Demand > Total Supply`
    A proportional allocation is executed. 
    `Agent Allocation = (Agent Demand / Total Demand) * Total Supply`
    *Impact: Wealthier agents (who demand more) will secure a larger absolute share of the scarce resources, naturally driving inequality during crises.*

---

## 5. Policy Mechanisms

The `PolicyEngine` dynamically intervenes in the aforementioned supply-demand pipeline. Policies are individually toggled in `config.py`.

1.  **Pricing Multiplier**: 
    Globally alters the `base_price` of resources (e.g., `value: 1.5` means 50% inflation). Decreases everyone's effective demand.
2.  **Targeted Subsidy**:
    Aimed at the most vulnerable. Agents below a certain `threshold_percentile` (e.g., 30th percentile) receive a `rate` reduction in effective price (e.g., 30% off). This artificial boost helps them secure a larger slice of the proportional allocation during scarcity.
3.  **Consumption Cap**:
    A hard limit (`cap_value`) on final allocated resources per agent. Acts as an anti-hoarding mechanism, preventing extremely high-income agents from monopolizing resources, thereby indirectly protecting the allocation of poorer agents during scarcity.

---

## 6. Shocks and System Perturbations

The `ShockModule` allows for stress-testing the urban system. Shocks can be one-shot (recovering naturally if supply is restocked) or persistent.

*   **Resource Scarcity**: Instantaneously reduces the `total_supply` of the model by a `magnitude` fraction (e.g., 0.5 reduces supply by 50%).
*   **Trust Breakdown**: Instantaneously reduces every agent's uniform trust by a `magnitude` fraction, simulating a panic or social crisis.

---

## 7. The Urban Stability Index (USI)

The health of the system is tracked mathematically via the `StabilityAnalyzer`, yielding a composite USI score (0.0 to 1.0) based on four weighted components (typically 25% each):

1.  **Resource Sufficiency ($S_R$)**: $\min( \frac{\text{Total Allocated}}{\text{Total Demand}}, 1.0 )$. Measures the macro ability of the city to satisfy aggregate needs.
2.  **Cooperation Ratio ($C$)**: The mean Trust across all agents. Models social cohesion.
3.  **Inequality Stability ($S_I$)**: $1 - \text{Gini}(\text{Allocations})$. 1.0 represents perfect equality in how resources were currently consumed; drops closer to 0 when few agents consume the vast majority.
4.  **Oscillation Stability ($S_O$)**: $1 / (1 + \text{Variance}(\text{USI}_{history}))$. Penalizes violent swings in systemic health; highly volatile systems score lower on stability.

### Trust Evolution (Feedback Loop)
At the end of a timestep, an agent updates their trust based on:
`new_trust = \alpha * (Personal Satisfaction) + (1 - \alpha) * (Mean Neighbor Trust)`
Where `Personal Satisfaction = min(Allocated / Demand, 1.0)`.
This creates a powerful feedback loop: if resources are scarce or severely unequally distributed through proportional allocation, poor agents get low satisfaction $\rightarrow$ their trust drops $\rightarrow$ neighbor trust drops $\rightarrow$ social cohesion component ($C$) of the USI collapses.

---

## Scaling to Real Data (Next Steps)
To scale this architecture to empirical data (e.g., Census Data), the immediate modifications required are:
1.  **Agent Initialization**: Replace the lognormal distribution of `Agent.income` with synthetic population generation tied to real demographic and socio-economic distributions (e.g., true Gini index of the target city).
2.  **Network Topology**: Move from an abstract Erdős–Rényi graph to spatially-embedded or socio-economically-segregated networks based on actual ward/district-level data.
3.  **Dynamic Supply**: Modify `total_supply` from a static integer to a time-series dataset reflecting actual water, electricity, or economic throughput metrics.
