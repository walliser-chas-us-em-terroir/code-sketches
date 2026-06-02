import base64
import io
import sys
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

print("─────────────────────────────────────────")
print("  Face Censor Pro — Serveur de détection")
print("─────────────────────────────────────────")

print("Chargement du modèle InsightFace (RetinaFace)...")
try:
    from insightface.app import FaceAnalysis
    detector = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection"],
        providers=["CPUExecutionProvider"]
    )
    detector.prepare(ctx_id=0, det_size=(1280, 1280))
    MODEL_NAME = "InsightFace — buffalo_l (RetinaFace)"
    print(f"Modèle chargé : {MODEL_NAME}")
except Exception as e:
    print(f"InsightFace non disponible ({e}), tentative MTCNN...")
    try:
        from facenet_pytorch import MTCNN
        mtcnn = MTCNN(keep_all=True, thresholds=[0.5, 0.6, 0.6])
        detector = None
        MODEL_NAME = "MTCNN (facenet-pytorch)"
        print(f"Modèle chargé : {MODEL_NAME}")
    except Exception as e2:
        print(f"Aucun modèle disponible : {e2}")
        print("Lancez : pip3 install insightface flask flask-cors onnxruntime")
        sys.exit(1)

print(f"\nServeur prêt sur http://localhost:8765")
print("─────────────────────────────────────────\n")


def pil_to_cv2(pil_img):
    return np.array(pil_img.convert("RGB"))[:, :, ::-1].copy()


@app.route("/status")
def status():
    return jsonify({"ok": True, "model": MODEL_NAME})


@app.route("/detect", methods=["POST"])
def detect():
    try:
        data       = request.get_json()
        b64        = data["image"].split(",")[1]
        confidence = float(data.get("confidence", 0.3))
        img_bytes  = base64.b64decode(b64)
        pil        = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        faces_out = []

        if "buffalo_l" in MODEL_NAME or "RetinaFace" in MODEL_NAME:
            from insightface.app import FaceAnalysis
            det_threshold = max(0.05, min(0.95, 1.0 - confidence))
            detector.det_thresh = det_threshold
            cv2_img = pil_to_cv2(pil)
            results = detector.get(cv2_img)
            for face in results:
                x1, y1, x2, y2 = face.bbox.tolist()
                faces_out.append({
                    "x": x1, "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                })
        else:
            boxes, probs = mtcnn.detect(pil)
            if boxes is not None:
                for box, prob in zip(boxes, probs):
                    if prob is not None and prob >= confidence:
                        x1, y1, x2, y2 = box.tolist()
                        faces_out.append({
                            "x": x1, "y": y1,
                            "width": x2 - x1,
                            "height": y2 - y1
                        })

        print(f"  {len(faces_out)} visage(s) détecté(s) (seuil={confidence:.2f})")
        return jsonify({"faces": faces_out, "count": len(faces_out), "model": MODEL_NAME})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False, use_reloader=False)
