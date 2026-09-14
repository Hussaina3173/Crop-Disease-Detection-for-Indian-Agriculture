import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE_MB = 10


def _validate_image(file: UploadFile, contents: bytes):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Only JPG and PNG images are allowed.")
    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"Image must be under {MAX_FILE_SIZE_MB}MB.")


def save_upload(file: UploadFile, contents: bytes) -> tuple[str, str]:
    """
    Saves the uploaded image and returns (file_path, file_url).
    Swap the body of this function for an S3 upload when STORAGE_BACKEND=s3 —
    the route code calling this doesn't need to change.
    """
    _validate_image(file, contents)

    ext = Path(file.filename).suffix.lower() or ".jpg"
    unique_name = f"{uuid.uuid4()}{ext}"

    if settings.storage_backend == "local":
        upload_dir = Path(settings.local_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / unique_name
        with open(file_path, "wb") as f:
            f.write(contents)
        file_url = f"/uploads/{unique_name}"
        return str(file_path), file_url

    if settings.storage_backend == "s3":
        # Example shape for when you wire this up:
        #
        # import boto3
        # s3 = boto3.client(
        #     "s3",
        #     aws_access_key_id=settings.aws_access_key_id,
        #     aws_secret_access_key=settings.aws_secret_access_key,
        #     region_name=settings.aws_region,
        # )
        # key = f"uploads/{unique_name}"
        # s3.put_object(Bucket=settings.aws_s3_bucket, Key=key, Body=contents,
        #               ContentType=file.content_type)
        # file_url = f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
        # return key, file_url
        raise NotImplementedError("S3 storage backend is not wired up yet — see comment above.")

    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend}")
