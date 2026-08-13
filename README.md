# Answer Controller

## Запуск

Нужны Docker и Docker Compose. Скопируйте конфигурацию, при необходимости измените пороги SLA и запустите сервис:

```bash
cp .env.example .env
docker compose up --build
```

Compose самостоятельно поднимет PostgreSQL и Redis, выполнит миграции, затем запустит API и фоновые процессы. Интерфейс будет доступен на <http://localhost:8000>, документация API — на <http://localhost:8000/docs>.

## Наполнение данными

Создать два открытых обращения:

```bash
curl -X POST http://localhost:8000/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "9e93ebc8-fd86-4cda-8d48-8067971989c9",
    "event_type": "customer_message",
    "occurred_at": "2026-08-13T10:00:00+03:00",
    "payload": {
      "message_id": "1d7fbfd7-f83c-4db0-aa5f-d38d056be435",
      "client_id": "customer-1",
      "channel": "chat",
      "direction": "sales",
      "text": "Нужна консультация по продукту"
    }
  }'

curl -X POST http://localhost:8000/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "8a36b28b-55b7-40a3-83dd-233f9e91203c",
    "event_type": "customer_message",
    "occurred_at": "2026-08-13T10:01:00+03:00",
    "payload": {
      "message_id": "cc4baf1f-3f80-4587-9ef7-a04ea84c90fb",
      "client_id": "customer-2",
      "channel": "email",
      "direction": "support",
      "text": "Не получается войти в личный кабинет"
    }
  }'
```

Чтобы закрыть первое обращение, событие ответа ссылается на `message_id` исходного сообщения клиента:

```bash
curl -X POST http://localhost:8000/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "e93df565-f97e-4691-8e8b-0c8e0d16db67",
    "event_type": "employee_response",
    "occurred_at": "2026-08-13T11:11:11+03:00",
    "payload": {
      "reply_to_message_id": "1d7fbfd7-f83c-4db0-aa5f-d38d056be435",
      "employee_id": "employee-1",
      "text": "Здравствуйте! Чем можем помочь?"
    }
  }'
```

`event_id` должен быть уникальным UUID. `message_id` идентифицирует исходное сообщение клиента, а `reply_to_message_id` связывает с ним ответ сотрудника. `occurred_at` должен содержать часовой пояс.

## Тесты

Для запуска нужен [uv](https://docs.astral.sh/uv/):

```bash
uv run pytest
```

PostgreSQL и Redis для тестов не требуются: границы репозиториев заменены in-memory реализациями. Тесты проверяют:

- конкурентную доставку 20 одинаковых событий — создаются ровно одно обращение и одно событие;
- доступность `/health` и `/api/tickets` во время искусственно замедленной отправки уведомления;
- отсутствие повторных `warning` и `overdue`, включая переход `warning → overdue`;
- откат после ошибки между сохранением события и созданием обращения, затем успешную повторную доставку;
- метрики по времени `occurred_at` из CRM, включая отвеченные просроченные обращения, медиану и пустую выборку.

Медленная интеграция не блокирует HTTP-запросы, потому что отправка выполняется отдельным Taskiq worker, а асинхронный адаптер освобождает event loop на время I/O.

## Будущие улучшения

- При росте объёма событий добавить в PostgreSQL расширение TimescaleDB: преобразовать временные данные в гипертаблицу и настроить retention/compression для метрик.
- Для внешних интеграций развить уже существующий outbox: добавить ретраи с бэкофф, лимиты попыток и метрики доставки. Таблица outbox уже обеспечивает атомарную запись намерения отправить уведомление вместе с изменением SLA.
- Добавить PostgreSQL-интеграционные тесты для ограничений, миграций и конкурентных блокировок.
- Возможно добавить ML-модель, которая будет оценивать качество ответа сотрудника и потом выдавать KPI для каждого
- Убрать докер и переехать в кубер, хотя в целом и текущая реализация легко масштабируется
- Добавить сборку метрик и логов сервиса (prometheus+loki+grafana)
- Обновить Dockerfile - сделать сборку слоями (сейчас не критично, т.к. она не занимает больше 20 секунд)

