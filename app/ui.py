from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .constants import EXACT_PERCENT_Q, MONEY_Q
from .store import DebtStore
from .utils import format_datetime_ru, money_to_str, now_iso, percent_of, to_decimal


def money_to_ui_str(value: Any) -> str:
    return money_to_str(value).replace(".", ",")


def percent_to_ui_str(value: Decimal, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


class MainWindow(QMainWindow):
    def __init__(self, store: DebtStore) -> None:
        super().__init__()
        self.store = store
        self.selected_debtor_id: str | None = None
        self.debtor_ids: list[str] = []

        self.setWindowTitle("Распределение долгов")
        self.resize(1200, 760)
        self._build_ui()
        self.refresh_debtors()

        if self.store.load_error:
            QMessageBox.warning(self, "Ошибка загрузки", self.store.load_error)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        left_layout.addWidget(QLabel("Должники"))
        self.debtor_list = QListWidget()
        self.debtor_list.currentRowChanged.connect(self.on_debtor_select)
        left_layout.addWidget(self.debtor_list, 1)

        self.add_debtor_btn = QPushButton("Добавить")
        self.rename_debtor_btn = QPushButton("Переименовать")
        self.delete_debtor_btn = QPushButton("Удалить")
        self.add_debtor_btn.clicked.connect(self.on_add_debtor)
        self.rename_debtor_btn.clicked.connect(self.on_rename_debtor)
        self.delete_debtor_btn.clicked.connect(self.on_delete_debtor)
        left_layout.addWidget(self.add_debtor_btn)
        left_layout.addWidget(self.rename_debtor_btn)
        left_layout.addWidget(self.delete_debtor_btn)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        header_row = QHBoxLayout()
        self.selected_debtor_label = QLabel("Выберите должника")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.selected_debtor_label.setFont(font)
        header_row.addWidget(self.selected_debtor_label)
        self.total_label = QLabel("Общий долг: 0,00")
        header_row.addWidget(self.total_label)
        header_row.addStretch()
        right_layout.addLayout(header_row)

        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setChildrenCollapsible(False)
        right_layout.addWidget(right_splitter, 1)

        creditors_box = QGroupBox("Кредиторы")
        creditors_layout = QVBoxLayout(creditors_box)
        self.creditors_table = QTableWidget(0, 3)
        self.creditors_table.setHorizontalHeaderLabels(
            ["Кредитор", "Долг", "Доля в процентах от общей суммы требований"]
        )
        self.creditors_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.creditors_table.setSelectionMode(QTableWidget.SingleSelection)
        self.creditors_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.creditors_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.creditors_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.creditors_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        creditors_layout.addWidget(self.creditors_table)

        creditor_buttons = QHBoxLayout()
        self.add_creditor_btn = QPushButton("Добавить")
        self.edit_creditor_btn = QPushButton("Изменить")
        self.delete_creditor_btn = QPushButton("Удалить")
        self.add_creditor_btn.clicked.connect(self.on_add_creditor)
        self.edit_creditor_btn.clicked.connect(self.on_edit_creditor)
        self.delete_creditor_btn.clicked.connect(self.on_delete_creditor)
        creditor_buttons.addWidget(self.add_creditor_btn)
        creditor_buttons.addWidget(self.edit_creditor_btn)
        creditor_buttons.addWidget(self.delete_creditor_btn)
        creditor_buttons.addStretch()
        creditors_layout.addLayout(creditor_buttons)
        right_splitter.addWidget(creditors_box)

        payment_box = QGroupBox("Платеж")
        payment_layout = QVBoxLayout(payment_box)
        payment_row = QHBoxLayout()
        payment_row.addWidget(QLabel("Сумма платежа"))
        self.payment_input = QLineEdit("0,00")
        self.payment_input.setMaximumWidth(160)
        payment_row.addWidget(self.payment_input)
        self.preview_btn = QPushButton("Предпросмотр")
        self.apply_btn = QPushButton("Применить платеж")
        self.preview_btn.clicked.connect(self.on_preview_payment)
        self.apply_btn.clicked.connect(self.on_apply_payment)
        payment_row.addWidget(self.preview_btn)
        payment_row.addWidget(self.apply_btn)
        payment_row.addStretch()
        payment_layout.addLayout(payment_row)

        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        payment_layout.addWidget(self.preview_label)

        self.preview_table = QTableWidget(0, 5)
        self.preview_table.setHorizontalHeaderLabels(
            [
                "Кредитор",
                "Сумма погашения (руб.)",
                "% от общей суммы требований",
                "Дата погашения",
                "Непогашенное требование",
            ]
        )
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setSelectionMode(QTableWidget.NoSelection)
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        payment_layout.addWidget(self.preview_table)
        right_splitter.addWidget(payment_box)

        history_box = QGroupBox("История платежей")
        history_layout = QVBoxLayout(history_box)
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            [
                "Кредитор",
                "Сумма погашения (руб.)",
                "% от общей суммы требований",
                "Дата погашения",
                "Непогашенное требование",
            ]
        )
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        history_layout.addWidget(self.history_table)

        history_buttons = QHBoxLayout()
        self.delete_payment_btn = QPushButton("Удалить платеж")
        self.delete_payment_btn.clicked.connect(self.on_delete_payment)
        history_buttons.addWidget(self.delete_payment_btn)
        history_buttons.addStretch()
        history_layout.addLayout(history_buttons)
        right_splitter.addWidget(history_box)

        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 4)
        right_splitter.setStretchFactor(2, 3)
        right_splitter.setSizes([260, 340, 240])

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def selected_debtor(self) -> dict[str, Any] | None:
        if not self.selected_debtor_id:
            return None
        return self.store.debtor_by_id(self.selected_debtor_id)

    def clear_tables(self) -> None:
        self.creditors_table.setRowCount(0)
        self.preview_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.preview_label.setText("")

    def refresh_debtors(self) -> None:
        self.debtor_list.blockSignals(True)
        self.debtor_list.clear()
        self.debtor_ids = []
        for debtor in sorted(self.store.debtors(), key=lambda d: d["name"].lower()):
            self.debtor_list.addItem(debtor["name"])
            self.debtor_ids.append(debtor["id"])

        if self.selected_debtor_id and self.selected_debtor_id in self.debtor_ids:
            idx = self.debtor_ids.index(self.selected_debtor_id)
            self.debtor_list.setCurrentRow(idx)
        else:
            self.selected_debtor_id = None
            self.selected_debtor_label.setText("Выберите должника")
            self.total_label.setText("Общий долг: 0,00")
            self.clear_tables()
        self.debtor_list.blockSignals(False)

        if self.selected_debtor_id:
            self.refresh_current_debtor_data()

    def refresh_current_debtor_data(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            self.clear_tables()
            return

        self.selected_debtor_label.setText(f"Должник: {debtor['name']}")
        self.total_label.setText(f"Общий долг: {money_to_ui_str(self.store.total_debt(debtor['id']))}")

        creditors = sorted(debtor["creditors"], key=lambda c: c["name"].lower())
        total_claim = sum((to_decimal(c.get("amount", 0)) for c in creditors), Decimal("0.00"))
        self.creditors_table.setRowCount(len(creditors))
        for row, creditor in enumerate(creditors):
            claim = to_decimal(creditor.get("amount", 0))
            name_item = QTableWidgetItem(creditor["name"])
            name_item.setData(Qt.UserRole, creditor["id"])
            amount_item = QTableWidgetItem(money_to_ui_str(claim))
            percentage_item = QTableWidgetItem(
                f"{percent_to_ui_str(percent_of(claim, total_claim, EXACT_PERCENT_Q), decimals=6)}%"
            )
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            percentage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.creditors_table.setItem(row, 0, name_item)
            self.creditors_table.setItem(row, 1, amount_item)
            self.creditors_table.setItem(row, 2, percentage_item)

        history = debtor.get("history", [])
        history_rows: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for event_index, event in enumerate(history):
            allocations = event.get("allocations", [])
            if not allocations:
                history_rows.append((event_index, event, {}))
                continue
            for allocation in allocations:
                history_rows.append((event_index, event, allocation))

        self.history_table.setRowCount(len(history_rows))
        for row, (event_index, event, allocation) in enumerate(history_rows):
            creditor_name = allocation.get("creditor_name", "—")
            amount_raw = allocation.get("amount", event.get("applied_payment", "0.00"))
            percentage_raw = allocation.get("percentage_of_queue")
            payment_date = allocation.get("payment_date") or event.get("timestamp", "")
            payment_date_display = format_datetime_ru(payment_date)
            remaining_raw = allocation.get("remaining_claim")

            amount_item = QTableWidgetItem(money_to_ui_str(amount_raw))
            percentage_item = QTableWidgetItem("—")
            if percentage_raw not in (None, ""):
                try:
                    percentage_item.setText(f"{percent_to_ui_str(to_decimal(percentage_raw), decimals=2)}%")
                except Exception:
                    percentage_item.setText(str(percentage_raw))

            remaining_item = QTableWidgetItem("—")
            if remaining_raw not in (None, ""):
                try:
                    remaining_item.setText(money_to_ui_str(remaining_raw))
                except Exception:
                    remaining_item.setText(str(remaining_raw))

            creditor_item = QTableWidgetItem(creditor_name)
            creditor_item.setData(Qt.UserRole, event_index)
            payment_date_item = QTableWidgetItem(payment_date_display)

            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            percentage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            remaining_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.history_table.setItem(row, 0, creditor_item)
            self.history_table.setItem(row, 1, amount_item)
            self.history_table.setItem(row, 2, percentage_item)
            self.history_table.setItem(row, 3, payment_date_item)
            self.history_table.setItem(row, 4, remaining_item)

        self.preview_table.setRowCount(0)
        self.preview_label.setText("")

    def parse_payment(self) -> Decimal | None:
        raw = self.payment_input.text().strip()
        try:
            payment = to_decimal(raw)
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Некорректная сумма платежа.")
            return None
        if payment <= 0:
            QMessageBox.critical(self, "Ошибка", "Сумма платежа должна быть больше 0.")
            return None
        return payment

    def ask_creditor_data(
        self, title: str, initial_name: str = "", initial_amount: str = "0,00"
    ) -> tuple[str, Decimal] | None:
        name, ok = QInputDialog.getText(self, title, "Название кредитора:", text=initial_name)
        if not ok:
            return None
        name = name.strip()
        if not name:
            QMessageBox.critical(self, "Ошибка", "Название кредитора не может быть пустым.")
            return None

        amount_raw, ok = QInputDialog.getText(
            self, title, "Сумма долга (например 12500,75):", text=initial_amount
        )
        if not ok:
            return None
        try:
            amount = to_decimal(amount_raw)
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Некорректная сумма.")
            return None
        if amount < 0:
            QMessageBox.critical(self, "Ошибка", "Сумма не может быть отрицательной.")
            return None
        return name, amount

    def selected_creditor_id(self) -> str | None:
        row = self.creditors_table.currentRow()
        if row < 0:
            return None
        name_item = self.creditors_table.item(row, 0)
        if not name_item:
            return None
        return name_item.data(Qt.UserRole)

    def on_debtor_select(self, row: int) -> None:
        if row < 0 or row >= len(self.debtor_ids):
            return
        self.selected_debtor_id = self.debtor_ids[row]
        self.refresh_current_debtor_data()

    def on_add_debtor(self) -> None:
        name, ok = QInputDialog.getText(self, "Новый должник", "Имя должника:")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.critical(self, "Ошибка", "Имя должника не может быть пустым.")
            return
        self.selected_debtor_id = self.store.add_debtor(name)
        self.refresh_debtors()

    def on_rename_debtor(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return
        new_name, ok = QInputDialog.getText(
            self, "Переименовать должника", "Новое имя:", text=debtor["name"]
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.critical(self, "Ошибка", "Имя не может быть пустым.")
            return
        self.store.rename_debtor(debtor["id"], new_name)
        self.refresh_debtors()

    def on_delete_debtor(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return
        answer = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить должника '{debtor['name']}' со всеми кредиторами и историей?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.store.delete_debtor(debtor["id"])
        self.selected_debtor_id = None
        self.refresh_debtors()

    def on_add_creditor(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return
        data = self.ask_creditor_data("Новый кредитор")
        if not data:
            return
        name, amount = data
        self.store.add_creditor(debtor["id"], name, amount)
        self.refresh_current_debtor_data()

    def on_edit_creditor(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return
        creditor_id = self.selected_creditor_id()
        if not creditor_id:
            QMessageBox.information(self, "Внимание", "Сначала выберите кредитора.")
            return
        creditor = next((c for c in debtor["creditors"] if c["id"] == creditor_id), None)
        if not creditor:
            return
        data = self.ask_creditor_data(
            "Изменить кредитора",
            initial_name=creditor["name"],
            initial_amount=money_to_ui_str(creditor.get("amount", 0)),
        )
        if not data:
            return
        name, amount = data
        self.store.update_creditor(debtor["id"], creditor_id, name, amount)
        self.refresh_current_debtor_data()

    def on_delete_creditor(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return
        creditor_id = self.selected_creditor_id()
        if not creditor_id:
            QMessageBox.information(self, "Внимание", "Сначала выберите кредитора.")
            return
        creditor = next((c for c in debtor["creditors"] if c["id"] == creditor_id), None)
        if not creditor:
            return
        answer = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить кредитора '{creditor['name']}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.store.delete_creditor(debtor["id"], creditor_id)
        self.refresh_current_debtor_data()

    def on_preview_payment(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return
        payment = self.parse_payment()
        if payment is None:
            return
        applied, allocations = self.store.preview_payment(debtor["id"], payment)
        total_claims = self.store.total_debt(debtor["id"])
        current_by_creditor_id = {c["id"]: to_decimal(c.get("amount", 0)) for c in debtor["creditors"]}
        payment_date = now_iso()
        payment_date_display = format_datetime_ru(payment_date)

        self.preview_table.setRowCount(len(allocations))
        for row, allocation in enumerate(allocations):
            creditor_item = QTableWidgetItem(allocation.creditor_name)
            amount_item = QTableWidgetItem(money_to_ui_str(allocation.amount))
            percentage_item = QTableWidgetItem(
                f"{percent_to_ui_str(percent_of(allocation.amount, total_claims), decimals=2)}%"
            )
            payment_date_item = QTableWidgetItem(payment_date_display)
            remaining = (
                current_by_creditor_id.get(allocation.creditor_id, Decimal("0.00")) - allocation.amount
            ).quantize(MONEY_Q)
            if remaining < 0:
                remaining = Decimal("0.00")
            remaining_item = QTableWidgetItem(money_to_ui_str(remaining))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            percentage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            remaining_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.preview_table.setItem(row, 0, creditor_item)
            self.preview_table.setItem(row, 1, amount_item)
            self.preview_table.setItem(row, 2, percentage_item)
            self.preview_table.setItem(row, 3, payment_date_item)
            self.preview_table.setItem(row, 4, remaining_item)

        self.preview_label.setText(
            f"Запрошено: {money_to_ui_str(payment)} | Будет применено: {money_to_ui_str(applied)}"
        )
        if applied <= 0:
            QMessageBox.information(self, "Информация", "Нет непогашенных долгов для распределения.")

    def on_apply_payment(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return
        payment = self.parse_payment()
        if payment is None:
            return
        applied, allocations = self.store.apply_payment(debtor["id"], payment)
        if applied <= 0:
            QMessageBox.information(self, "Информация", "Нет непогашенных долгов для списания.")
            return
        self.refresh_current_debtor_data()
        details = ", ".join(f"{a.creditor_name}: {money_to_ui_str(a.amount)}" for a in allocations)
        QMessageBox.information(
            self,
            "Платеж применен",
            f"Списано: {money_to_ui_str(applied)}\nРаспределение: {details}",
        )

    def on_delete_payment(self) -> None:
        debtor = self.selected_debtor()
        if not debtor:
            QMessageBox.information(self, "Внимание", "Сначала выберите должника.")
            return

        row = self.history_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Внимание", "Сначала выберите платеж в истории.")
            return
        row_item = self.history_table.item(row, 0)
        history_index = row_item.data(Qt.UserRole) if row_item else None
        if history_index is None:
            history_index = row

        answer = QMessageBox.question(
            self,
            "Подтверждение",
            "Удалить выбранный платеж и вернуть его суммы в долги?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            self.store.delete_payment(debtor["id"], int(history_index))
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить платеж:\n{exc}")
            return

        self.refresh_current_debtor_data()
        QMessageBox.information(self, "Готово", "Платеж удален. Суммы долга восстановлены.")
