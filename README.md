# SHDR Davomat Boti

Telegram bot — xodimlarning ishga kelish-ketishini video-doira (кружок) orqali nazorat qiladi.
Bot: **SHDR keldim, ketdim** (@shdr_keldi_keti_bot)

## Imkoniyatlar

- ✅ Keldim / 🚪 Ketdim — video-doira bilan tasdiqlash, kechikishni avtomatik hisoblash
- 🚶 Chiqib ketyapman / ↩️ Qaytdim — vaqtincha chiqishlar (kuniga 3 marta limit)
- 🕐 Kech qolaman — oldindan xabar (kuniga 1 marta), kalendar + tugmalardan sana/vaqt
- 🏖 Dam olish so'rash — bir kun / bir necha kun / yarim kun (oyiga 3 ta kutilayotgan)
- 📊 Hisobotim — oylik statistika va filialdagi reyting
- 🛠 Admin panel — kunlik hisobot, so'rovlarni tasdiqlash, Excel eksport
- 🤖 Avtomatik vazifalar — eslatmalar, kunlik/haftalik/oylik hisobotlar
- 🛡 Anti-spam va soxta matnlarga qarshi validatsiya

## Texnologiyalar

Python 3.11 · aiogram 3.x (FSM) · PostgreSQL + SQLAlchemy (async) + Alembic · Redis · APScheduler
Vaqt zonasi: **Asia/Tashkent**. Til: **o'zbek (lotin)**.

## Talablar

- Docker va Docker Compose (eng oson yo'l), yoki
- Python 3.11 + PostgreSQL 14+ + Redis 6+

---

## 1. Botni yaratish (@BotFather)

1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring
2. `/newbot` → nom va username bering → **tokenni** oling
3. `/setprivacy` → botni tanlang → **Disable** (guruhda ishlashi uchun)

## 2. O'z Telegram ID'ingizni bilish

Botni ishga tushirgach unga `/id` yozing — yoki [@userinfobot](https://t.me/userinfobot) dan oling.
Bu ID `SUPER_ADMINS` ga yoziladi.

---

## 3. Lokal ishga tushirish (Docker)

```bash
cp .env.example .env
# .env ni tahrirlang: BOT_TOKEN va SUPER_ADMINS ni to'ldiring

docker compose up --build -d
docker compose logs -f bot
```

Postgres, Redis, migratsiyalar va bot avtomatik ishga tushadi.

## 4. Lokal ishga tushirish (Docker'siz)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# PostgreSQL va Redis ishlab turgan bo'lsin, .env ni sozlang
alembic upgrade head
python main.py
```

---

## 5. Bulutga joylash — Railway (tavsiya, 24/7)

1. [railway.app](https://railway.app) da GitHub bilan ro'yxatdan o'ting
2. **New Project → Deploy from GitHub repo** → shu rep'ni tanlang
3. Loyihaga **PostgreSQL** va **Redis** qo'shing: *New → Database → Add PostgreSQL*, keyin *Add Redis*
4. Bot servisining **Variables** bo'limiga o'zgaruvchilar qo'shing:
   - `BOT_TOKEN` — BotFather tokeni
   - `SUPER_ADMINS` — sizning Telegram ID'ingiz
   - `DATABASE_URL` — Postgres o'zgaruvchisidan (`${{Postgres.DATABASE_URL}}`)
   - `REDIS_URL` — Redis o'zgaruvchisidan (`${{Redis.REDIS_URL}}`)
   - `TZ_NAME` — `Asia/Tashkent`
5. Railway `Dockerfile` orqali avtomatik quradi, `start.sh` migratsiyalarni qo'llab botni ishga tushiradi.

> `DATABASE_URL` `postgresql://...` ko'rinishida bo'lsa ham bot avtomatik `asyncpg` driveriga o'giradi.

---

## 6. Birinchi sozlash (bot ishga tushgach)

1. Botga yoki **filial guruhiga** super-admin sifatida `/setup` yozing.
   Bu birinchi filialni yaratadi, o'sha chatni admin guruh qiladi va sizni admin qiladi.
2. Filial nomini o'zgartirish: `/branch_name SHDR QO'QON`
3. Ish vaqtini sozlash: `/work_time 09:00 18:00`
4. Yangi filial qo'shish (super-admin): `/newbranch SHDR TOSHKENT`

Endi xodimlar `/start` bosib ro'yxatdan o'tadi. Siz (admin) ularni tasdiqlaysiz.

## Foydali buyruqlar

| Buyruq | Kim | Vazifa |
|---|---|---|
| `/start` | hamma | Boshlash / menyu |
| `/cancel` | hamma | Joriy amalni bekor qilish |
| `/id` | hamma | Telegram ID'ni ko'rsatadi |
| `/setup` | super-admin | Boshlang'ich sozlash |
| `/newbranch NOMI` | super-admin | Yangi filial |
| `/branch_name NOMI` | admin | Filial nomini o'zgartirish |
| `/work_time 09:00 18:00` | admin | Ish vaqtini sozlash |

## Loyiha tuzilishi

```
shdr_bot/
├── main.py               # kirish nuqtasi (bot + dispatcher + scheduler)
├── config.py             # .env sozlamalari
├── database/             # modellar, so'rovlar, sessiya
├── handlers/             # registration, attendance, breaks, requests, reports, admin, setup
├── keyboards/            # user, admin, kalendar klaviaturalari
├── middlewares/          # throttling (anti-spam), auth, logging
├── services/             # scheduler, report_builder, excel_export, notifier
├── utils/                # validators, time_helpers, templates, menu
├── locales/uz.py         # sabab/lavozim yorliqlari
└── alembic/              # migratsiyalar
```

Barcha foydalanuvchiga ko'rinadigan matnlar `utils/templates.py` da markazlashgan.

## Xavfsizlik

- Token va DB parollari faqat `.env` da (kodga yozilmaydi, `.gitignore` da)
- Xodim telefon raqami faqat admin/menejerga ko'rinadi
- Barcha vaqtlar Asia/Tashkent, bazaga UTC bilan saqlanadi
