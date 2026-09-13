"""
Treatment Recommendation Service
===================================
Simple lookup table: pest/disease name -> recommended treatment + timing.
Sourced from standard agricultural extension guidelines.

Used by:
  - Pest Risk module, when risk crosses "High"/"Severe"
  - Disease Detection module, once a CNN identifies a problem from a photo

This is deliberately a plain dict so it's trivial to extend with real data.
"""

TREATMENT_LOOKUP = {
    "Bollworm (Helicoverpa armigera)": {
        "treatment": "Spray Emamectin benzoate 5% SG @ 0.4g/L or install pheromone traps (5/acre) for monitoring; encourage natural predators like Trichogramma.",
        "timing": "Apply at early larval stage (before boll entry), preferably early morning or evening.",
    },
    "Brown Planthopper": {
        "treatment": "Apply Imidacloprid 17.8% SL @ 0.3ml/L or Buprofezin 25% SC; drain excess field water to reduce humidity at the base.",
        "timing": "Apply as soon as hoppers are seen at the base of tillers, before population exceeds economic threshold (~10-15/hill).",
    },
    "Girdle Beetle": {
        "treatment": "Spray Chlorantraniliprole 18.5% SC @ 0.3ml/L; remove and destroy infested/girdled stems.",
        "timing": "Apply at first sign of stem girdling, typically 3-4 weeks after sowing.",
    },
    "Aphids": {
        "treatment": "Spray Imidacloprid 17.8% SL @ 0.5ml/L or use neem oil (5%) for low-severity cases; conserve ladybird beetle populations.",
        "timing": "Apply when aphid colonies are visible on new growth, before curling of leaves becomes severe.",
    },
    "Generic foliar pest/disease pressure": {
        "treatment": "Conduct a field inspection to confirm the specific pest/disease; consider a broad-spectrum neem-based spray as a first, low-risk response.",
        "timing": "As soon as symptoms are confirmed; avoid spraying during flowering to protect pollinators.",
    },
    # Common PlantVillage-style disease labels (for the CNN module, once built)
    "Tomato Late Blight": {
        "treatment": "Apply Mancozeb 75% WP @ 2.5g/L or Chlorothalonil; remove and destroy infected foliage.",
        "timing": "Apply preventively before humid/rainy periods, and immediately on first symptom sighting.",
    },
    "Tomato Early Blight": {
        "treatment": "Apply Mancozeb or Copper oxychloride @ 2.5-3g/L; ensure adequate plant spacing for airflow.",
        "timing": "Apply at first spotting of lower-leaf lesions.",
    },
    "Potato Late Blight": {
        "treatment": "Apply Metalaxyl + Mancozeb combination fungicide; avoid overhead irrigation.",
        "timing": "Apply preventively ahead of cool, wet weather forecasts.",
    },
}

DEFAULT_TREATMENT = {
    "treatment": "No specific treatment on file — consult local Krishi Vigyan Kendra (KVK) or agricultural extension officer.",
    "timing": "As soon as possible after confirmed identification.",
}


def get_treatment(problem_name: str) -> dict:
    return TREATMENT_LOOKUP.get(problem_name, DEFAULT_TREATMENT)
