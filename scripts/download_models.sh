#!/usr/bin/env bash
set -e

MODELS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/models"
mkdir -p "$MODELS_DIR"

YUNET_URL="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL="https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

GESTURE_URL="https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task"
MINIFASNET_URL="https://huggingface.co/garciafido/minifasnet-v2-anti-spoofing-onnx/resolve/main/minifasnet_v2.onnx"

echo "📥 Verificando y descargando modelos de IA..."

if [ ! -f "$MODELS_DIR/face_detection_yunet_2023mar.onnx" ]; then
    echo "  -> Descargando YuNet (Detección facial)..."
    curl -L --progress-bar -o "$MODELS_DIR/face_detection_yunet_2023mar.onnx" "$YUNET_URL"
else
    echo "  ✓ YuNet ya está presente."
fi

if [ ! -f "$MODELS_DIR/face_recognition_sface_2021dec.onnx" ]; then
    echo "  -> Descargando SFace (Reconocimiento e incrustación facial)..."
    curl -L --progress-bar -o "$MODELS_DIR/face_recognition_sface_2021dec.onnx" "$SFACE_URL"
else
    echo "  ✓ SFace ya está presente."
fi

if [ ! -f "$MODELS_DIR/gesture_recognizer.task" ]; then
    echo "  -> Descargando Gesture Recognizer (Detección de Pulgar Arriba)..."
    curl -L --progress-bar -o "$MODELS_DIR/gesture_recognizer.task" "$GESTURE_URL"
else
    echo "  ✓ Gesture Recognizer ya está presente."
fi

if [ ! -f "$MODELS_DIR/minifasnet_v2.onnx" ]; then
    echo "  -> Descargando MiniFASNet V2 (Red Neuronal Anti-Spoofing e IA de vida)..."
    curl -L --progress-bar -o "$MODELS_DIR/minifasnet_v2.onnx" "$MINIFASNET_URL"
else
    echo "  ✓ MiniFASNet V2 ya está presente."
fi

echo "✨ Modelos listos en $MODELS_DIR"
