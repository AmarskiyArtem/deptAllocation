Fully vibe-coded, minimally reviewed.

# DeptAllocation

[![Tests](https://github.com/AmarskiyArtem/deptAllocation/actions/workflows/tests.yml/badge.svg)](https://github.com/AmarskiyArtem/deptAllocation/actions/workflows/tests.yml)
[![Build Release](https://github.com/AmarskiyArtem/deptAllocation/actions/workflows/build-main.yml/badge.svg)](https://github.com/AmarskiyArtem/deptAllocation/actions/workflows/build-main.yml)

Desktop-приложение на `PySide6` для учета должников и кредиторов с пропорциональным распределением платежей.

## Возможности

- Ведение списка должников.
- Добавление, редактирование и удаление кредиторов с суммами требований.
- Предпросмотр распределения платежа между кредиторами.
- Применение платежа с сохранением истории.
- Удаление платежа из истории с восстановлением сумм требований.

## Требования

- Python 3.11+ (рекомендуется)
- `pip`

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Запуск

```bash
python app.py
```

## Тесты

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Сборка

### macOS

```bash
./build_mac.sh
```

Результат:

- `dist/DeptAllocation.app`
- `dist/DeptAllocation.zip` (архив для передачи пользователям macOS, создается через `ditto`)

Опционально можно подписать приложение Developer ID во время сборки:

```bash
MAC_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" ./build_mac.sh
```

Если `MAC_SIGN_IDENTITY` не задана, приложение собирается без Developer ID подписи.

### Windows

```bash
./build_windows.sh
```

Результат: `dist/DeptAllocation.exe`

## Где хранятся данные

Данные сохраняются в `debt_data.json` в системной папке приложения:

- macOS: `~/Library/Application Support/DeptAllocation/debt_data.json`
- Windows: `%APPDATA%/DeptAllocation/debt_data.json`
- Linux: `$XDG_DATA_HOME/dept_allocation/debt_data.json` или `~/.local/share/dept_allocation/debt_data.json`
