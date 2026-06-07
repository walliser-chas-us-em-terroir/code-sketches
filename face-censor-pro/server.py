import base64
import io
import os
import shutil
import sys
import numpy as np
from PIL import Image, ImageOps
from flask import Flask, request, jsonify
from flask_cors import CORS


def fix_insightface_pack(name):
    """Le zip antelopev2 s'extrait dans un sous-dossier imbriqué
    (~/.insightface/models/antelopev2/antelopev2/*.onnx), ce qui fait
    échouer le chargement. On remonte les .onnx d'un niveau si besoin."""
    base = os.path.expanduser(f"~/.insightface/models/{name}")
    nested = os.path.join(base, name)
    if os.path.isdir(nested) and not any(
        f.endswith(".onnx") for f in os.listdir(base)
    ):
        for f in os.listdir(nested):
            shutil.move(os.path.join(nested, f), os.path.join(base, f))
        try:
            os.rmdir(nested)
        except OSError:
            pass

app = Flask(__name__)
CORS(app)

print("─────────────────────────────────────────")
print("  Face Censor Pro — Serveur de détection")
print("─────────────────────────────────────────")

# ── Détecteur de visages (InsightFace) ────────────────────────────────────────
# Point 3 : on tente d'abord antelopev2 (plus gros modèle, meilleur rappel),
# puis on retombe sur buffalo_l, puis sur MTCNN.
USE_INSIGHT = True
detector = None
mtcnn = None

print("Chargement du détecteur de visages...")
try:
    from insightface.app import FaceAnalysis

    def load_pack(name):
        return FaceAnalysis(
            name=name,
            allowed_modules=["detection"],
            providers=["CPUExecutionProvider"]
        )

    pack = "antelopev2"
    try:
        detector = load_pack("antelopev2")
    except Exception:
        # 1re tentative échouée : souvent le dossier imbriqué -> on corrige et on réessaie.
        fix_insightface_pack("antelopev2")
        try:
            detector = load_pack("antelopev2")
        except Exception:
            pack = "buffalo_l"
            detector = load_pack("buffalo_l")
    detector.prepare(ctx_id=0, det_size=(1280, 1280))
    MODEL_NAME = f"InsightFace — {pack} (RetinaFace)"
    print(f"  Visages : {MODEL_NAME}")
except Exception as e:
    print(f"  InsightFace non disponible ({e}), tentative MTCNN...")
    try:
        from facenet_pytorch import MTCNN
        mtcnn = MTCNN(keep_all=True, thresholds=[0.5, 0.6, 0.6])
        USE_INSIGHT = False
        MODEL_NAME = "MTCNN (facenet-pytorch)"
        print(f"  Visages : {MODEL_NAME}")
    except Exception as e2:
        print(f"  Aucun modèle de visage disponible : {e2}")
        print("  Lancez : pip3 install insightface flask flask-cors onnxruntime")
        sys.exit(1)

# ── Détecteur de têtes / silhouettes (YOLOv8-seg) ─────────────────────────────
# Points 1 + 4 : segmentation des personnes -> on découpe la silhouette de la
# tête (utile pour les têtes de dos ou totalement détournées, qu'aucun
# détecteur de VISAGE ne peut voir) et on renvoie son contour exact.
YOLO_OK = False
yolo = None
cv2 = None
try:
    import cv2 as _cv2
    from ultralytics import YOLO
    cv2 = _cv2
    yolo = YOLO("yolov8m-seg.pt")  # téléchargé une fois (~52 Mo)
    YOLO_OK = True
    print("  Têtes/silhouette : YOLOv8m-seg")
except Exception as e:
    print(f"  Segmentation des têtes indisponible ({e}) — option « têtes de dos » désactivée")

print(f"\nServeur prêt sur http://localhost:8765")
print("─────────────────────────────────────────\n")


# ── Outils ──────────────────────────────────────────────────────────────────

def pil_to_cv2(pil_img):
    """PIL RGB -> numpy BGR (format attendu par InsightFace/OpenCV)."""
    return np.array(pil_img.convert("RGB"))[:, :, ::-1].copy()


