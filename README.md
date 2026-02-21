# Telegram-бот "Мастер на час" (MVP)

## Функции
- `/start` + постоянная кнопка `Создать заявку`.
- FSM-анкета: имя, телефон, адрес, описание, опциональное фото, подтверждение.
- Сохранение заявки в PostgreSQL.
- Уведомление владельца (ADMIN_ID) с inline-кнопками смены статуса.
- `/admin` (только для владельца):
  - просмотр по статусам (новые / в работе / завершённые) с пагинацией по 5,
  - `/admin_last` — последние 10,
  - `/admin_get <id>` — заявка по ID.

## Структура
```text
config.py
bot.py
handlers/
  start.py
  application.py
  admin.py
keyboards/
database/
  models.py
  session.py
  crud.py
migrations/
```

## Запуск
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`, затем выполните миграции:
```bash
alembic upgrade head
```

Запуск бота:
```bash
python bot.py
```
