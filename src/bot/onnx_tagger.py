import os
import json
import logging
import requests
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MODEL_DIR = os.environ.get("ONNX_MODEL_DIR", os.path.join(_PROJECT_ROOT, "models"))
_MODEL_PATH = os.path.join(_MODEL_DIR, "camie-tagger-v2.onnx")
_METADATA_PATH = os.path.join(_MODEL_DIR, "camie-tagger-v2-metadata.json")

_HF_BASE = "https://huggingface.co/Camais03/camie-tagger-v2/resolve/main"
_HF_MODEL_URL = f"{_HF_BASE}/camie-tagger-v2.onnx"
_HF_METADATA_URL = f"{_HF_BASE}/camie-tagger-v2-metadata.json"

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_PAD_COLOR = (124, 116, 104)
_TARGET_SIZE = 512

_THRESHOLDS = {
    "general": 0.35,
    "default": 0.5,
}

CATEGORY_MAP = {
    "general": "一般",
    "character": "角色",
    "copyright": "版权",
    "artist": "画师",
    "meta": "元信息",
    "year": "元信息",
    "rating": "元信息",
}


def _download_file(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    logger.info("Downloading %s -> %s", url, dest)
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    if pct % 20 == 0 and downloaded % (1024 * 1024 * 20) < len(chunk):
                        logger.info("Download progress: %d%% (%d/%d MB)", pct, downloaded // 1048576, total // 1048576)
    logger.info("Downloaded %s (%d MB)", os.path.basename(dest), total // 1048576)


def _ensure_model_files() -> None:
    os.makedirs(_MODEL_DIR, exist_ok=True)
    if not os.path.exists(_MODEL_PATH):
        _download_file(_HF_MODEL_URL, _MODEL_PATH)
    if not os.path.exists(_METADATA_PATH):
        _download_file(_HF_METADATA_URL, _METADATA_PATH)


def preprocess_image_pil(pil_image: Image.Image) -> np.ndarray:
    if pil_image.mode in ("RGBA", "P"):
        pil_image = pil_image.convert("RGB")

    width, height = pil_image.size
    aspect = width / height
    if aspect > 1:
        new_w = _TARGET_SIZE
        new_h = int(_TARGET_SIZE / aspect)
    else:
        new_h = _TARGET_SIZE
        new_w = int(_TARGET_SIZE * aspect)
    pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (_TARGET_SIZE, _TARGET_SIZE), _PAD_COLOR)
    paste_x = (_TARGET_SIZE - new_w) // 2
    paste_y = (_TARGET_SIZE - new_h) // 2
    canvas.paste(pil_image, (paste_x, paste_y))

    arr = np.array(canvas, dtype=np.float32)
    arr = arr.transpose((2, 0, 1))
    arr = arr / 255.0

    arr[0] = (arr[0] - _MEAN[0]) / _STD[0]
    arr[1] = (arr[1] - _MEAN[1]) / _STD[1]
    arr[2] = (arr[2] - _MEAN[2]) / _STD[2]

    arr = np.expand_dims(arr, axis=0)
    return arr.astype(np.float32)


class ONNXTagger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
            cls._instance._session = None
            cls._instance._idx_to_tag = None
            cls._instance._tag_to_category = None
            cls._instance._input_name = None
        return cls._instance

    def _load(self):
        if self._loaded:
            return

        import onnxruntime as ort

        _ensure_model_files()

        logger.info("Loading ONNX model from %s", _MODEL_PATH)
        self._session = ort.InferenceSession(
            _MODEL_PATH,
            providers=["CPUExecutionProvider"],
        )

        with open(_METADATA_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        tm = meta["dataset_info"]["tag_mapping"]
        self._idx_to_tag = tm["idx_to_tag"]
        self._tag_to_category = tm["tag_to_category"]

        self._input_name = self._session.get_inputs()[0].name
        self._loaded = True
        logger.info("ONNX model loaded successfully")

    def tag(self, pil_image: Image.Image) -> dict:
        self._load()

        input_tensor = preprocess_image_pil(pil_image)
        outputs = self._session.run(None, {self._input_name: input_tensor})

        if len(outputs) >= 2:
            logits = outputs[1]
        else:
            logits = outputs[0]

        probs = 1.0 / (1.0 + np.exp(-logits))
        probs = probs[0]

        raw_tags = {}
        for idx in range(probs.shape[0]):
            prob = float(probs[idx])
            idx_str = str(idx)
            tag_name = self._idx_to_tag.get(idx_str, None)
            if tag_name is None:
                continue
            raw_cat = self._tag_to_category.get(tag_name, "general")
            threshold = _THRESHOLDS.get(raw_cat, _THRESHOLDS["default"])
            if prob < threshold:
                continue
            if raw_cat not in raw_tags:
                raw_tags[raw_cat] = []
            raw_tags[raw_cat].append((tag_name, prob))

        for cat in raw_tags:
            raw_tags[cat].sort(key=lambda x: x[1], reverse=True)
            raw_tags[cat] = raw_tags[cat][:30]

        display_tags = {}
        for cat_name, display_name in CATEGORY_MAP.items():
            if cat_name in raw_tags and raw_tags[cat_name]:
                if display_name not in display_tags:
                    display_tags[display_name] = []
                display_tags[display_name].extend(raw_tags[cat_name])

        for cat in display_tags:
            display_tags[cat].sort(key=lambda x: x[1], reverse=True)

        return display_tags
