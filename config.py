CONFIG = {
    # Simulation
    "num_agents": 100,
    "num_steps": 50,
    "num_runs": 30,
    "random_seed": 42,

    # Agent
    "income_mean": 2,
    "income_sigma": 1,
    "initial_trust_range": (0.3, 0.9),
    "trust_weight_personal": 0.7,

    # Resource
    "total_supply": 2000,
    "base_price": 1.0,

    # Network
    "network_type": "erdos_renyi",
    "avg_degree": 8,

    # Policy (toggle each independently)
    "policy": {
        "pricing_multiplier": {
            "enabled": False,
            "value": 1.5
        },
        "subsidy": {
            "enabled": False,
            "rate": 0.3,
            "threshold_percentile": 30
        },
        "consumption_cap": {
            "enabled": True,
            "cap_value": 50
        }
    },

    # Shock (Phase 3)
    "shock": {
        "enabled": True,
        "type": "resource_scarcity",   # or "trust_breakdown"
        "step": 25,
        "magnitude": 0.5,
        "persistent": False
    },

    # USI Weights (Phase 3)
    "usi_weights": [0.25, 0.25, 0.25, 0.25],
    "collapse_threshold": -1,
    "collapse_consecutive_steps": 3,
    "oscillation_window": 5,
}