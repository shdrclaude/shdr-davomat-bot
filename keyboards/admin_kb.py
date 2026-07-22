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
    b.row(KeyboardButton(text="🏢 Filiallar"), KeyboardButton(text="📊 Hisobotim"))
    b.row(KeyboardButton(text="ℹ️ Yordam"))
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


def employees_list_kb(employees, show_branch: bool = False) -> InlineKeyboardMarkup:
    """Xodimlar ro'yxati — har biri tahrirlash uchun tugma."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for e in employees:
        icon = {"admin": "👑", "menejer": "🧑‍💼", "xodim": "👷"}.get(e.role.value, "·")
        st = {"faol": "", "kutilmoqda": " ⏳", "faolsiz": " 🚫"}.get(e.status.value, "")
        label = f"{icon} {e.full_name}{st}"
        if show_branch and getattr(e, "branch", None):
            label = f"{icon} {e.full_name} · {e.branch.name}{st}"
        b.button(text=label, callback_data=f"empmng:{e.id}")
    b.adjust(1)
    return b.as_markup()


def employee_card_kb(emp) -> InlineKeyboardMarkup:
    """Bitta xodim kartasi — rol va holat tugmalari."""
    rows: list[list[InlineKeyboardButton]] = []
    role_row: list[InlineKeyboardButton] = []
    if emp.role.value != "admin":
        role_row.append(InlineKeyboardButton(text="👑 Admin", callback_data=f"emprole:{emp.id}:admin"))
    if emp.role.value != "menejer":
        role_row.append(InlineKeyboardButton(text="🧑‍💼 Menejer", callback_data=f"emprole:{emp.id}:menejer"))
    if emp.role.value != "xodim":
        role_row.append(InlineKeyboardButton(text="👷 Xodim", callback_data=f"emprole:{emp.id}:xodim"))
    for i in range(0, len(role_row), 2):
        rows.append(role_row[i:i + 2])
    if emp.status.value == "faol":
        rows.append([InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"empstat:{emp.id}:faolsiz")])
    else:
        rows.append([InlineKeyboardButton(text="✅ Faollashtirish", callback_data=f"empstat:{emp.id}:faol")])
    rows.append([InlineKeyboardButton(text="🕐 Ish vaqtini belgilash", callback_data=f"empwt:{emp.id}")])
    rows.append([InlineKeyboardButton(text="◀️ Ro'yxatga qaytish", callback_data="empmng_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def branches_kb_manage(branches) -> InlineKeyboardMarkup:
    """Filiallar ro'yxati — tahrirlash uchun."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for br in branches:
        b.button(text=f"🏢 {br.name}", callback_data=f"brmng:{br.id}")
    b.adjust(1)
    return b.as_markup()


def branch_card_kb(branch) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"brname:{branch.id}")],
            [InlineKeyboardButton(text="🗑 Filialni o'chirish", callback_data=f"brdel:{branch.id}")],
            [InlineKeyboardButton(text="◀️ Ro'yxatga qaytish", callback_data="brmng_list")],
        ]
    )


def branch_delete_confirm_kb(branch_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"brdelyes:{branch_id}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"brmng:{branch_id}"),
            ]
        ]
    )
