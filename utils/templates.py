"""Barcha foydalanuvchiga ko'rinadigan matnlar shu yerda markazlashgan.

Shablon: sarlavha → ma'lumot → harakat.
"""
from __future__ import annotations

from datetime import date, time

from utils.time_helpers import (
    fmt_date,
    fmt_date_short,
    fmt_duration,
    fmt_duration_short,
    fmt_time,
)

LINE = "━━━━━━━━━━━━━━━━━━"

# ==================== RO'YXATDAN O'TISH ====================
WELCOME = (
    "👋 Assalomu alaykum!\n\n"
    "SHDR davomat tizimiga xush kelibsiz.\n"
    "Ro'yxatdan o'tish uchun 4 ta savolga javob bering."
)

REG_PHONE = "1/4 — 📞 Telefon raqamingizni yuboring.\n\nPastdagi tugmani bosing."
REG_NAME = "2/4 — 👤 Ism va familiyangizni yozing.\n\nMasalan: Sherzodbek Nurullayev"
REG_BRANCH = "3/4 — 🏢 Filialingizni tanlang:"
REG_POSITION = "4/4 — 💼 Lavozimingizni tanlang:"

WAITING_APPROVAL = "⏳ So'rovingiz rahbarga yuborildi. Tasdiqlangach xabar beramiz."
APPROVED = (
    "✅ Tabriklaymiz! Siz tizimga qo'shildingiz.\n\n"
    "Endi har kuni ishga kelganingizda \"✅ Keldim\" tugmasini bosing."
)
REJECTED_EMP = "❌ Kechirasiz, so'rovingiz rad etildi. Savollar bo'lsa menejeringizga murojaat qiling."


def reg_preview(full_name: str, phone: str, branch: str, position: str) -> str:
    return (
        "📋 Ma'lumotlaringiz:\n\n"
        f"👤 Ism: {full_name}\n"
        f"📞 Telefon: {phone}\n"
        f"🏢 Filial: {branch}\n"
        f"💼 Lavozim: {position}"
    )


def admin_new_employee(full_name: str, phone: str, branch: str, position: str, username: str | None) -> str:
    uname = f"@{username}" if username else "—"
    return (
        "🆕 Yangi xodim so'rovi\n\n"
        f"👤 {full_name}\n"
        f"📞 {phone}\n"
        f"🏢 {branch} — {position}\n"
        f"🔗 {uname}"
    )


# ==================== KELDIM ====================
CHECKIN_ASK_VIDEO = (
    "🎥 Tasdiqlash uchun video-doira (кружок) yuboring.\n\n"
    "Kamerani yuzingizga qarating, 2-5 soniya yozing."
)
CHECKIN_ALREADY = "ℹ️ Siz bugun {time} da ishni boshlagansiz."
CHECKIN_DAYOFF = "🏖 Bugun sizda dam olish kuni. Yaxshi dam oling!"
CHECKIN_NOT_VIDEO = "❌ Faqat video-doira qabul qilinadi. Mikrofon yonidagi kamera belgisini bosing."
CHECKIN_TOO_SHORT = "❌ Video juda qisqa. Kamida 2 soniya yozing."
TIMEOUT_CHECKIN = '⏱ Vaqt tugadi. Qaytadan "✅ Keldim" bosing.'


def checkin_success(name: str, tm: time, branch: str) -> str:
    return (
        "✅ Ish boshlandi\n\n"
        f"👤 {name}\n"
        f"🕐 Vaqt: {fmt_time(tm)}\n"
        f"🏢 {branch}\n\n"
        "Yaxshi ish kuni tilaymiz!"
    )


def checkin_late(name: str, tm: time, late_min: int, branch: str) -> str:
    return (
        "✅ Ish boshlandi\n\n"
        f"👤 {name}\n"
        f"🕐 Vaqt: {fmt_time(tm)}\n"
        f"⚠️ Kechikish: {late_min} daqiqa\n"
        f"🏢 {branch}\n\n"
        "Kechikish sababini tanlang:"
    )


# ==================== CHIQIB KETYAPMAN ====================
BREAK_WORK_ENDED = 'ℹ️ Ish vaqti tugadi. "🚪 Ketdim" tugmasini bosing.'
BREAK_LIMIT = "⛔ Bugungi limit tugadi (3/3). Zarur bo'lsa menejeringizga murojaat qiling."
BREAK_ASK_WHERE = "🚶 Qayerga chiqyapsiz?"
BREAK_ASK_WHEN = "⏰ Qachon qaytasiz?"


def break_preview(reason: str, minutes: int, back_time: time) -> str:
    return (
        "📋 Tekshiring:\n\n"
        f"🚶 Sabab: {reason}\n"
        f"⏰ Qaytish: {minutes} daqiqadan keyin ({fmt_time(back_time)})"
    )


def break_recorded(out_t: time, back_t: time, reason: str) -> str:
    return (
        "🚶 Chiqish qayd etildi\n\n"
        f"🕐 Chiqdi: {fmt_time(out_t)}\n"
        f"⏰ Kutilayotgan qaytish: {fmt_time(back_t)}\n"
        f"📝 Sabab: {reason}\n\n"
        'Qaytganingizda "↩️ Qaytdim" tugmasini bosing.'
    )


BREAK_REMIND_EMP = "⏰ Qaytish vaqti keldi. Qaytganingizda tugmani bosing."


def break_return(back_t: time, duration: int, expected: int, count: int) -> str:
    extra = ""
    if duration > expected:
        extra = f" (⚠️ {duration - expected} daqiqa ortiq)"
    return (
        "↩️ Qaytish qayd etildi\n\n"
        f"🕐 Qaytdi: {fmt_time(back_t)}\n"
        f"⏱ Tashqarida: {duration} daqiqa{extra}\n\n"
        f"Bugungi chiqishlar: {count}/3"
    )


