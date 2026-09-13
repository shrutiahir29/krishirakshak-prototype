from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import DiseaseDetectionResult
from app.services import disease_detection_service

router = APIRouter(prefix="/api/disease-detection", tags=["disease-detection"])


@router.post("/detect", response_model=DiseaseDetectionResult)
async def detect_disease(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    return disease_detection_service.detect_disease(image_bytes)
