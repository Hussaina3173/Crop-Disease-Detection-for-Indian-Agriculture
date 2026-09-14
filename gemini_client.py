import json
import base64
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiClient:
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        self.model = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')

    @property
    def configured(self):
        return bool(self.api_key)

    @staticmethod
    def _provider_error(error, action):
        try:
            details = json.loads(error.read().decode('utf-8')).get('error', {}).get('message', '')
        except (OSError, ValueError):
            details = ''
        suffix = f' Provider message: {details}' if details else ''
        return RuntimeError(f'Gemini could not {action}.{suffix}')

    def answer(self, question, context=''):
        if not self.configured:
            raise RuntimeError('Gemini is not configured. Set GEMINI_API_KEY in the server environment.')
        prompt = (
            'You are an agricultural assistant for Indian farmers. Answer briefly and clearly. '
            'Explain likely plant diseases, visible signs, prevention, and safe next steps. '
            'Do not claim certainty from text alone. Recommend a local agricultural expert for severe or uncertain cases. '
            f'\nContext: {context}\nQuestion: {question}'
        )
        payload = json.dumps({'contents': [{'parts': [{'text': prompt}]}]}).encode('utf-8')
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}'
        request = Request(endpoint, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=25) as response:
                result = json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            raise self._provider_error(error, 'answer') from error
        except (URLError, TimeoutError) as error:
            raise RuntimeError('Gemini could not be reached. Check your internet connection and server configuration.') from error
        candidates = result.get('candidates', [])
        if not candidates:
            raise RuntimeError('Gemini returned no answer.')
        parts = candidates[0].get('content', {}).get('parts', [])
        answer = ' '.join(part.get('text', '') for part in parts).strip()
        if not answer:
            raise RuntimeError('Gemini returned an empty answer.')
        return answer, round(time.perf_counter() - started, 3)

    def local_answer(self, question, context=''):
        """Provide useful offline guidance when Gemini is not configured."""
        text = f'{question} {context}'.lower()
        topics = {
            'possible chewing insect damage': 'The image screening suggests possible chewing insect damage because of irregular missing areas in the leaf. Inspect both leaf surfaces for insects or eggs, remove badly damaged leaves, control weeds, and use only a crop-approved treatment after local pest confirmation. The crop cannot be identified reliably from this offline screening.',
            'possible leaf stress or disease': 'The image screening suggests possible leaf stress or disease, but it cannot identify the crop or disease reliably offline. Check for spots, powder, curling, insects, and wilt; water at the soil, improve airflow, capture a closer leaf image, and confirm with local agricultural guidance.',
            'tomato': 'For tomato leaves, check for early blight (brown target-like spots), late blight (water-soaked dark lesions), or leaf curl. Remove badly affected leaves, keep foliage dry, improve airflow, and confirm the diagnosis locally before applying an approved treatment.',
            'rice': 'For rice, bacterial leaf blight often causes water-soaked streaks that turn yellow to white. Improve drainage, avoid excess nitrogen, use resistant varieties, and consult local agriculture guidance for treatment.',
            'wheat': 'Wheat rust commonly appears as orange, brown, or yellow powdery lines. Remove volunteer plants, monitor nearby leaves, and use a locally approved fungicide or resistant variety based on expert advice.',
            'cotton': 'Inspect cotton for angular spots, boll damage, and curling leaves. Remove severely affected material, control weeds, avoid unnecessary leaf wetness, and ask an extension officer to identify the pest or disease.',
            'healthy': 'Healthy leaves are usually evenly colored and firm without expanding spots, wilt, powder, or unusual curling. Keep monitoring, water at the soil, and maintain balanced nutrition.',
            'blight': 'Blight symptoms can include expanding brown or black lesions and rapid leaf decline. Remove affected material, avoid overhead watering, improve airflow, and use only treatments approved for the crop and region.',
            'rust': 'Rust usually appears as orange, yellow, or brown powdery pustules. Remove volunteer hosts, monitor field spread, and seek local advice about resistant varieties and approved fungicides.',
            'fungus': 'For a suspected fungal disease, isolate affected plants where practical, remove badly damaged leaves, reduce leaf wetness, and get a local confirmation before using a fungicide.',
        }
        for keyword, answer in topics.items():
            if keyword in text:
                return answer
        if context:
            return f'I received the latest image context ({context}). I cannot inspect the image offline, so I cannot confirm a disease. Please use Gemini Vision or train the local model, then ask about the returned crop and disease. Meanwhile, isolate severely affected leaves, avoid overhead watering, and seek local agricultural advice.'
        return 'I can help with crop disease signs and prevention. Tell me the crop and visible symptoms, such as spots, curling, yellowing, powder, wilting, or insects. For a reliable image diagnosis, configure Gemini Vision or install a trained local model.'

    def analyze_image(self, image_path):
        if not self.configured:
            raise RuntimeError('Gemini is not configured. Set GEMINI_API_KEY in the server environment.')
        encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
        mime_type = 'image/png' if image_path.suffix.lower() == '.png' else 'image/jpeg'
        prompt = (
            'Inspect this plant leaf image for crop and disease identification. Return only valid JSON with exactly these keys: '
            'crop (string), disease (string), healthy (boolean), confidence (number from 0 to 1), '
            'recommendations (array of 3 to 5 short strings). If the image is unclear, say Unknown and use a low confidence. '
            'Do not invent certainty. Recommendations must be cautious and tell the farmer to follow local agricultural guidance.'
        )
        payload = json.dumps({'contents': [{'parts': [
            {'text': prompt},
            {'inline_data': {'mime_type': mime_type, 'data': encoded}},
        ]}], 'generationConfig': {'responseMimeType': 'application/json'}}).encode('utf-8')
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}'
        request = Request(endpoint, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=45) as response:
                result = json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            raise self._provider_error(error, 'analyze this image') from error
        except (URLError, TimeoutError) as error:
            raise RuntimeError('Gemini could not analyze this image. Check your internet connection and server configuration.') from error
        parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        text = ''.join(part.get('text', '') for part in parts).strip()
        try:
            prediction = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError('Gemini returned an invalid image diagnosis.') from error
        required = {'crop', 'disease', 'healthy', 'confidence', 'recommendations'}
        if not required.issubset(prediction):
            raise RuntimeError('Gemini returned an incomplete image diagnosis.')
        prediction['confidence'] = max(0.0, min(1.0, float(prediction['confidence'])))
        prediction['healthy'] = bool(prediction['healthy'])
        prediction['recommendations'] = [str(item) for item in prediction['recommendations']]
        return prediction, round(time.perf_counter() - started, 3)

    def answer_image(self, image_path, question, context=''):
        if not self.configured:
            raise RuntimeError('Gemini is not configured. Set GEMINI_API_KEY in the server environment.')
        encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
        mime_type = 'image/png' if image_path.suffix.lower() == '.png' else 'image/jpeg'
        prompt = (
            'You are an agricultural assistant. Inspect the attached plant image and answer the user briefly. '
            'Identify the likely crop, describe visible disease or pest symptoms, explain uncertainty, and give safe next steps. '
            'Do not claim certainty from one image and do not recommend unapproved chemical use. '
            f'\nExisting context: {context}\nUser question: {question}'
        )
        payload = json.dumps({'contents': [{'parts': [
            {'text': prompt},
            {'inline_data': {'mime_type': mime_type, 'data': encoded}},
        ]}]}).encode('utf-8')
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}'
        request = Request(endpoint, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=45) as response:
                result = json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            raise self._provider_error(error, 'inspect this image') from error
        except (URLError, TimeoutError) as error:
            raise RuntimeError('Gemini could not inspect this image. Check your internet connection and server configuration.') from error
        parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        answer = ' '.join(part.get('text', '') for part in parts).strip()
        if not answer:
            raise RuntimeError('Gemini returned no image-based answer.')
        return answer, round(time.perf_counter() - started, 3)
