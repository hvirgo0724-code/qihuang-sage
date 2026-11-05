"""多模态舌象/面色识别：Pillow 质量预检 + DashScope 多模态结构化识别。"""
import base64
import json
import logging
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image, ImageStat

from app.core import llm

logger = logging.getLogger("app.image_analysis")

MAX_EDGE = 1600          # 归一化最大边长
MIN_EDGE = 120           # 最小边长
MAX_BYTES = 10 * 1024 * 1024  # 10MB

TONGUE_PROMPT = (
    "你是中医望诊助手。请识别这张舌象图片，输出严格 JSON（只输出 JSON，不要多余文字）："
    '{"tongue_color":"淡白|淡红|红|绛|紫|青紫|其他","tongue_shape":"胖大|瘦薄|齿痕|裂纹|点刺|正常|其他",'
    '"coating":"薄白|白腻|黄腻|灰黑|薄黄|少苔|无苔|剥落|其他","moisture":"润|燥|滑|正常",'
    '"sublingual":"正常|青紫怒张|其他或空","confidence":0.0~1.0,'
    '"quality_flags":["是否光线不足/过曝/模糊/非舌象内容等，无则空数组"]}'
)

FACE_PROMPT = (
    "你是中医望诊助手。请识别这张面色图片，输出严格 JSON（只输出 JSON）："
    '{"complexion":"红润|萎黄|苍白|青紫|晦暗|潮红|黧黑|正常|其他","sheen":"有华|无华|正常",'
    '"abnormal_regions":"异常部位描述或空","confidence":0.0~1.0,'
    '"quality_flags":["光线不足/过曝/模糊/非面部内容等，无则空数组"]}'
)


def _to_data_url(img: Image.Image) -> str:
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def precheck_image(data: bytes) -> Tuple[bool, str]:
    """返回 (是否通过, 提示语)。"""
    if len(data) > MAX_BYTES:
        raise ValueError("图片过大，请上传 10MB 以内的图片")
    try:
        img = Image.open(BytesIO(data))
        img.load()
    except Exception:
        return False, "无法解析图片，请上传有效的 JPG/PNG 图片"
    if img.format not in ("JPEG", "PNG", "WEBP"):
        return False, "仅支持 JPG/PNG/WEBP 格式"
    w, h = img.size
    if w < MIN_EDGE or h < MIN_EDGE:
        return False, "图片分辨率过低，请对准舌面/面部重新拍摄"
    if w > 5000 or h > 5000:
        return False, "图片尺寸过大，请压缩后上传"

    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    brightness = stat.mean[0]
    if brightness < 40:
        return False, "光线不足，请打开闪光灯、避免阴影后重拍"
    if brightness > 225:
        return False, "图片过曝，请调整光线后重拍"

    # 模糊度：拉普拉斯方差
    import numpy as np
    try:
        arr = np.asarray(gray.resize((256, 256)), dtype=np.float32)
        lap = np.abs(
            arr[:-2, :-2] - 2 * arr[1:-1, 1:-1] + arr[2:, 2:]
        ).var()
        if lap < 15:
            return False, "图片模糊，请对准部位、保持稳定后重拍"
    except Exception:  # noqa: BLE001
        pass
    return True, ""


def normalize_image(data: bytes) -> bytes:
    """尺寸归一化、去 Exif 方向、转 JPEG。"""
    img = Image.open(BytesIO(data))
    from PIL import ImageOps

    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def analyze(image_path: str, image_type: str) -> dict:
    """多模态识别，返回结构化 dict。"""
    prompt = TONGUE_PROMPT if image_type == "tongue" else FACE_PROMPT
    with open(image_path, "rb") as f:
        img = Image.open(BytesIO(f.read())).convert("RGB")
    data_url = _to_data_url(img)
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ],
    }]
    raw = llm.invoke_vision(messages, scene="inspection")
    data = _parse_json(raw)
    data["image_type"] = image_type
    data.setdefault("confidence", 0.5)
    data.setdefault("quality_flags", [])
    return data


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            try:
                return json.loads(text[s:e + 1])
            except Exception:
                pass
    return {}