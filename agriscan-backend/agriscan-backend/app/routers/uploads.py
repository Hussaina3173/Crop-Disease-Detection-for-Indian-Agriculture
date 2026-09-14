from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app import models, schemas
from app.utils.storage import save_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=schemas.UploadResponse, status_code=201)
async def create_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contents = await file.read()

    try:
        file_path, file_url = save_upload(file, contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    upload = models.Upload(
        user_id=current_user.id,
        file_path=file_path,
        file_url=file_url,
        original_filename=file.filename,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return upload


@router.get("", response_model=list[schemas.UploadResponse])
def list_uploads(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Upload)
        .filter(models.Upload.user_id == current_user.id)
        .order_by(models.Upload.uploaded_at.desc())
        .all()
    )


@router.delete("/{upload_id}", status_code=204)
def delete_upload(
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

    db.delete(upload)
    db.commit()
