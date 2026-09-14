from pathlib import Path
import json
import os
import tempfile
import time

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        if not path.exists():
            return
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))

from ml_model import DiseaseModel, ModelNotReadyError, offline_image_guess
from chat_metrics import ChatMetrics
from gemini_client import GeminiClient
from auth import AuthService
from notifications import send_email, send_sms

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
MODEL_DIR = BASE_DIR / 'models'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
app = Flask(__name__, static_folder='.', static_url_path='')
model = DiseaseModel(MODEL_DIR)
gemini = GeminiClient()
chat_metrics = ChatMetrics(BASE_DIR / 'data' / 'chat_metrics.jsonl')
auth = AuthService(BASE_DIR / 'data' / 'agriscanner.sqlite3')

CURES = {
    'healthy': ['Continue regular monitoring', 'Maintain balanced irrigation and nutrition', 'Remove heavily damaged leaves and keep tools clean'],
    'default': ['Isolate affected plants where practical', 'Remove and safely dispose of severely affected leaves', 'Use only a locally approved treatment according to its label', 'Ask a local agricultural extension officer before applying chemicals'],
    'early blight': ['Remove affected leaves', 'Improve airflow and avoid overhead watering', 'Use an approved fungicide according to the label'],
    'late blight': ['Remove infected material immediately', 'Keep foliage dry and improve field drainage', 'Use an approved blight treatment according to the label'],
    'bacterial leaf blight': ['Improve field drainage', 'Avoid excess nitrogen and overhead irrigation', 'Use resistant varieties in the next season'],
    'leaf rust': ['Monitor nearby plants for spread', 'Use a rust-resistant variety next season', 'Apply an approved fungicide according to the label'],
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get('/')
def index():
    return app.send_static_file('index.html')


@app.get('/api/status')
def status():
    result = model.status()
    result['chatbot'] = {'configured': gemini.configured, 'model': gemini.model}
    return jsonify(result)


@app.get('/api/chat/kpis')
def chat_kpis():
    return jsonify(chat_metrics.summary())


@app.post('/api/auth/register')
def register():
    body = request.get_json(silent=True) or {}
    try:
        user = auth.register(str(body.get('name', '')).strip(), str(body.get('email', '')).strip().lower(), str(body.get('mobile', '')).strip(), str(body.get('password', '')))
        return jsonify(user=user), 201
    except ValueError as error:
        return jsonify(error=str(error)), 400


@app.post('/api/auth/login')
def login():
    body = request.get_json(silent=True) or {}
    try:
        user = auth.login(str(body.get('identifier', '')).strip().lower(), str(body.get('password', '')))
        return jsonify(user=user)
    except ValueError as error:
        return jsonify(error=str(error)), 401


@app.post('/api/auth/forgot-password')
def forgot_password():
    body = request.get_json(silent=True) or {}
    destination = str(body.get('destination', '')).strip().lower()
    try:
        reset = auth.request_reset(destination)
        delivered, notification = (send_email(reset['destination'], reset['token']) if reset['channel'] == 'email' else send_sms(reset['destination'], reset['token']))
        return jsonify(message=notification, channel=reset['channel'], delivered=delivered, development_token=reset['token'] if app.debug and not delivered else None)
    except ValueError as error:
        return jsonify(error=str(error)), 404


@app.post('/api/auth/reset-password')
def reset_password():
    body = request.get_json(silent=True) or {}
    destination = str(body.get('destination', '')).strip().lower()
    token = str(body.get('token', '')).strip()
    new_password = str(body.get('new_password', ''))
    try:
        auth.reset_password(destination, token, new_password)
        return jsonify(message='Password reset successfully. You can now log in.')
    except ValueError as error:
        return jsonify(error=str(error)), 400


@app.post('/api/chat')
def chat():
    if request.files:
        question = request.form.get('question', '').strip()
        context = request.form.get('context', '').strip()
        uploaded = request.files.get('image')
    else:
        body = request.get_json(silent=True) or {}
        question = str(body.get('question', '')).strip()
        context = str(body.get('context', '')).strip()
        uploaded = None
    if not question:
        return jsonify(error='Ask a question about a crop or plant disease.'), 400
    started = time.perf_counter()
    temporary_path = None
    try:
        if uploaded and uploaded.filename and allowed_file(uploaded.filename):
            with tempfile.NamedTemporaryFile(suffix=Path(secure_filename(uploaded.filename)).suffix, delete=False) as temporary:
                uploaded.save(temporary.name)
                temporary_path = Path(temporary.name)
            if gemini.configured:
                answer, provider_latency = gemini.answer_image(temporary_path, question, context)
                chat_metrics.record('gemini_vision_chat', provider_latency, True)
                return jsonify(answer=answer, provider='gemini_vision')
            image_guess = offline_image_guess(temporary_path, uploaded.filename)
            context = f'{context} Offline image screening: crop={image_guess["crop"]}, disease={image_guess["disease"]}.'
        if gemini.configured:
            answer, provider_latency = gemini.answer(question, context)
            chat_metrics.record('gemini', provider_latency, True)
            return jsonify(answer=answer, provider='gemini')
        answer = gemini.local_answer(question, context)
        latency = round(time.perf_counter() - started, 3)
        chat_metrics.record('fallback', latency, True)
        return jsonify(answer=answer, provider='offline')
    except RuntimeError as error:
        latency = round(time.perf_counter() - started, 3)
        chat_metrics.record('error', latency, False)
        return jsonify(error=str(error)), 503
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


@app.post('/api/analyze')
def analyze():
    uploaded = request.files.get('image')
    if uploaded is None or not uploaded.filename:
        return jsonify(error='Please upload a leaf image.'), 400
    if not allowed_file(uploaded.filename):
        return jsonify(error='Only JPG and PNG images are supported.'), 400
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(secure_filename(uploaded.filename)).suffix, delete=False) as temporary:
            uploaded.save(temporary.name)
            try:
                prediction = model.predict(Path(temporary.name))
                prediction['provider'] = 'local_model'
            except ModelNotReadyError:
                if gemini.configured:
                    prediction, provider_latency = gemini.analyze_image(Path(temporary.name))
                    chat_metrics.record('gemini_vision', provider_latency, True)
                    prediction['provider'] = 'gemini_vision'
                    prediction['note'] = 'Image diagnosis provided by Gemini Vision. Confirm uncertain cases with an agricultural expert.'
                else:
                    prediction = offline_image_guess(Path(temporary.name), uploaded.filename)
                    chat_metrics.record('offline_image_heuristic', 0, True)
    except ModelNotReadyError as error:
        return jsonify(error=str(error), note='Run train.py with a labeled dataset or configure GEMINI_API_KEY for image analysis.'), 503
    except RuntimeError as error:
        return jsonify(error=str(error)), 503
    except ValueError as error:
        return jsonify(error=str(error)), 422
    finally:
        if 'temporary' in locals() and os.path.exists(temporary.name):
            os.unlink(temporary.name)

    disease_key = prediction['disease'].lower()
    if not prediction.get('recommendations'):
        prediction['recommendations'] = CURES['healthy'] if prediction['healthy'] else CURES.get(disease_key, CURES['default'])
    prediction.setdefault('note', 'This is a model prediction. Confirm uncertain cases with an agricultural expert before treatment.')
    return jsonify(prediction)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')), debug=True)
