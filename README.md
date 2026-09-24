# Cat Screen Call 1.0

Настольное приложение Python для удалённой помощи.

## Возможности 1.0
- прямое TCP-подключение;
- одноразовый код комнаты;
- явное подтверждение владельца ПК;
- просмотр экрана;
- чат;
- без скрытого агента и автозапуска;
- проверка и скачивание обновлений через GitHub;
- проверка и скачивание праздничных Event Updates.

## GitHub Updates & Events
Источник обновлений:
`https://github.com/Cat67Lisic/Cat-Screen-Call-Updates-events`

Программа читает два файла из ветки `main`:
- `update.json` — обычные обновления;
- `events.json` — временные праздничные обновления.

Обычное обновление сравнивается с локальной версией `1.0.0`. Если версия новее, пользователь может скачать ZIP. Если указан SHA-256, файл проверяется перед использованием.

Event Update содержит `start_date` и `end_date`, поэтому программа показывает событие только в заданный период. Событийные обновления не увеличивают основную версию Cat Screen Call.

### Формат update.json
```json
{
  "version": "1.1.0",
  "download_url": "https://github.com/Cat67Lisic/Cat-Screen-Call-Updates-events/releases/download/v1.1.0/CatScreenCall-1.1.0.zip",
  "release_url": "https://github.com/Cat67Lisic/Cat-Screen-Call-Updates-events/releases/tag/v1.1.0",
  "sha256": "",
  "notes": "Изменения версии"
}
```

### Формат events.json
```json
{
  "events": [
    {
      "id": "halloween-2026",
      "title": "Halloween Event 2026",
      "description": "Праздничное оформление",
      "start_date": "2026-10-25",
      "end_date": "2026-11-02",
      "download_url": "https://github.com/Cat67Lisic/Cat-Screen-Call-Updates-events/releases/download/event-halloween-2026/Halloween-Event.zip",
      "sha256": ""
    }
  ]
}
```

Если `events.json` пустой, приложение просто сообщает, что активных событий нет.
