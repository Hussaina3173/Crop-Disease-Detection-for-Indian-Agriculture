# AgriScan Backend

FastAPI backend for the crop disease detection project: accounts, image uploads,
and disease predictions.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env with your real values
```

You'll need a PostgreSQL database running that matches `DATABASE_URL` in `.env`.
For quick local testing without installing Postgres, you can temporarily swap
`DATABASE_URL` for a SQLite URL like `sqlite:///./agriscan.db` — fine for
development, not recommended once you're storing real user data.

## Run

```bash
uvicorn app.main:app --reload
```

API docs (interactive, auto-generated): http://localhost:8000/docs

## What's implemented

- **Auth**: register, login (JWT access + refresh tokens), forgot password
  (emails a reset link — prints to console if SMTP isn't configured),
  reset password, change password, get current user.
- **Uploads**: upload an image (validated for type/size), list your uploads,
  delete an upload. Saved locally under `/uploads` by default — see
  `app/utils/storage.py` to switch to S3.
- **Predictions**: run analysis on an uploaded image, view prediction history,
  submit feedback (correct/incorrect) on a prediction — useful data for
  retraining later.

## Where to plug in your trained model

`app/utils/ml_model.py` currently returns randomized placeholder results so
the whole flow (upload → analyze → store → retrieve) works end-to-end. Replace
the `predict()` function with real inference — the file has a commented
example for a Keras/TensorFlow model. Keep the same return shape
(`crop_name`, `disease_name`, `is_healthy`, `confidence`, `model_version`) and
nothing else in the app needs to change.

## Seeding the disease reference table

Recommendations shown to users come from the `diseases` table, not from the
model itself — so you can update advice text without retraining anything.
Add rows directly via SQL or a small seed script, e.g.:

```python
from app.database import SessionLocal
from app.models import Disease

db = SessionLocal()
db.add(Disease(
    crop_name="Tomato",
    disease_name="Early Blight",
    description="A fungal disease causing dark concentric spots on leaves.",
    recommendations="Remove and destroy affected leaves\nApply a copper-based fungicide\nAvoid overhead watering\nRotate crops next season",
    severity="medium",
))
db.commit()
```

## Connecting the frontend

The frontend's placeholder `runAnalysis()` should be replaced with two calls:

```js
// 1. Upload the image
const formData = new FormData();
formData.append('file', selectedFile);
const uploadRes = await fetch('http://localhost:8000/uploads', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${accessToken}` },
  body: formData
});
const upload = await uploadRes.json();

// 2. Analyze it
const predictionRes = await fetch(`http://localhost:8000/predictions/analyze/${upload.id}`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
const prediction = await predictionRes.json();
```

## Not yet included (add before going to production)

- Email/OTP verification on registration (`is_verified` field is there, but
  nothing sets it yet).
- Rate limiting on auth endpoints (e.g. via `slowapi`).
- Alembic migrations (currently using `create_all`, which won't handle
  schema changes to existing tables).
- Real S3 integration (stubbed in `app/utils/storage.py`).
