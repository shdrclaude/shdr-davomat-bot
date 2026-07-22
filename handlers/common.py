"""Umumiy handlerlar: /start dispatch, /cancel, /help, menyu, nazoratchi."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Employee, EmployeeStatus, Role
from database.queries import list_branches, upsert_supervisor
from keyboards import admin_kb, user_kb
from services import excel_export
from services.report_builder import today_branch_report
from utils import templates
from utils.menu import determine_menu_state
from utils.time_helpers import today_local

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


def _is_supervisor(message: Message) -> bool:
    uname = (message.from_user.username or "").lower()
    return uname in settings.supervisor_username_set


async def show_menu(message: Message, session: AsyncSession, emp: Employee) -> None:
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

    # Nazoratchi (supervisor) — username orqali
    if _is_supervisor(message):
        await upsert_supervisor(session, message.from_user.id, message.from_user.username)
        await message.answer(
            "👁 Siz nazoratchisiz.\n\n"
            "Barcha filiallardan keladigan hisobot va bildirishnomalarni avtomatik olasiz.\n"
            "Pastdagi tugmalar orqali istalgan payt barcha filiallar hisobotini ko'ring.",
            reply_markup=user_kb.supervisor_menu(),
        )
        return

    if employee is None:
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
    await message.answer(templates.CANCELLED)
    if employee and employee.status == EmployeeStatus.faol:
        await show_menu(message, session, employee)


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


# ==================== NAZORATCHI TUGMALARI ====================
@router.message(F.text == "📊 Barcha filiallar — bugun")
async def sup_all_today(message: Message, session: AsyncSession):
    if not _is_supervisor(message):
        return
    branches = await list_branches(session)
    if not branches:
        await message.answer("ℹ️ Hozircha filiallar yo'q.")
        return
    for br in branches:
        text = await today_branch_report(session, br, today_local())
        await message.answer(text)


@router.message(F.text == "📥 Barcha filiallar — Excel")
async def sup_all_excel(message: Message, session: AsyncSession):
    if not _is_supervisor(message):
        return
    branches = await list_branches(session)
    if not branches:
        await message.answer("ℹ️ Hozircha filiallar yo'q.")
        return
    await message.answer("⏳ Excel tayyorlanmoqda...")
    day = today_local()
    for br in branches:
        data = await excel_export.build_month_excel(session, br.id, day.year, day.month)
        safe_name = br.name.replace(" ", "_").replace("/", "-")
        fname = f"{safe_name}_{day.year}_{day.month:02d}.xlsx"
        await message.answer_document(BufferedInputFile(data, filename=fname))
