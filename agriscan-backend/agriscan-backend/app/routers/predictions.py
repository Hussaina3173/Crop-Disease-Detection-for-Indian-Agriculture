from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app import models, schemas
from app.utils.ml_model import predict, get_recommendations

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _to_response(prediction: models.Prediction) -> schemas.PredictionResponse:
    return schemas.PredictionResponse(
        id=prediction.id,
        upload_id=prediction.upload_id,
        crop_name=prediction.crop_name,
        disease_name=prediction.disease_name,
        is_healthy=prediction.is_healthy,
        confidence=prediction.confidence,
        recommendations=(prediction.recommendations or "").split("\n") if prediction.recommendations else [],
        model_version=prediction.model_version,
        created_at=prediction.created_at,
    )


@router.post("/analyze/{upload_id}", response_model=schemas.PredictionResponse, status_code=201)
def analyze_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    upload = (
        db.query(models.Upload)
        .filter(models.Upload.id == upload_id, models.Upload.user_id == current_user.id)
        .first()
    )
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found.")

    result = predict(upload.file_path)
    recommendations = get_recommendations(result["crop_name"], result["disease_name"], db)

    prediction = models.Prediction(
        upload_id=upload.id,
        crop_name=result["crop_name"],
        disease_name=result["disease_name"],
        is_healthy=result["is_healthy"],
        confidence=result["confidence"],
        model_version=result["model_version"],
        recommendations="\n".join(recommendations),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return _to_response(prediction)


@router.get("/history", response_model=list[schemas.PredictionResponse])
def prediction_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    predictions = (
        db.query(models.Prediction)
        .join(models.Upload)
        .filter(models.Upload.user_id == current_user.id)
        .order_by(models.Prediction.created_at.desc())
        .all()
    )
    return [_to_response(p) for p in predictions]


@router.post("/{prediction_id}/feedback")
def submit_feedback(
    prediction_id: str,
    payload: schemas.FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    prediction = (
        db.query(models.Prediction)
        .join(models.Upload)
        .filter(models.Prediction.id == prediction_id, models.Upload.user_id == current_user.id)
        .first()
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found.")

    prediction.user_feedback = "correct" if payload.is_correct else "incorrect"
    db.commit()
    return {"message": "Feedback recorded. Thanks — this helps improve the model."}
