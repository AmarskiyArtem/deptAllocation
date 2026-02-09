# Приложение для распределения долгов

GUI-приложение на Python (`PySide6`) для Windows и macOS, которое:
- хранит список должников;
- хранит по каждому должнику список кредиторов и суммы долга;
- распределяет платеж пропорционально текущим долгам;
- уменьшает долги после применения платежа;
- сохраняет историю платежей;
- экспортирует текущее состояние и историю в Excel.

## Требования

- Python 3.10+
- `PySide6`
- `openpyxl`

## Установка

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

Windows:

```bash
python app.py
```

macOS:

```bash
python3 app.py
```

После запуска:
1. Добавьте должника.
2. Добавьте кредиторов и суммы долга.
3. Введите сумму платежа.
4. Нажмите `Предпросмотр` или `Применить платеж`.
5. Для выгрузки используйте кнопку `Экспорт в Excel`.

## Данные

- Файл данных: `debt_data.json` (создается рядом с `app.py` автоматически).
- История хранится внутри каждого должника.

## Экспорт в Excel

Создается `.xlsx` файл с листами:
- `CurrentState` — текущее состояние долгов;
- `History` — история платежей и распределений.

## Отправка готового приложения (для людей без Python)

### macOS

1. На вашей машине выполните:
```bash
./build_portable_mac.sh
```
2. Будет создана папка:
`release/DebtAllocator-mac`
3. Заархивируйте **всю папку** `DebtAllocator-mac` и отправьте архив.
4. Получатель распаковывает архив и запускает:
`Run DebtAllocator.command` (двойной клик).

### Windows

1. На вашей машине с Windows выполните:
```bat
build_portable_windows.bat
```
2. Будет создана папка:
`release\DebtAllocator-windows`
3. Заархивируйте **всю папку** `DebtAllocator-windows` и отправьте архив.
4. Получатель распаковывает архив и запускает:
`Start DebtAllocator.bat` (двойной клик).
