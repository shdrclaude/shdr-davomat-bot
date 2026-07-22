"""Umumiy handlerlar: /start dispatch, /cancel, /help, menyu ko'rsatish."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Employee, EmployeeStatus, Role
from keyboards import admin_kb, user_kb
from utils import templates
from utils.menu import determine_menu_state

router = Router(name="common")

HELP_TEXT = (
    "ℹ️ Yordam\n\n"
    "• ✅ Keldim — ish boshlanishini video-doira bilan qayd etadi\n"
    "• 🚪 Ketdim — ish yakunini qayd etadi\n"
    "• 🚶 Chiqib ketyapman — vaqtincha chiqishni belgilaydi\n"
    "• 🕐 Kech qolaman — oldindan kechikish haqida xabar beradi\n"
    "• 🏖 Dam olish so'rash — dam olish arizasi\n"
    "• 📊 Hisobotim — oylik statistikangiz\n\n"
    "Muammo bo'lsa menejeringizga murojaat qiling."
)


async def show_menu(message: Message, session: AsyncSession, emp: Employee) -> None:
    """Xodimning holatiga mos dinamik menyuni ko'rsatadi."""
    if emp.role in (Role.admin, Role.menejer):
        await message.answer(
            "🛠 Admin rejimi. Pastdagi tugmalardan foydalaning.",
            reply_markup=admin_kb.admin_menu_reply(),
        )
        return
    state = await determine_menu_state(session, emp, emp.branch)
    await message.answer("🏠 Asosiy menyu", reply_markup=user_kb.main_menu(state))


async def refresh_menu(message: Message, session: AsyncSession, emp: Employee) -> None:
    state = await determine_menu_state(session, emp, emp.branch)
    await message.answer("👇", reply_markup=user_kb.main_menu(state))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, employee: Employee | None):
    await state.clear()
    if employee is None:
        # ro'yxatdan o'tmagan → registration router boshqaradi
        await message.answer(templates.WELCOME, reply_markup=ReplyKeyboardRemove())
        await message.answer("Boshlash uchun tugmani bosing:", reply_markup=user_kb.start_kb())
        return
    if employee.status == EmployeeStatus.kutilmoqda:
        await message.answer(templates.WAITING_APPROVAL)
        return
    if employee.status == EmployeeStatus.faolsiz:
        await message.answer(templates.REJECTED_EMP)
        return
    await show_menu(message, session, employee)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, session: AsyncSession, employee: Employee | None):
    await state.clear()
    if employee and employee.status == EmployeeStatus.faol:
        await message.answer(templates.CANCELLED)
        await show_menu(message, session, employee)
    else:
        await message.answer(templates.CANCELLED)


@router.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext, session: AsyncSession, employee: Employee | None):
    await state.clear()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.answer("Bekor qilindi")
    if employee and employee.status == EmployeeStatus.faol:
        await call.message.answer(templates.CANCELLED)
        await show_menu(call.message, session, employee)


@router.message(F.text == "ℹ️ Yordam")
async def help_btn(message: Message):
    await message.answer(HELP_TEXT)
