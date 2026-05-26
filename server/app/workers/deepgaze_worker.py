import io

import numpy as np
import torch
from matplotlib import cm
from PIL import Image

from app.models import CtaDetection, DeepgazeWorkerOutput, FixationPoint
from app.storage import put_asset

_model = None


def _get_model():
    global _model
    if _model is None:
        from deepgaze_pytorch import DeepGazeIIE
        _model = DeepGazeIIE(pretrained=True).eval()
    return _model


async def run_deepgaze(
    screenshot_bytes: bytes,
    review_id: str,
    viewport: str = "desktop",
    ctas_layout: list[dict] | None = None,
) -> DeepgazeWorkerOutput:
    img = Image.open(io.BytesIO(screenshot_bytes)).convert("RGB")
    img_arr = np.array(img)

    saliency = _predict_saliency(img_arr)
    top_points = _extract_top_fixations(saliency, n=10)

    heatmap_png = _saliency_to_png(saliency)
    overlay_png = _overlay_heatmap(img_arr, saliency)
    heatmap_key = f"{review_id}/deepgaze_{viewport}_heatmap.png"
    overlay_key = f"{review_id}/deepgaze_{viewport}_overlay.png"
    put_asset(heatmap_key, heatmap_png, "image/png")
    put_asset(overlay_key, overlay_png, "image/png")

    ctas = _detect_ctas(ctas_layout or [], saliency, top_points)

    return DeepgazeWorkerOutput(
        saliency_heatmap=f"asset://{heatmap_key}",
        saliency_overlay=f"asset://{overlay_key}",
        top_fixation_points=[FixationPoint(**p) for p in top_points],
        ctas_detected=ctas,
    )


def _predict_saliency(img_arr: np.ndarray) -> np.ndarray:
    model = _get_model()
    h, w = img_arr.shape[:2]
    img_tensor = torch.from_numpy(img_arr).permute(2, 0, 1).unsqueeze(0).float() / 255.0

    centerbias = torch.zeros(1, h, w)

    with torch.no_grad():
        log_density = model(img_tensor, centerbias)

    saliency = torch.softmax(log_density.flatten(), dim=0).reshape(log_density.shape[-2:])
    return saliency.numpy()


def _extract_top_fixations(saliency: np.ndarray, n: int = 10) -> list[dict]:
    flat = saliency.flatten()
    top_idx = np.argpartition(flat, -n)[-n:]
    top_idx = top_idx[np.argsort(flat[top_idx])[::-1]]
    points = []
    h, w = saliency.shape
    for idx in top_idx:
        y, x = divmod(int(idx), w)
        points.append({"x": int(x), "y": int(y), "weight": float(flat[idx])})
    return points


def _saliency_to_png(saliency: np.ndarray) -> bytes:
    norm = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-9)
    img = Image.fromarray((norm * 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _overlay_heatmap(img_arr: np.ndarray, saliency: np.ndarray) -> bytes:
    h, w = img_arr.shape[:2]
    sh, sw = saliency.shape
    if sh != h or sw != w:
        saliency_resized = np.array(Image.fromarray(saliency).resize((w, h), Image.BILINEAR))
    else:
        saliency_resized = saliency

    norm = (saliency_resized - saliency_resized.min()) / (saliency_resized.max() - saliency_resized.min() + 1e-9)
    heatmap_rgba = (cm.jet(norm) * 255).astype(np.uint8)
    heatmap_rgb = heatmap_rgba[..., :3]
    overlay = (0.6 * img_arr + 0.4 * heatmap_rgb).astype(np.uint8)
    img = Image.fromarray(overlay)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _detect_ctas(
    ctas_layout: list[dict], saliency: np.ndarray, top_points: list[dict]
) -> list[CtaDetection]:
    if not ctas_layout or not top_points:
        return []

    h, w = saliency.shape
    top_3_weight = sorted(top_points, key=lambda p: p["weight"], reverse=True)[
        min(2, len(top_points) - 1)
    ]["weight"]

    results = []
    for cta in ctas_layout:
        x, y, bw, bh = cta["bbox"]
        x2, y2 = min(x + bw, w), min(y + bh, h)
        if x >= w or y >= h or x < 0 or y < 0:
            continue
        region = saliency[max(0, y):y2, max(0, x):x2]
        attention = float(region.mean()) if region.size > 0 else 0.0
        results.append({
            "selector": cta["selector"],
            "bbox": cta["bbox"],
            "attention": attention,
        })

    results.sort(key=lambda r: r["attention"], reverse=True)
    out = []
    for rank, r in enumerate(results, 1):
        out.append(
            CtaDetection(
                selector=r["selector"],
                bbox=r["bbox"],
                in_top_attention=r["attention"] >= top_3_weight,
                rank=rank,
            )
        )
    return out