def iou(a, b):
    """Intersection-over-Union de deux boîtes [x1, y1, x2, y2, ...]."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def nms(boxes, iou_thresh=0.4):
    """Supprime les doublons issus du chevauchement des tuiles.
    Garde la boîte au meilleur score parmi chaque groupe qui se recouvre."""
    boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
    keep = []
    while boxes:
        best = boxes.pop(0)
        keep.append(best)
        boxes = [b for b in boxes if iou(best, b) < iou_thresh]
    return keep


def insight_detect(cv2_img, threshold):
    """Une passe de détection InsightFace sur une image BGR donnée."""
    detector.det_thresh = threshold
    out = []
    for face in detector.get(cv2_img):
        x1, y1, x2, y2 = face.bbox.tolist()
        out.append([x1, y1, x2, y2, float(getattr(face, "det_score", 1.0))])
    return out


def detect_faces(pil, confidence, deep):
    """Détection de visages multi-échelle.

    Passe 1 : image entière -> visages proches/grands.
    Passe 2 (deep) : tuiles 1280px qui se chevauchent, détectées à pleine
    résolution -> visages lointains/petits invisibles après redimensionnement.
    Fusion finale par NMS. Renvoie des boîtes [x1, y1, x2, y2, score].
    """
    base = pil_to_cv2(pil)
    H, W = base.shape[:2]
    threshold = max(0.05, min(0.95, 1.0 - confidence))

    boxes = insight_detect(base, threshold)

    if deep:
        tile = 1280
        overlap = 0.25
        step = int(tile * (1 - overlap))
        if max(W, H) > tile * 1.25:
            for ty in range(0, H, step):
                for tx in range(0, W, step):
                    x0, y0 = tx, ty
                    x1t, y1t = min(tx + tile, W), min(ty + tile, H)
                    if (x1t - x0) < 96 or (y1t - y0) < 96:
                        continue
                    crop = base[y0:y1t, x0:x1t]
                    for bx1, by1, bx2, by2, sc in insight_detect(crop, threshold):
                        boxes.append([bx1 + x0, by1 + y0, bx2 + x0, by2 + y0, sc])

    return nms(boxes, iou_thresh=0.4)


def detect_heads(pil, confidence, face_boxes):
    """Segmente les personnes (YOLOv8-seg) et renvoie la SILHOUETTE de chaque
    tête sous forme de polygone. Couvre les têtes de dos / détournées.

    Une tête qui recouvre fortement un visage déjà détecté est ignorée :
    le visage (ellipse précise) s'en charge déjà.
    """
    rgb = np.array(pil.convert("RGB"))
    H, W = rgb.shape[:2]
    conf = max(0.10, min(0.50, 0.50 - confidence * 0.4))

    res = yolo.predict(rgb, imgsz=1280, classes=[0], conf=conf,
                       retina_masks=True, verbose=False)[0]
    heads = []
    if res.masks is None:
        return heads

    boxes_xyxy = res.boxes.xyxy.cpu().numpy()
    for poly, (px1, py1, px2, py2) in zip(res.masks.xy, boxes_xyxy):
        pw, ph = px2 - px1, py2 - py1
        if pw <= 2 or ph <= 2:
            continue
        # La tête occupe le haut de la personne ; on coupe au niveau du cou.
        head_bottom = int(py1 + min(ph, pw * 1.3))

        mask = np.zeros((H, W), np.uint8)
        cv2.fillPoly(mask, [poly.astype(np.int32)], 255)
        mask[head_bottom:, :] = 0

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) < 80:
            continue

        hx, hy, hw, hh = cv2.boundingRect(c)
        hb = [hx, hy, hx + hw, hy + hh, 1.0]
        if any(iou(hb, fb) > 0.30 for fb in face_boxes):
            continue  # déjà couvert par un visage détecté

        eps = 0.008 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        heads.append({
            "kind": "head",
            "x": float(hx), "y": float(hy),
            "width": float(hw), "height": float(hh),
            "polygon": approx.astype(float).tolist()
        })
    return heads


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/status")
def status():
    return jsonify({"ok": True, "model": MODEL_NAME, "heads": YOLO_OK})


@app.route("/detect", methods=["POST"])
def detect():
    try:
        data = request.get_json()
        b64 = data["image"].split(",")[1]
        confidence = float(data.get("confidence", 0.3))
        deep = bool(data.get("deep", True))
        heads_on = bool(data.get("heads", False))
        img_bytes = base64.b64decode(b64)
        pil = Image.open(io.BytesIO(img_bytes))
        pil = ImageOps.exif_transpose(pil).convert("RGB")  # respecte l'orientation EXIF

        out = []
        face_boxes = []

        if USE_INSIGHT:
            face_boxes = detect_faces(pil, confidence, deep)
            for x1, y1, x2, y2, _sc in face_boxes:
                out.append({
                    "kind": "face", "polygon": None,
                    "x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1
                })
        else:
            boxes, probs = mtcnn.detect(pil)
            if boxes is not None:
                for box, prob in zip(boxes, probs):
                    if prob is not None and prob >= confidence:
                        x1, y1, x2, y2 = box.tolist()
                        face_boxes.append([x1, y1, x2, y2, float(prob)])
                        out.append({
                            "kind": "face", "polygon": None,
                            "x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1
                        })

        n_heads = 0
        if heads_on and YOLO_OK:
            heads = detect_heads(pil, confidence, face_boxes)
            n_heads = len(heads)
            out.extend(heads)

        scan = "multi-échelle" if (USE_INSIGHT and deep) else "simple"
        print(f"  {len(out)} détection(s) — {len(out) - n_heads} visage(s) + "
              f"{n_heads} tête(s) — (seuil={confidence:.2f}, scan={scan})")
        return jsonify({"faces": out, "count": len(out), "model": MODEL_NAME})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False, use_reloader=False)
