# services/gemini.py — Google Gemini Vision integration
import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
import base64

import config

# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class FoodAnalysis:
    is_food: bool = False
    description: str = ""
    calories: float = 0.0
    protein: float = 0.0
    fat: float = 0.0
    carbs: float = 0.0
    raw_text: str = ""


@dataclass
class ChatResponse:
    text: str = ""
    error: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Gemini API client (async, no SDK — direct REST calls for reliability)
# ─────────────────────────────────────────────────────────────────────────────
_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_VISION_MODEL = "gemini-1.5-flash"
_CHAT_MODEL   = "gemini-1.5-flash"


async def _post_json(url: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def analyze_food_photo(
    image_bytes: bytes,
    user_lang: str = "uz",
) -> FoodAnalysis:
    """
    Send an image to Gemini Vision and parse the structured nutrition response.
    The prompt instructs Gemini to reply strictly in *user_lang*.
    """
    lang_map = {
        "uz": "O'zbek tilida",
        "ru": "на русском языке",
        "en": "in English",
    }
    reply_lang = lang_map.get(user_lang, "O'zbek tilida")

    system_prompt = (
        f"Siz professional dietolog yordamchisiz. "
        f"Ushbu rasm taomsami yoki yo'qligini aniqlang. "
        f"Agar taom bo'lsa, quyidagi formatda javob bering ({reply_lang}):\n\n"
        f"TAOM: [taom nomi]\n"
        f"KALORIYA: [son]\n"
        f"OQSIL: [son] g\n"
        f"YOG: [son] g\n"
        f"UGLEVODLAR: [son] g\n"
        f"TAVSIF: [qisqacha tavsif]\n\n"
        f"Agar rasm taom emas bo'lsa, faqat 'NOT_FOOD' deb yozing."
    )

    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": system_prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
    }

    url = f"{_BASE}/{_VISION_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    try:
        data = await _post_json(url, payload)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:
        return FoodAnalysis(is_food=False, raw_text=str(exc))

    if "NOT_FOOD" in text.upper():
        return FoodAnalysis(is_food=False, raw_text=text)

    result = FoodAnalysis(is_food=True, raw_text=text)

    # Parse structured fields
    def _extract(pattern: str, default: float = 0.0) -> float:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                pass
        return default

    def _extract_str(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else default

    result.calories    = _extract(r"KALORIYA[:\s]+([\d.,]+)")
    result.protein     = _extract(r"OQSIL[:\s]+([\d.,]+)")
    result.fat         = _extract(r"YOG[:\s]+([\d.,]+)")
    result.carbs       = _extract(r"UGLEVODLAR[:\s]+([\d.,]+)")
    result.description = _extract_str(r"TAOM[:\s]+(.+)")
    if not result.description:
        result.description = _extract_str(r"TAVSIF[:\s]+(.+)")

    return result


async def chat_with_dietitian(
    message: str,
    user_lang: str = "uz",
    history: Optional[list] = None,
) -> ChatResponse:
    """
    Send a free-text question to Gemini and get a dietitian response.
    """
    lang_map = {
        "uz": "O'zbek tilida qisqa va aniq javob bering.",
        "ru": "Ответьте кратко и точно на русском языке.",
        "en": "Reply briefly and clearly in English.",
    }
    sys_instruction = (
        "Siz professional dietolog va sog'lom turmush tarzi bo'yicha maslahatchi."
        " Faqat ovqatlanish, dietalar, kaloriya, ozish va sog'lom hayot mavzularida javob bering."
        " Boshqa mavzularda 'Bu mening ixtisosim emas' deying. "
        + lang_map.get(user_lang, lang_map["uz"])
    )

    contents = [{"role": "user", "parts": [{"text": sys_instruction}]}]
    if history:
        contents.extend(history[-10:])  # last 5 turns
    contents.append({"role": "user", "parts": [{"text": message}]})

    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
    }
    url = f"{_BASE}/{_CHAT_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    try:
        data = await _post_json(url, payload)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return ChatResponse(text=text)
    except Exception as exc:
        return ChatResponse(text=str(exc), error=True)
