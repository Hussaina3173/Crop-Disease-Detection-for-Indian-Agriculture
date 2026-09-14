# Recommended Datasets

Download the datasets from their official pages and keep each one under `data/`. Check each dataset's license and terms before commercial use.

## 1. PlantVillage

- Source: https://github.com/spMohanty/PlantVillage-Dataset
- Best for: a large, controlled baseline with crop/disease folder labels.
- Layout: `data/plantvillage/<Crop>___<Disease>/*.jpg`

## 2. PlantDoc

- Source: https://github.com/pratikkayal/PlantDoc-Dataset
- Best for: field images with more realistic lighting and backgrounds.
- Layout: convert or place its class folders under `data/plantdoc/`.

## 3. Paddy Doctor

- Source: https://github.com/rm1009/Paddy-Doctor
- Best for: rice disease coverage relevant to Indian agriculture.
- Layout: place labeled class folders under `data/paddy/`.

The trainer accepts multiple roots. Every class folder name should use the same spelling across datasets, for example `Tomato___Early_blight` and `Rice___Bacterial_leaf_blight`. Do not mix unlabeled images into the training roots.

Example:

```powershell
python train.py --data-dir data/plantvillage --data-dir data/plantdoc --data-dir data/paddy --epochs 15
```

The result is written to `models/metrics.json`, including train and validation accuracy. Accuracy is only meaningful when the validation images are kept separate from training images and the datasets have consistent labels.
