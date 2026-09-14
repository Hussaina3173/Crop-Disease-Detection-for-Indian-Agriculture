"""Train one crop+disease classifier from several labeled dataset roots.

Each root must contain class folders such as Tomato___Early_blight/*.jpg.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, action='append', required=True, help='Repeat for every labeled dataset root')
    parser.add_argument('--epochs', type=int, default=12)
    args = parser.parse_args()
    if args.epochs < 2:
        raise SystemExit('--epochs must be at least 2 so the trainer can warm up and fine-tune')
    missing = [str(path) for path in args.data_dir if not path.exists()]
    if missing:
        raise SystemExit('Dataset directory not found: ' + ', '.join(missing))

    import tensorflow as tf
    from tensorflow.keras import layers

    image_size = (224, 224)
    batch_size = 32
    source_datasets = []
    labels = set()
    for root in args.data_dir:
        dataset = tf.keras.utils.image_dataset_from_directory(root, validation_split=0.2, subset='both', seed=42, image_size=image_size, batch_size=batch_size)
        train_part, validation_part = dataset
        local_labels = train_part.class_names
        labels.update(local_labels)
        source_datasets.append((train_part, validation_part, local_labels))

    labels = sorted(labels)
    label_index = {label: index for index, label in enumerate(labels)}

    def remap(dataset, local_labels):
        mapping = tf.constant([label_index[label] for label in local_labels], dtype=tf.int32)
        return dataset.map(lambda images, targets: (images, tf.gather(mapping, targets)), num_parallel_calls=tf.data.AUTOTUNE)

    train = remap(source_datasets[0][0], source_datasets[0][2])
    validation = remap(source_datasets[0][1], source_datasets[0][2])
    for train_part, validation_part, local_labels in source_datasets[1:]:
        train = train.concatenate(remap(train_part, local_labels))
        validation = validation.concatenate(remap(validation_part, local_labels))
    train = train.shuffle(1024, seed=42).prefetch(tf.data.AUTOTUNE)
    validation = validation.prefetch(tf.data.AUTOTUNE)

    augmentation = tf.keras.Sequential([layers.RandomFlip('horizontal'), layers.RandomRotation(0.08), layers.RandomZoom(0.1)])
    base = tf.keras.applications.MobileNetV2(input_shape=(*image_size, 3), include_top=False, weights='imagenet')
    base.trainable = False
    inputs = tf.keras.Input(shape=(*image_size, 3))
    x = augmentation(inputs)
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x * 255.0)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(len(labels), activation='softmax')(x)
    classifier = tf.keras.Model(inputs, outputs)
    classifier.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    warmup_epochs = max(1, min(5, args.epochs // 3, args.epochs - 1))
    classifier.fit(train, validation_data=validation, epochs=warmup_epochs)
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    classifier.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5), loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    history = classifier.fit(train, validation_data=validation, initial_epoch=warmup_epochs, epochs=args.epochs)

    model_dir = Path('models')
    model_dir.mkdir(exist_ok=True)
    classifier.save(model_dir / 'crop_disease.keras')
    (model_dir / 'labels.json').write_text(json.dumps(labels, indent=2), encoding='utf-8')
    metrics = {
        'train_accuracy': float(history.history['accuracy'][-1]),
        'validation_accuracy': float(history.history['val_accuracy'][-1]),
        'epochs': args.epochs,
        'classes': len(labels),
        'datasets': [str(path) for path in args.data_dir],
    }
    (model_dir / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
