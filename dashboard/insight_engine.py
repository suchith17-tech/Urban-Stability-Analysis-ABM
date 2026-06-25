"""
dashboard/insight_engine.py
============================
Rule-based insight engine for the Urban Stability ABM dashboard.

Given a city, scenario, and metric snapshot, generates 2-4 human-readable
insight strings that explain WHAT the data means and WHY it happened.

Design philosophy:
  - Deterministic, rule-based (no LLM dependency — works offline)
  - Thresholds reflect the model's own trust/USI mechanics
  - Insights are tiered: primary finding → causal mechanism → policy note
"""
from __future__ import annotations


# ─────────────────────────────────────────────────────────────────────────────
# THRESHOLD CONSTANTS (aligned with StabilityAnalyzer & UrbanAgent)
# ─────────────────────────────────────────────────────────────────────────────
USI_STABLE    = 0.85
USI_MODERATE  = 0.65
USI_FRAGILE   = 0.50

TRUST_HEALTHY = 0.60
TRUST_WARNING = 0.50
TRUST_DANGER  = 0.30

GINI_LOW  = 0.005
GINI_MED  = 0.008
GINI_HIGH = 0.012

SR_FULL    = 0.90
SR_PARTIAL = 0.70


# ─────────────────────────────────────────────────────────────────────────────
# CITY PERSONALITY PROFILES (background context)
# ─────────────────────────────────────────────────────────────────────────────
CITY_PROFILES = {
    "Bengaluru": {
        "character": "high-income metropolitan hub with severe economic stratification",
        "vulnerability": "structurally fragile: high non-poor consumption crowds out PDS supply for extreme-poor",
        "strength": "largest resource base but weakest equity",
    },
    "Mysuru": {
        "character": "heritage city with moderate income diversity and strong civic trust",
        "vulnerability": "moderately sensitive to droughts due to agricultural water dependence",
        "strength": "resilient trust response — recovers quickly post-shock",
    },
    "Mangaluru": {
        "character": "coastal city with high flood exposure but equitable income distribution",
        "vulnerability": "flood-prone (40% water reduction during Jul–Sep)",
        "strength": "steep recovery curve; strong PDS uptake among BPL households",
    },
    "Hubballi-Dharwad": {
        "character": "semi-arid twin city with high drought sensitivity",
        "vulnerability": "drought exposure disproportionately affects water-food chain",
        "strength": "moderate policy responsiveness — Gruha Lakshmi uptake is high",
    },
    "Belagavi": {
        "character": "agrarian-military city with the most equitable income distribution",
        "vulnerability": "lowest absolute resource base but lowest inequality",
        "strength": "highest combined stability (USI) under stress — most resilient city",
    },
}

