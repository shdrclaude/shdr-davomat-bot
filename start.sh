#!/usr/bin/env bash
set -e

echo "==> Migratsiyalar qo'llanmoqda..."
alembic upgrade head

echo "==> Bot ishga tushmoqda..."
exec python main.py
