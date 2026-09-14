import json
from pathlib import Path


class ModelNotReadyError(RuntimeError):
    pass


class DiseaseModel:
    def __init__(self, model_dir):
        self.model_dir = Path(model_dir)
        self._model = None
        self._labels = None
        self._metrics = None

    def _load(self):
        model_path = self.model_dir / 'crop_disease.keras'
        labels_path = self.model_dir / 'labels.json'
        metrics_path = self.model_dir / 'metrics.json'
        if not model_path.exists() or not labels_path.exists():
            raise ModelNotReadyError('No trained model is installed. Add a labeled dataset and run: python train.py --data-dir data/plantvillage')
        if self._model is None:
            try:
                import tensorflow as tf
            except ImportError as error:
                raise ModelNotReadyError('TensorFlow is not installed. Install requirements.txt before analyzing images.') from error
            self._model = tf.keras.models.load_model(model_path)
            self._labels = json.loads(labels_path.read_text(encoding='utf-8'))
            self._metrics = json.loads(metrics_path.read_text(encoding='utf-8')) if metrics_path.exists() else {}

    def status(self):
        try:
            self._load()
            return {'ready': True, 'classes': len(self._labels), 'metrics': self._metrics}
        except ModelNotReadyError as error:
            return {'ready': False, 'error': str(error)}

    def predict(self, image_path):
        self._load()
        import tensorflow as tf
        image = tf.keras.utils.load_img(image_path, target_size=(224, 224))
        tensor = tf.keras.utils.img_to_array(image) / 255.0
        probabilities = self._model.predict(tensor[None, ...], verbose=0)[0]
        index = int(probabilities.argmax())
        label = self._labels[index]
        parts = label.split('___', 1)
        crop = parts[0].replace('_', ' ').strip()
        disease = parts[1].replace('_', ' ').strip() if len(parts) == 2 else label.replace('_', ' ')
        healthy = disease.lower() in {'healthy', 'healthy leaf'}
        return {'crop': crop, 'disease': 'No disease detected' if healthy else disease, 'healthy': healthy, 'confidence': float(probabilities[index])}


def offline_image_guess(image_path, original_name=''):
    """Return a visibly useful, low-confidence fallback when no ML provider is installed."""
    try:
        from PIL import Image, ImageStat
        image = Image.open(image_path).convert('RGB').resize((96, 96))
        pixels = list(image.getdata())
    except Exception as error:
        raise ValueError('The uploaded file is not a readable image.') from error

    green_pixels = sum(1 for red, green, blue in pixels if green > red * 1.05 and green > blue * 1.05)
    red_pixels = sum(1 for red, green, blue in pixels if red > green * 1.35 and red > blue * 1.35 and red > 100)
    dark_pixels = sum(1 for red, green, blue in pixels if red + green + blue < 120)
    variation = sum(ImageStat.Stat(image).stddev) / 3
    green_ratio = green_pixels / len(pixels)
    filename = original_name.lower()
    crop = next((name for name in ('tomato', 'rice', 'wheat', 'cotton', 'potato', 'maize', 'corn', 'grape', 'apple') if name in filename), '')
    # Colour alone cannot distinguish tomato, pepper, cotton, or many other crops.
    # Only use an explicit crop name in the filename; trained/Gemini models own visual identification.
    crop = crop.title() if crop else 'Unknown crop'
    dark_ratio = dark_pixels / len(pixels)

    if green_ratio < 0.18:
        disease = 'Unclear plant image'
        recommendations = ['Capture one leaf in daylight against a plain background', 'Avoid diagnosing from this image alone', 'Ask an agricultural expert to inspect the plant']
    elif dark_ratio > 0.22 and variation > 45:
        disease = 'Possible chewing insect damage'
        recommendations = ['Inspect both sides of leaves for insects or eggs', 'Remove heavily damaged leaves and control weeds', 'Use only a crop-approved treatment after local pest confirmation']
    else:
        disease = 'Possible leaf stress or disease'
        recommendations = ['Check for spots, powder, curling, insects, and wilt', 'Water at the soil and improve airflow around the plant', 'Capture a closer image and confirm with local agricultural guidance']
    return {'crop': crop, 'disease': disease, 'healthy': False, 'uncertain': True, 'confidence': 0.2 if crop == 'Unknown crop' else 0.35, 'recommendations': recommendations, 'provider': 'offline_image_heuristic', 'note': 'No visual crop model is installed. Crop is only inferred from an explicit filename hint; configure Gemini Vision or train the local model for reliable crop and disease identification.'}