def admin_break_overdue(name: str, branch: str, out_t: time, expected_t: time, reason: str) -> str:
    return (
        f"⚠️ {name} ({branch}) 30 daqiqa kechikdi. "
        f"Chiqdi: {fmt_time(out_t)}, va'da: {fmt_time(expected_t)}, sabab: {reason}"
    )


# ==================== KECH QOLAMAN / DAM OLISH ====================
LATE_ASK_DATE = "📅 Qaysi kunga?"
LATE_ASK_TIME = "⏰ Soat nechada kelasiz?"
LATE_ASK_REASON = "📝 Sababni tanlang:"


def late_already(tm: str, d: date, t: time, reason: str) -> str:
    return (
        f"ℹ️ Siz bugun soat {tm} da xabar bergansiz.\n\n"
        f"📅 Sana: {fmt_date_short(d)}\n"
        f"⏰ Vaqt: {fmt_time(t)}\n"
        f"📝 Sabab: {reason}\n"
        "📌 Holat: ⏳ Rahbar javobi kutilmoqda"
    )


def late_preview(d: date, t: time, late_txt: str, reason: str) -> str:
    return (
        "📋 So'rovingizni tekshiring:\n\n"
        f"📅 Sana: {fmt_date(d)}\n"
        f"⏰ Kelish: {fmt_time(t)} ({late_txt})\n"
        f"📝 Sabab: {reason}"
    )


REQUEST_SENT = (
    "📤 So'rov yuborildi\n\n"
    "Rahbar ko'rib chiqadi va javob beradi.\n"
    "Javob kelganda sizga xabar beramiz.\n\n"
    "📌 Holat: ⏳ Kutilmoqda"
)


def request_approved_emp(d: date, t: time | None, admin_name: str, comment: str | None) -> str:
    tline = f", {fmt_time(t)}" if t else ""
    body = (
        "✅ So'rovingiz TASDIQLANDI\n\n"
        f"📅 {fmt_date_short(d)}{tline}\n"
        f"👤 Tasdiqladi: {admin_name}"
    )
    if comment:
        body += f"\n💬 Izoh: {comment}"
    return body


def request_rejected_emp(d: date, t: time | None, admin_name: str, comment: str | None) -> str:
    tline = f", {fmt_time(t)}" if t else ""
    body = (
        "❌ So'rovingiz RAD ETILDI\n\n"
        f"📅 {fmt_date_short(d)}{tline}\n"
        f"👤 Rad etdi: {admin_name}"
    )
    if comment:
        body += f"\n💬 Sabab: {comment}"
    body += "\n\nIltimos, vaqtida keling."
    return body


VACATION_ASK_TYPE = "🏖 Qanday dam olish?"


# ==================== KETDIM ====================
def checkout_summary(name: str, tm: time, worked: int, breaks_count: int, break_min: int) -> str:
    return (
        "🚪 Ish yakunlandi\n\n"
        f"👤 {name}\n"
        f"🕐 Ketdi: {fmt_time(tm)}\n"
        f"⏱ Ish vaqti: {fmt_duration(worked)}\n"
        f"🚶 Chiqishlar: {breaks_count} marta ({fmt_duration(break_min)})\n\n"
        "Yaxshi dam oling! 👋"
    )


CHECKOUT_ASK_VIDEO = "🎥 Ketishni tasdiqlash uchun video-doira yuboring."
CHECKOUT_NO_CHECKIN = "ℹ️ Siz bugun ishni boshlamagansiz."


# ==================== HISOBOT ====================
def my_report(name: str, month: str, stats: dict) -> str:
    return (
        f"📊 {name} — {month}\n\n"
        f"{LINE}\n"
        f"✅ Ishlagan kun:      {stats['worked_days']}\n"
        f"❌ Kelmagan:           {stats['absent_days']}\n"
        f"🏖 Dam olgan:          {stats['dayoff_days']}\n"
        f"{LINE}\n"
        f"⏱ Jami ish vaqti:  {stats['total_hours']} soat\n"
        f"📈 O'rtacha kun:    {fmt_duration(stats['avg_minutes'])}\n"
        f"{LINE}\n"
        f"⚠️ Kech qolgan:      {stats['late_count']} marta\n"
        f"   Jami kechikish:   {fmt_duration(stats['late_minutes'])}\n"
        f"🚶 Chiqishlar:      {stats['break_count']} marta\n"
        f"   Jami:             {fmt_duration(stats['break_minutes'])}\n"
        f"{LINE}\n\n"
        f"🏆 Filialdagi o'rningiz: {stats['rank']}/{stats['branch_total']}"
    )


# ==================== ANTI-SPAM / XATO ====================
THROTTLE = "⏳ Biroz sekinroq. 2 soniyadan keyin qayta urinib ko'ring."
TECH_ERROR = "⚠️ Texnik nosozlik yuz berdi. Qaytadan urinib ko'ring yoki /start bosing."
FSM_TIMEOUT = "⏱ Vaqt tugadi. Menyuga qaytdingiz."
CANCELLED = "❌ Bekor qilindi. Menyuga qaytdingiz."

REASON_TOO_MANY = (
    "⚠️ Sabab qabul qilinmadi.\n\n"
    "Tayyor variantlardan birini tanlang yoki menejeringizga\n"
    "to'g'ridan-to'g'ri murojaat qiling."
)


def admin_reason_abuse(name: str) -> str:
    return f"⚠️ {name} 3 marta noto'g'ri sabab kiritdi."


def admin_break_limit_hit(name: str, branch: str) -> str:
    return f"⚠️ {name} ({branch}) chiqib ketish limitiga yetdi (3/3)."
