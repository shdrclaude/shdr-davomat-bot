"""Ro'yxatdan o'tish (4 qadam)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Employee
from database.queries import (
    create_employee,
    get_branch,
    list_branches,
    log_action,
)
from handlers.states import Reg
from keyboards import admin_kb, user_kb
from services.notifier import notify_branch_admins
from utils import templates
from utils.validators import validate_full_name

router = Router(name="registration")


@router.callback_query(F.data == "reg_start")
async def reg_start(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Reg.phone)
    await call.message.answer(templates.REG_PHONE, reply_markup=user_kb.contact_kb())
    await call.answer()


@router.callback_query(F.data == "reg_restart")
async def reg_restart(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Reg.phone)
    await call.message.answer(templates.REG_PHONE, reply_markup=user_kb.contact_kb())
    await call.answer("Qaytadan boshlaymiz")


@router.message(Reg.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext):
    # request_contact — foydalanuvchi o'z raqamini yuborishi shart
    if message.contact.user_id != message.from_user.id:
        await message.answer("❌ Iltimos, o'z raqamingizni yuboring (tugma orqali).")
        return
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(Reg.name)
    await message.answer(templates.REG_NAME, reply_markup=ReplyKeyboardRemove())


@router.message(Reg.phone)
async def reg_phone_invalid(message: Message):
    await message.answer(
        "❌ Raqamni qo'lda yozib bo'lmaydi. Pastdagi \"📞 Raqamni yuborish\" tugmasini bosing.",
        reply_markup=user_kb.contact_kb(),
    )


@router.message(Reg.name, F.text)
async def reg_name(message: Message, state: FSMContext, session: AsyncSession):
    ok, err = validate_full_name(message.text)
    if not ok:
        await message.answer(err)
        return
    full_name = " ".join(message.text.split())
    await state.update_data(full_name=full_name)
    branches = await list_branches(session)
    if not branches:
        await message.answer(
            "⚠️ Hozircha filiallar sozlanmagan. Iltimos, administrator bilan bog'laning."
        )
        return
    await state.set_state(Reg.branch)
    await message.answer(templates.REG_BRANCH, reply_markup=user_kb.branches_kb(branches))


@router.callback_query(Reg.branch, F.data.startswith("reg_branch:"))
async def reg_branch(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    branch_id = int(call.data.split(":")[1])
    branch = await get_branch(session, branch_id)
    if not branch:
        await call.answer("Filial topilmadi", show_alert=True)
        return
    await state.update_data(branch_id=branch_id, branch_name=branch.name)
    await state.set_state(Reg.position)
    await call.message.edit_text(templates.REG_POSITION, reply_markup=user_kb.positions_kb())
    await call.answer()


@router.callback_query(Reg.position, F.data.startswith("reg_pos:"))
async def reg_position(call: CallbackQuery, state: FSMContext):
    position = call.data.split(":", 1)[1]
    await state.update_data(position=position)
    data = await state.get_data()
    preview = templates.reg_preview(
        data["full_name"], data["phone"], data["branch_name"], position
    )
    await state.set_state(Reg.confirm)
    await call.message.edit_text(preview, reply_markup=user_kb.reg_confirm_kb())
    await call.answer()


@router.callback_query(Reg.confirm, F.data == "reg_confirm")
async def reg_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    emp: Employee = await create_employee(
        session,
        telegram_id=call.from_user.id,
        full_name=data["full_name"],
        username=call.from_user.username,
        phone=data["phone"],
        branch_id=data["branch_id"],
        position=data["position"],
    )
    await log_action(session, emp.id, "register", {"branch_id": data["branch_id"]})
    await state.clear()
    await call.message.edit_text(templates.WAITING_APPROVAL)
    await call.answer()

    # Adminlarga xabar
    text = templates.admin_new_employee(
        data["full_name"], data["phone"], data["branch_name"], data["position"],
        call.from_user.username,
    )
    await notify_branch_admins(
        call.bot, session, data["branch_id"], text,
        reply_markup=admin_kb.approve_employee_kb(emp.id),
    )
