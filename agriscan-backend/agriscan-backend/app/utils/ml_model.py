"""
Wraps whatever crop-disease model you train, so route code only ever
calls `predict(image_path)` and never touches the model directly.

--- Replace this file's internals with your real model. Example shape
    for a Keras/TensorFlow model once you have one trained:

    import tensorflow as tf
    import numpy as np
    from PIL import Image

    _model = tf.keras.models.load_model("model/crop_disease_model.h5")
    _class_names = ["Tomato_Early_Blight", "Rice_Bacterial_Blight", ...]

    def predict(image_path: str) -> dict:
        img = Image.open(image_path).convert("RGB").resize((224, 224))
        arr = np.expand_dims(np.array(img) / 255.0, axis=0)
        preds = _model.predict(arr)[0]
        idx = int(np.argmax(preds))
        label = _class_names[idx]
        crop, disease = label.split("_", 1)
        return {
            "crop_name": crop,
            "disease_name": disease.replace("_", " "),
            "is_healthy": "healthy" in label.lower(),
            "confidence": float(preds[idx]),
            "model_version": "v1",
        }
"""

import random

_MODEL_VERSION = "placeholder-v0"

_SAMPLE_RESULTS = [
    {"crop_name": "Tomato", "disease_name": "Early Blight", "is_healthy": False, "confidence": 0.91},
    {"crop_name": "Rice", "disease_name": "Bacterial Leaf Blight", "is_healthy": False, "confidence": 0.87},
    {"crop_name": "Cotton", "disease_name": "No disease detected", "is_healthy": True, "confidence": 0.95},
    {"crop_name": "Wheat", "disease_name": "Leaf Rust", "is_healthy": False, "confidence": 0.83},
]


def predict(image_path: str) -> dict:
    """
    Placeholder inference. Takes the path to a saved image and returns a
    prediction dict. Swap this out for real model inference — the return
    shape (crop_name, disease_name, is_healthy, confidence, model_version)
    is what the rest of the app expects, so keep that contract when you
    plug in the real model.
    """
    result = random.choice(_SAMPLE_RESULTS).copy()
    result["model_version"] = _MODEL_VERSION
    return result


def get_recommendations(crop_name: str, disease_name: str, db) -> list[str]:
    """Looks up recommendation text from the `diseases` reference table."""
    from app import models  # local import to avoid circular imports

    entry = (
        db.query(models.Disease)
        .filter(
            models.Disease.crop_name.ilike(crop_name),
            models.Disease.disease_name.ilike(disease_name),
        )
        .first()
    )
    if entry and entry.recommendations:
        return [line.strip() for line in entry.recommendations.split("\n") if line.strip()]

    return ["Consult a local agricultural extension officer for a confirmed diagnosis."]
