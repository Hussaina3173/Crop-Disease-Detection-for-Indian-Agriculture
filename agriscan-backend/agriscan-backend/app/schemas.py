from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = None
    farm_location: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    farm_location: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Uploads & Predictions ----------

class UploadResponse(BaseModel):
    id: str
    file_url: Optional[str]
    original_filename: Optional[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    id: str
    upload_id: str
    crop_name: Optional[str]
    disease_name: str
    is_healthy: bool
    confidence: float
    recommendations: List[str]
    model_version: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
        protected_namespaces = ()


class FeedbackRequest(BaseModel):
    is_correct: bool
