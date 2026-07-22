"""FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class Reg(StatesGroup):
    phone = State()
    name = State()
    branch = State()
    position = State()
    confirm = State()


class CheckIn(StatesGroup):
    video = State()
    late_reason = State()      # kechikish sababi tugmasi
    late_reason_text = State()  # "Boshqa" — erkin matn


class CheckOut(StatesGroup):
    video = State()
    early_reason = State()
    early_reason_text = State()


class BreakOut(StatesGroup):
    reason = State()
    reason_text = State()
    duration = State()
    confirm = State()


class LateRequest(StatesGroup):
    date = State()
    calendar = State()
    time = State()
    time_custom = State()
    reason = State()
    reason_text = State()
    confirm = State()


class Vacation(StatesGroup):
    vtype = State()
    date = State()
    calendar = State()
    end_calendar = State()
    reason = State()
    reason_text = State()
    confirm = State()


class AdminReview(StatesGroup):
    comment = State()


class BranchEdit(StatesGroup):
    name = State()


class EmpWork(StatesGroup):
    times = State()
