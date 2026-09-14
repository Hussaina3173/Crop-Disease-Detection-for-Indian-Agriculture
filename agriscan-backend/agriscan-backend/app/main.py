from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import auth, uploads, predictions

# Creates tables if they don't exist yet.
# For anything beyond local development, use Alembic migrations instead
# of relying on this — it won't handle schema changes to existing tables.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AgriScan API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves locally-stored images at /uploads/<filename> (dev only —
# in production, images should be served from S3/CDN, not this app).
if settings.storage_backend == "local":
    app.mount("/uploads", StaticFiles(directory=settings.local_upload_dir), name="uploads")

app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(predictions.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
