"""Kod → yorliq lug'atlari (barcha tanlovlar shu yerda)."""

POSITIONS = ["Sotuvchi", "Menejer", "Omborchi", "Haydovchi", "Usta", "Boshqa"]

# Kechikish sababi (Keldim ichida)
LATE_ARRIVAL_REASONS = {
    "transport": "🚗 Transport",
    "health": "🏥 Sog'liq",
    "family": "👨‍👩‍👧 Oilaviy",
    "other": "✍️ Boshqa",
}

# Chiqib ketish sabablari
BREAK_REASONS = {
    "lunch": "🍽 Tushlik",
    "bank": "🏦 Bank / hujjat",
    "client": "🚚 Mijozga chiqish",
    "store": "📦 Ombor / do'kon",
    "doctor": "🏥 Shifokor",
    "personal": "👤 Shaxsiy ish",
    "other": "✍️ Boshqa",
}

# Chiqib ketishda qaytish vaqti variantlari (daqiqa)
BREAK_DURATIONS = {
    "15": ("15 daqiqa", 15),
    "30": ("30 daqiqa", 30),
    "60": ("1 soat", 60),
    "120": ("2 soat", 120),
}

# Kech qolish so'rovi sabablari
LATE_REQUEST_REASONS = {
    "doctor": "🏥 Shifokorga borishim kerak",
    "family": "👨‍👩‍👧 Oilaviy sabab",
    "transport": "🚗 Transport / yo'l muammosi",
    "document": "📄 Hujjat / davlat idorasi",
    "other": "✍️ Boshqa sabab",
}

# Kelish vaqti variantlari (kech qolish)
ARRIVAL_TIME_SLOTS = ["09:00", "09:30", "10:00", "10:30", "11:00", "12:00"]

# Dam olish turlari
VACATION_TYPES = {
    "one_day": "1️⃣ Bir kun",
    "multi_day": "📆 Bir necha kun",
    "half_day": "⏱ Yarim kun",
}

# Dam olish sabablari
VACATION_REASONS = {
    "family": "👨‍👩‍👧 Oilaviy sabab",
    "health": "🏥 Sog'liq",
    "personal": "👤 Shaxsiy ish",
    "travel": "✈️ Safar",
    "other": "✍️ Boshqa sabab",
}


def reason_label(mapping: dict, code: str | None, free_text: str | None = None) -> str:
    """Kod bo'yicha yorliq; 'other' bo'lsa erkin matn ko'rsatiladi."""
    if code == "other" and free_text:
        return free_text
    if code and code in mapping:
        # emoji-siz toza matn kerak bo'lsa ham to'liq yorliqni qaytaramiz
        return mapping[code]
    return free_text or "—"
