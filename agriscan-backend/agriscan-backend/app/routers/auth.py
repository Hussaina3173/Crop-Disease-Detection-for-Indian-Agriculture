from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app import models, schemas, security
from app.utils.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = models.User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        farm_location=payload.farm_location,
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # TODO: send a verification email/OTP here before is_verified is set true.
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    if not user or not security.verify_password(payload.password, user.password_hash):
        # Same error for "no such user" and "wrong password" — don't reveal which.
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been disabled.")

    return schemas.TokenResponse(
        access_token=security.create_access_token(user.id),
        refresh_token=security.create_refresh_token(user.id),
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    # Always return the same response whether or not the email exists,
    # so attackers can't use this endpoint to enumerate registered users.
    if user:
        raw_token, token_hash, expires_at = security.generate_reset_token()
        reset_entry = models.PasswordResetToken(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at
        )
        db.add(reset_entry)
        db.commit()
        send_password_reset_email(user.email, raw_token)

    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = security.hash_reset_token(payload.token)

    reset_entry = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == token_hash)
        .first()
    )

    if (
        not reset_entry
        or reset_entry.used
        or reset_entry.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user = db.query(models.User).filter(models.User.id == reset_entry.user_id).first()
    user.password_hash = security.hash_password(payload.new_password)
    reset_entry.used = True
    db.commit()

    return {"message": "Password has been reset. You can now log in."}


@router.post("/change-password")
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not security.verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    current_user.password_hash = security.hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated."}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user
