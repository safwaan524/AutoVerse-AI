from typing import Dict, Any, List, Optional
import pandas as pd
from database import get_recommendation_candidates
from llm_engine import generate_response


def generate_recommendation_rationale(
    candidates_df: pd.DataFrame,
    budget: float,
    fuel_preference: str,
    seats: int,
    usage: str,
    priority: str
) -> str:
    """
    Use Llama 3 to generate structured, explainable AI recommendation rationale
    grounded on the retrieved database records.
    """
    if candidates_df.empty:
        return (
            "No vehicles matching your exact criteria were found in the database. "
            "Consider slightly increasing your budget or selecting 'Any' for fuel or transmission."
        )

    # Format candidates list
    cars_context = []
    for idx, row in candidates_df.iterrows():
        car_info = (
            f"- Model: {row['brand']} {row['model']} (Variant: {row['variant']})\n"
            f"  Fuel: {row['fuel_type']}, Transmission: {row['transmission']}\n"
            f"  Engine: {row['engine_cc']} cc, Mileage: {row['mileage_kmpl']} kmpl, Seats: {row['seats']}\n"
            f"  Ex-Showroom Price: ₹{row['ex_showroom_inr']:,.0f}, On-Road Price: ₹{row.get('on_road_inr', 0):,.0f}"
        )
        cars_context.append(car_info)

    cars_text = "\n\n".join(cars_context)

    prompt = f"""You are AutoVerse AI, a senior automotive advisor.
A customer has provided the following requirements:
- Maximum Budget: ₹{budget:,.0f} ({budget/100000:.1f} Lakh)
- Fuel Preference: {fuel_preference}
- Family Size / Required Seats: {seats} seats
- Primary Usage: {usage} (e.g. City daily commute, Highway long trips, Mixed)
- Top Priority: {priority} (e.g. Fuel efficiency, Performance, Space, Value for money)

Here are the top candidate vehicles retrieved from our verified database:
{cars_text}

TASK:
Provide an explainable, structured automotive recommendation report for this customer:
1. Executive Summary: Quick analysis of their requirement and how the options align.
2. For each recommended vehicle:
   - Why it fits their specific profile (connect to their budget, usage, and priority).
   - Key strengths / advantages.
   - Any trade-offs to keep in mind.
3. Final Verdict: AutoVerse AI's top pick for this customer and why.

CRITICAL: Ground your advice strictly on the provided vehicle specifications and prices. Do not invent features or numbers."""

    response = generate_response(prompt, temperature=0.3)
    return response


def get_ai_recommendations(
    budget: float,
    fuel_preference: str = "Any",
    seats: int = 5,
    transmission: str = "Any",
    usage: str = "Mixed",
    priority: str = "Fuel Efficiency",
    limit: int = 4
) -> Dict[str, Any]:
    """
    Complete recommendation pipeline:
    1. Query database for matching candidates.
    2. Run Generative AI explanation generator.
    3. Return candidates table + AI explanation report.
    """
    candidates = get_recommendation_candidates(
        budget=budget,
        fuel_preference=fuel_preference,
        seats=seats,
        transmission=transmission,
        usage=usage,
        limit=limit
    )

    ai_rationale = generate_recommendation_rationale(
        candidates_df=candidates,
        budget=budget,
        fuel_preference=fuel_preference,
        seats=seats,
        usage=usage,
        priority=priority
    )

    return {
        "candidates": candidates,
        "ai_rationale": ai_rationale,
        "total_matches": len(candidates)
    }
