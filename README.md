# Crop Disease Detection for Indian Agriculture

This project is a Flask web application for classifying crop and disease from a leaf image. The browser never invents a diagnosis: it sends the selected image to `/api/analyze`, which uses the trained model artifact in `models/`.

## Run the application

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Authentication uses a local SQLite database. Register with a name, a valid email or mobile number, and a password of at least 8 characters. Login accepts either the registered email or mobile number. Password-reset requests create a secure reset token; actual Gmail or SMS delivery requires SMTP or Twilio credentials configured on the server.

The reset screen has separate Email and Mobile SMS choices. Gmail SMTP is free within Gmail sending limits. Enable 2-Step Verification on the Gmail account, create a Google App Password, and add `GMAIL_USERNAME` and `GMAIL_APP_PASSWORD` to `.env` (never use your normal Gmail password). Restart Flask after changing `.env`; the UI reports whether delivery succeeded. SMS remains optional and requires Twilio.

## Configure the Gemini chatbot

Create a Gemini API key in Google AI Studio and set it only in the server environment:

```powershell
$env:GEMINI_API_KEY = 'your-key-here'
$env:GEMINI_MODEL = 'gemini-3.6-flash'
python app.py
```

The same values are listed in [.env.example](.env.example). Do not put the real key in that file or in frontend code. Restart Flask after setting environment variables because they are read when the server starts.

The browser calls `/api/chat`; the key is never exposed to frontend JavaScript. `/api/chat/kpis` reports total questions, successful Gemini answers, errors, and average latency. Chat logs are written locally to `data/chat_metrics.jsonl` and ignored by Git.

## Train the model

The repository does not include image data, so a model cannot be trained or an honest accuracy number produced until a labeled dataset is supplied. PlantVillage-style folders are supported:

```text
data/plantvillage/Tomato___Early_blight/image-001.jpg
data/plantvillage/Tomato___healthy/image-002.jpg
```

After placing one or more datasets locally, see [datasets.md](datasets.md) for recommended sources and licensing notes:

```powershell
python train.py --data-dir data/plantvillage --data-dir data/plantdoc --data-dir data/paddy --epochs 12
```

The script writes `models/crop_disease.keras`, `models/labels.json`, and `models/metrics.json`. The reported `validation_accuracy` is shown by the training command and returned by `/api/status`. Until this artifact exists, image analysis uses Gemini Vision when `GEMINI_API_KEY` is configured. Gemini confidence is an estimate, not a validated model accuracy. Treatment suggestions are conservative guidance and are not a substitute for an agricultural expert or product label.

Python 3.11 or 3.12 is recommended for the TensorFlow dependency. The current Python 3.14 installation may require a compatible TensorFlow release or a separate supported virtual environment.

## Deploy the complete app for free

The included [render.yaml](render.yaml) deploys the frontend and Flask API together on Render. Netlify alone cannot run this Python backend, TensorFlow inference, SQLite authentication, Gemini calls, or Gmail SMTP.

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint**, connect the repository, and apply `render.yaml`.
3. Add `GEMINI_API_KEY`, `GMAIL_USERNAME`, and `GMAIL_APP_PASSWORD` as secret environment variables in the Render dashboard.
4. Deploy and open the generated `onrender.com` URL.

The free Render service may sleep when idle. SQLite and local chat logs are instance-local and can be lost when the service is redeployed; use a managed Postgres database before treating this as production authentication. Do not commit `.env` or any secret values.
