"""Admin/menejer klaviaturalari."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_menu(pending_count: int = 0) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📊 Bugungi hisobot", callback_data="adm:today")],
        [InlineKeyboardButton(text=f"⏳ Kutilayotgan so'rovlar ({pending_count})", callback_data="adm:pending")],
        [InlineKeyboardButton(text="⚠️ Hozir tashqarida", callback_data="adm:outside")],
        [InlineKeyboardButton(text="⏰ Bugun kech qolganlar", callback_data="adm:late")],
        [InlineKeyboardButton(text="👥 Xodimlar", callback_data="adm:employees")],
        [InlineKeyboardButton(text="🎥 Bugungi videolar", callback_data="adm:videos")],
        [InlineKeyboardButton(text="🏆 Reyting", callback_data="adm:rating")],
        [InlineKeyboardButton(text="📅 Sana bo'yicha", callback_data="adm:bydate")],
        [InlineKeyboardButton(text="📥 Excel", callback_data="adm:excel")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="adm:settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_reply():
    """Admin uchun asosiy klaviatura — funksiyalar to'g'ridan-to'g'ri tugmalarda."""
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="📊 Bugungi hisobot"))
    b.row(KeyboardButton(text="⏳ Kutilayotgan so'rovlar"), KeyboardButton(text="⚠️ Hozir tashqarida"))
    b.row(KeyboardButton(text="⏰ Bugun kech qolganlar"), KeyboardButton(text="👥 Xodimlar"))
    b.row(KeyboardButton(text="🎥 Bugungi videolar"), KeyboardButton(text="📥 Excel"))
    b.row(KeyboardButton(text="📊 Hisobotim"), KeyboardButton(text="ℹ️ Yordam"))
    return b.as_markup(resize_keyboard=True)


def approve_employee_kb(emp_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"emp_ok:{emp_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"emp_no:{emp_id}"),
            ]
        ]
    )


def review_request_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"req_ok:{req_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"req_no:{req_id}"),
            ],
            [InlineKeyboardButton(text="💬 Izoh bilan javob", callback_data=f"req_cm:{req_id}")],
        ]
    )


def comment_decision_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Izoh bilan tasdiqlash", callback_data=f"reqc_ok:{req_id}"),
                InlineKeyboardButton(text="❌ Izoh bilan rad etish", callback_data=f"reqc_no:{req_id}"),
            ]
        ]
    )
