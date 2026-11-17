from typing import List, Dict, Any
import pandas as pd
from database import get_comparison_data, get_vehicle_details
from llm_engine import generate_response


def generate_ai_vehicle_comparison(model_names: List[str]) -> str:
    """
    Generate an in-depth AI comparison analysis for selected vehicles
    grounded strictly on database specifications.
    """
    if not model_names or len(model_names) < 2:
        return "Please select at least two vehicle models to compare."

    df_comp = get_comparison_data(model_names)
    if df_comp.empty:
        return "Vehicle comparison data could not be retrieved from the database."

    # Format side-by-side comparison summary
    details_list = []
    for _, row in df_comp.iterrows():
        min_p = row.get("min_price", 0) or 0
        max_p = row.get("max_price", 0) or 0
        price_str = f"₹{min_p:,.0f} - ₹{max_p:,.0f}" if min_p > 0 else "Price on inquiry"
        
        detail = (
            f"MODEL: {row['brand_name']} {row['model_name']}\n"
            f"- Price Range: {price_str}\n"
            f"- Fuel Options: {row.get('fuel_types', 'N/A')}\n"
            f"- Transmission Options: {row.get('transmissions', 'N/A')}\n"
            f"- Mileage Range: {row.get('min_mileage', 'N/A')} - {row.get('max_mileage', 'N/A')} kmpl\n"
            f"- Engine Displacement: {row.get('min_engine_cc', 'N/A')} - {row.get('max_engine_cc', 'N/A')} cc\n"
            f"- Seating Capacity: {row.get('seating_capacity', 5)} seats\n"
            f"- Total Variants in DB: {row.get('total_variants', 0)}"
        )
        details_list.append(detail)

    comparison_context = "\n\n".join(details_list)

    prompt = f"""You are AutoVerse AI, a senior automotive journalist and automotive test engineer.
Compare the following vehicles side-by-side using ONLY the verified database specifications below:

{comparison_context}

TASK:
Write an authoritative, fair, and comprehensive automotive comparison report:
1. Overview & Positioning: How these vehicles compare in the market segment.
2. Powertrain & Performance: Engine options (displacement), transmission choices, and performance character.
3. Fuel Efficiency & Running Costs: Compare mileage figures, fuel alternatives, and long-term running economy.
4. Value for Money & Pricing: Compare price spread and variant diversity.
5. Buyer Verdict: Who should buy which vehicle? (e.g. "Choose {model_names[0]} if... ; Choose {model_names[1]} if...").

GROUNDING RULE: Rely strictly on the provided specs. Do not invent numbers."""

    response = generate_response(prompt, temperature=0.3)
    return response
