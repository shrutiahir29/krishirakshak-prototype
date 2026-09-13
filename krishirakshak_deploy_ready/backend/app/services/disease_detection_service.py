"""
Disease/Pest Detection Service (Prototype Stub)
==================================================
PROTOTYPE NOTE: A real MobileNet/EfficientNet model fine-tuned on
PlantVillage needs a training pipeline (dataset download, transfer learning,
export to ONNX/TorchScript, etc.) which is a separate, heavier build step
from this prototype.

For now, this module exposes the REAL final interface (image in -> detected
problem + confidence + treatment out) with a deterministic placeholder
"model" so the full UI flow (upload -> detect -> treatment -> historical
context) can be demoed end-to-end today. Swapping in a trained model later
only means replacing `_run_inference()` - the router/response contract and
the entire frontend stay the same.
"""

import hashlib
import random
from typing import Optional

from app.models.schemas import DiseaseDetectionResult
from app.services.treatment_service import get_treatment

# Stand-in "class list" - matches common PlantVillage-style labels
DEMO_CLASSES = [
    "Tomato Late Blight",
    "Tomato Early Blight",
    "Potato Late Blight",
    "Healthy Leaf",
    "Bollworm (Helicoverpa armigera)",
    "Aphids",
]


def _run_inference(image_bytes: bytes) -> tuple[str, float]:
    """
    PLACEHOLDER inference. Deterministic (hash-based) so the same image
    always returns the same result during demos, rather than pure randomness.
    Replace this function body with real model.predict(image) once trained.
    """
    h = hashlib.sha256(image_bytes).hexdigest()
    seed = int(h[:8], 16)
    rng = random.Random(seed)

    label = rng.choice(DEMO_CLASSES)
    confidence = round(rng.uniform(68.0, 96.0), 1)
    return label, confidence


def detect_disease(image_bytes: bytes, recent_pest_risk_context: Optional[str] = None) -> DiseaseDetectionResult:
    label, confidence = _run_inference(image_bytes)

    if label == "Healthy Leaf":
        return DiseaseDetectionResult(
            detected_problem="Healthy Leaf",
            confidence_pct=confidence,
            recommended_treatment="No treatment needed. Continue routine monitoring.",
            treatment_timing="N/A",
            historical_context=recent_pest_risk_context,
        )

    treatment = get_treatment(label)
    return DiseaseDetectionResult(
        detected_problem=label,
        confidence_pct=confidence,
        recommended_treatment=treatment["treatment"],
        treatment_timing=treatment["timing"],
        historical_context=recent_pest_risk_context,
    )
