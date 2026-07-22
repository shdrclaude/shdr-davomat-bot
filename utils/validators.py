"""Kiritilgan matnlarni tekshirish (soxta/tushunarsiz matnlarga qarshi)."""
from __future__ import annotations

import re


def validate_reason(text: str) -> tuple[bool, str]:
    """Erkin matnli sababni tekshiradi. Bittasi ham o'tmasa — rad etiladi."""
    t = text.strip()

    # 1. Uzunlik
    if len(t) < 15:
        return False, "❌ Sabab juda qisqa. Kamida 15 ta belgi yozing."
    if len(t) > 300:
        return False, "❌ Sabab juda uzun. 300 belgidan oshmasin."

    # 2. Kamida 3 ta so'z (bir harfli so'zlar hisobga olinmaydi)
    words = [w for w in t.split() if len(w) > 1]
    if len(words) < 3:
        return False, "❌ Iltimos, sababni to'liq jumla bilan yozing."

    # 3. Unli harflar bo'lishi shart (shunchaki klaviatura bosish emas)
    # Unlilar to'plami (lotin + kirill)
    vowel_set = set("aeiouoʻ‘'оаеиуыэяёюі")
    vowels = sum(1 for c in t.lower() if c in vowel_set)
    if vowels / max(len(t), 1) < 0.15:
        return False, "❌ Tushunarsiz matn. Sababni aniq yozing."

    # 4. Takroriy belgilar (aaa, hhh, 111)
    if re.search(r"(.)\1{2,}", t):
        return False, "❌ Tushunarsiz matn. Sababni aniq yozing."

    # 5. Klaviatura ketma-ketligi (asdf, qwerty, zxcv, 1234)
    seqs = ["qwert", "asdf", "zxcv", "yuiop", "hjkl", "1234", "12345", "йцук", "фыва"]
    low = t.lower()
    if any(s in low for s in seqs):
        return False, "❌ Tushunarsiz matn. Sababni aniq yozing."

    # 6. Umuman unli bo'lmasa
    if vowels == 0:
        return False, "❌ Tushunarsiz matn. Sababni aniq yozing."

    # 7. Bo'g'in takrori — "hdhdhd", "zvsvsvsv"
    if re.search(r"(..)\1{2,}", low):
        return False, "❌ Tushunarsiz matn. Sababni aniq yozing."

    return True, ""


NAME_RE = re.compile(r"^[A-Za-zʻ‘'`Ѐ-ӿ\s]+$")


def validate_full_name(text: str) -> tuple[bool, str]:
    """Ism-familiya: kamida 2 so'z, har biri >=3 harf, faqat harflar va apostrof."""
    t = " ".join(text.split()).strip()
    if not NAME_RE.match(t):
        return False, "❌ Ism faqat harflardan iborat bo'lsin. Qaytadan kiriting."
    words = [w for w in t.split() if w]
    if len(words) < 2:
        return False, "❌ Ism va familiyani to'liq yozing (kamida 2 so'z)."
    if any(len(w.replace("'", "").replace("ʻ", "").replace("‘", "")) < 3 for w in words):
        return False, "❌ Har bir so'z kamida 3 harfdan iborat bo'lsin."
    return True, ""
