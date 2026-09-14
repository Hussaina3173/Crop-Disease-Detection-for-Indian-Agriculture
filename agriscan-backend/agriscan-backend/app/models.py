import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Float, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    farm_location = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    uploads = relationship("Upload", back_populates="user", cascade="all, delete-orphan")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reset_tokens")


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    file_path = Column(String(500), nullable=False)   # local path or S3 key
    file_url = Column(String(500), nullable=True)      # public/served URL
    original_filename = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="uploads")
    prediction = relationship("Prediction", back_populates="upload", uselist=False, cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    upload_id = Column(UUID(as_uuid=False), ForeignKey("uploads.id"), nullable=False)
    crop_name = Column(String(100), nullable=True)
    disease_name = Column(String(150), nullable=False)
    is_healthy = Column(Boolean, default=False)
    confidence = Column(Float, nullable=False)
    recommendations = Column(Text, nullable=True)   # newline-separated or JSON string
    model_version = Column(String(50), nullable=True)
    user_feedback = Column(String(20), nullable=True)  # "correct" / "incorrect" / null
    created_at = Column(DateTime, default=datetime.utcnow)

    upload = relationship("Upload", back_populates="prediction")


class Disease(Base):
    """Reference table: recommendation text is kept here, not hardcoded in the model."""
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String(100), nullable=False)
    disease_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    severity = Column(String(20), nullable=True)  # "low" / "medium" / "high"