SCENARIO_CONTEXT = {
    "exp1_baseline":        ("baseline (no shocks)", "normal city behaviour without external stressors"),
    "exp2_flood":           ("flood shock", "monsoon water reduction (Jul–Sep) with cascading food impact"),
    "exp3_drought":         ("drought shock", "water scarcity (Mar–May) propagating to food and trust"),
    "exp4_economic":        ("economic shock", "income reduction via GDP contraction; demand compression"),
    "exp5a_shock_nopolicy": ("all shocks without policy", "worst-case — concurrent shocks with no government safety nets"),
    "exp5b_shock_policy":   ("all shocks with policy", "realistic scenario — concurrent shocks cushioned by Karnataka schemes"),
    "exp6_combined":        ("combined stress test", "full 24-month stress: all shocks + all policies active"),
}


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_insights(
    city: str,
    scenario_id: str,
    final_usi: float,
    min_usi: float,
    final_trust: float,
    final_gini: float,
    final_sr: float,
    baseline_usi: float | None = None,
) -> list[dict]:
    """
    Generate 2–4 insight dicts for the given city + scenario.

    Each insight dict:
        {
            "level":   "info" | "warning" | "critical",
            "icon":    emoji string,
            "title":   short headline,
            "body":    1–2 sentence explanation,
        }
    """
    insights = []
    profile = CITY_PROFILES.get(city, {})
    scen_label, scen_desc = SCENARIO_CONTEXT.get(
        scenario_id, (scenario_id, "custom scenario")
    )

    # ── INSIGHT 1: Overall stability assessment ──────────────────────────────
    if final_usi >= USI_STABLE:
        insights.append({
            "level": "info",
            "icon":  "🟢",
            "title": f"{city} demonstrates strong stability under {scen_label}",
            "body":  (
                f"Final USI of {final_usi:.3f} indicates the city maintained robust resource "
                f"sufficiency, high cooperation, and low inequality throughout the simulation. "
                f"{profile.get('strength', '')}"
            ),
        })
    elif final_usi >= USI_MODERATE:
        drop = f" ({(baseline_usi - final_usi):.3f} below baseline)" if baseline_usi else ""
        insights.append({
            "level": "warning",
            "icon":  "🟡",
            "title": f"{city} shows moderate stress under {scen_label}",
            "body":  (
                f"Final USI of {final_usi:.3f}{drop} reflects partial system strain. "
                f"The city's {profile.get('vulnerability', 'vulnerability profile')} "
                f"contributes to this sensitivity. Stability can be maintained but requires monitoring."
            ),
        })
    else:
        insights.append({
            "level": "critical",
            "icon":  "🔴",
            "title": f"{city} is structurally fragile under {scen_label}",
            "body":  (
                f"Final USI of {final_usi:.3f} — well below the stable threshold of {USI_STABLE}. "
                f"Root cause: {profile.get('vulnerability', 'system-level inequality')}. "
                f"This city requires targeted policy intervention, not just shock mitigation."
            ),
        })

    # ── INSIGHT 2: Trust dynamics ────────────────────────────────────────────
    if final_trust < TRUST_DANGER:
        insights.append({
            "level": "critical",
            "icon":  "⚠️",
            "title": "Trust collapse detected — systemic cooperation breakdown",
            "body":  (
                f"Average agent trust fell to {final_trust:.3f} (below the 0.3 protest-risk threshold). "
                f"In the model, trust below 0.4 triggers cooperation collapse — agents stop "
                f"moderating demand, causing a demand escalation cascade that further depletes supply. "
                f"Real-world equivalent: civil unrest, reduced institutional compliance."
            ),
        })
    elif final_trust < TRUST_WARNING:
        insights.append({
            "level": "warning",
            "icon":  "🔶",
            "title": "Trust is under stress — intervention recommended",
            "body":  (
                f"Final trust of {final_trust:.3f} is in the warning zone (0.3–0.5). "
                f"Policy benefits (Anna Bhagya, Gruha Jyothi) help rebuild trust through perceived "
                f"government responsiveness. Activating these schemes would likely push trust above 0.6 "
                f"within 3–4 months."
            ),
        })
    else:
        insights.append({
            "level": "info",
            "icon":  "🤝",
            "title": "Civic trust is healthy — social cooperation intact",
            "body":  (
                f"Trust maintained at {final_trust:.3f}, sustaining cooperative demand behaviour. "
                f"This prevents the panic-hoarding demand escalation that normally accompanies "
                f"resource scarcity, providing a natural stability buffer."
            ),
        })

    # ── INSIGHT 3: Resource sufficiency & scarcity chain ────────────────────
    if final_sr < SR_PARTIAL:
        insights.append({
            "level": "critical",
            "icon":  "🚰",
            "title": "Multi-resource scarcity — food–water–electricity chain affected",
            "body":  (
                f"Composite resource sufficiency (S_R) fell to {final_sr:.3f}, meaning less than "
                f"{final_sr*100:.0f}% of aggregate demand was met. Under this scenario ({scen_desc}), "
                f"the water→food coupling (c=0.715) amplifies initial water deficits into food "
                f"shortages, disproportionately harming BPL households who depend on PDS channels."
            ),
        })
    elif final_sr < SR_FULL:
        insights.append({
            "level": "warning",
            "icon":  "📉",
            "title": "Partial resource deficit — demand exceeds supply in peak months",
            "body":  (
                f"S_R of {final_sr:.3f} indicates supply gaps during peak months (worst: "
                f"USI dipped to {min_usi:.3f}). Resource interaction effects "
                f"(electricity→water pumping, water→food processing) magnify these gaps beyond "
                f"their individual magnitudes."
            ),
        })

    # ── INSIGHT 4: Inequality signal ─────────────────────────────────────────
    if final_gini > GINI_HIGH:
        insights.append({
            "level": "warning",
            "icon":  "📊",
            "title": "Rising consumption inequality — uneven shock absorption",
            "body":  (
                f"Consumption Gini of {final_gini:.4f} (high range) signals that non-poor agents "
                f"maintained near-full resource satisfaction while extreme-poor households faced "
                f"significant shortfalls. PDS food floors (Anna Bhagya) are the most effective "
                f"lever to compress this gap."
            ),
        })
    elif final_gini > GINI_MED:
        insights.append({
            "level": "info",
            "icon":  "⚖️",
            "title": "Moderate inequality — income groups diverging under stress",
            "body":  (
                f"Gini of {final_gini:.4f} shows a widening satisfaction gap between income groups. "
                f"This is expected under {scen_label} — poorer households have thinner buffers. "
                f"Gruha Lakshmi income transfers partially compensate by boosting purchasing power."
            ),
        })
    else:
        insights.append({
            "level": "info",
            "icon":  "✅",
            "title": "Low inequality — resource satisfaction distributed equitably",
            "body":  (
                f"Gini of {final_gini:.4f} indicates equitable resource satisfaction across income "
                f"groups. Policy interventions (PDS guarantees, income transfers) are successfully "
                f"compressing the consumption gap between rich and poor households."
            ),
        })

    return insights[:4]  # Cap at 4 insights max


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def generate_verdict(city: str, scenario_id: str, final_usi: float) -> str:
    """One-line research verdict for display in the header."""
    scen_label = SCENARIO_CONTEXT.get(scenario_id, (scenario_id,))[0]
    if final_usi >= USI_STABLE:
        return f"✅ **{city}** remains stable under **{scen_label}** (USI {final_usi:.3f})"
    elif final_usi >= USI_MODERATE:
        return f"⚠️ **{city}** shows stress under **{scen_label}** — marginal stability (USI {final_usi:.3f})"
    else:
        return f"🔴 **{city}** is fragile under **{scen_label}** — structural intervention needed (USI {final_usi:.3f})"
