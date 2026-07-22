"""Xodim (foydalanuvchi) klaviaturalari."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from locales import uz

CANCEL_BTN = InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[CANCEL_BTN]])


# ==================== RO'YXATDAN O'TISH ====================
def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="▶️ Boshlash", callback_data="reg_start")]]
    )


def contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def branches_kb(branches) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for br in branches:
        b.button(text=br.name, callback_data=f"reg_branch:{br.id}")
    b.adjust(1)
    b.row(CANCEL_BTN)
    return b.as_markup()


def positions_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for pos in uz.POSITIONS:
        b.button(text=pos, callback_data=f"reg_pos:{pos}")
    b.adjust(2)
    b.row(CANCEL_BTN)
    return b.as_markup()


def reg_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="reg_confirm"),
                InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="reg_restart"),
            ]
        ]
    )


# ==================== ASOSIY MENYU (dinamik) ====================
def main_menu(state: str) -> ReplyKeyboardMarkup:
    """state: 'not_in' | 'working' | 'outside' | 'done'."""
    b = ReplyKeyboardBuilder()
    if state == "not_in":
        b.row(KeyboardButton(text="✅ Keldim"))
        b.row(KeyboardButton(text="🕐 Kech qolaman"), KeyboardButton(text="🏖 Dam olish so'rash"))
    elif state == "working":
        b.row(KeyboardButton(text="🚪 Ketdim"))
        b.row(KeyboardButton(text="🚶 Chiqib ketyapman"))
        b.row(KeyboardButton(text="🏖 Dam olish so'rash"))
    elif state == "outside":
        b.row(KeyboardButton(text="↩️ Qaytdim"))
    elif state == "done":
        b.row(KeyboardButton(text="🕐 Ertaga kech qolaman"))
        b.row(KeyboardButton(text="🏖 Dam olish so'rash"))
    b.row(KeyboardButton(text="📊 Hisobotim"), KeyboardButton(text="ℹ️ Yordam"))
    return b.as_markup(resize_keyboard=True)


# ==================== SABAB / TANLOV KLAVIATURALARI ====================
def _mapping_kb(mapping: dict, prefix: str, per_row: int = 2) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, label in mapping.items():
        b.button(text=label, callback_data=f"{prefix}:{code}")
    b.adjust(per_row)
    b.row(CANCEL_BTN)
    return b.as_markup()


def late_arrival_reason_kb() -> InlineKeyboardMarkup:
    return _mapping_kb(uz.LATE_ARRIVAL_REASONS, "lar")


def break_reason_kb() -> InlineKeyboardMarkup:
    return _mapping_kb(uz.BREAK_REASONS, "brr")


def break_duration_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, (label, _m) in uz.BREAK_DURATIONS.items():
        b.button(text=label, callback_data=f"brd:{code}")
    b.adjust(2)
    b.row(CANCEL_BTN)
    return b.as_markup()


def late_request_reason_kb() -> InlineKeyboardMarkup:
    return _mapping_kb(uz.LATE_REQUEST_REASONS, "lrr", per_row=1)


def vacation_reason_kb() -> InlineKeyboardMarkup:
    return _mapping_kb(uz.VACATION_REASONS, "vrr", per_row=1)


def vacation_type_kb() -> InlineKeyboardMarkup:
    return _mapping_kb(uz.VACATION_TYPES, "vt", per_row=1)


def arrival_time_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for slot in uz.ARRIVAL_TIME_SLOTS:
        b.button(text=slot, callback_data=f"latt:{slot}")
    b.button(text="🕐 Boshqa vaqt", callback_data="latt:custom")
    b.adjust(3)
    b.row(CANCEL_BTN)
    return b.as_markup()


def date_choice_kb(tomorrow_lbl: str, day_after_lbl: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tomorrow_lbl, callback_data="ldate:1")],
            [InlineKeyboardButton(text=day_after_lbl, callback_data="ldate:2")],
            [InlineKeyboardButton(text="📆 Boshqa sana", callback_data="ldate:custom")],
            [CANCEL_BTN],
        ]
    )


def confirm_send_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data="send"),
                InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="edit"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
            ]
        ]
    )


def confirm_break_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="send"),
                InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="edit"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
            ]
        ]
    )


def existing_request_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="req_edit"),
                InlineKeyboardButton(text="🗑 Bekor qilish", callback_data="req_delete"),
            ]
        ]
    )


def ready_reasons_kb(mapping: dict, prefix: str) -> InlineKeyboardMarkup:
    """3 marta xato kiritilgach — tayyor variantlar."""
    return _mapping_kb(mapping, prefix, per_row=1)


def report_nav_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 O'tgan oy", callback_data="rep_prev"),
                InlineKeyboardButton(text="📆 Sana tanlash", callback_data="rep_pick"),
            ]
        ]
    )


def supervisor_menu() -> ReplyKeyboardMarkup:
    """Nazoratchi (supervisor) uchun klaviatura — barcha filiallar."""
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="📊 Barcha filiallar — bugun"))
    b.row(KeyboardButton(text="📥 Barcha filiallar — Excel"))
    b.row(KeyboardButton(text="ℹ️ Yordam"))
    return b.as_markup(resize_keyboard=True)
