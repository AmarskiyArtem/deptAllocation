from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)


MONEY_Q = Decimal("0.01")
PERCENT_Q = Decimal("0.01")


def to_decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def money_to_str(value: Any) -> str:
    return f"{to_decimal(value):.2f}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def percent_of(part: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal("0.00")
    return ((part * Decimal("100")) / total).quantize(PERCENT_Q, rounding=ROUND_HALF_UP)


@dataclass
class Allocation:
    creditor_id: str
    creditor_name: str
    amount: Decimal


def allocate_proportionally(creditors: list[dict[str, Any]], payment: Decimal) -> tuple[Decimal, list[Allocation]]:
    positive_creditors = [c for c in creditors if to_decimal(c.get("amount", 0)) > 0]
    if not positive_creditors:
        return Decimal("0.00"), []

    debt_cents_by_creditor: dict[str, int] = {}
    name_by_creditor: dict[str, str] = {}
    total_debt_cents = 0

    for creditor in positive_creditors:
        creditor_id = creditor["id"]
        creditor_name = creditor["name"]
        cents = int((to_decimal(creditor["amount"]) * 100).to_integral_value(rounding=ROUND_HALF_UP))
        if cents <= 0:
            continue
        debt_cents_by_creditor[creditor_id] = cents
        name_by_creditor[creditor_id] = creditor_name
        total_debt_cents += cents

    if total_debt_cents <= 0:
        return Decimal("0.00"), []

    requested_cents = int((to_decimal(payment) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    applied_cents = min(requested_cents, total_debt_cents)
    if applied_cents <= 0:
        return Decimal("0.00"), []

    bases: dict[str, int] = {}
    fractions: list[tuple[Decimal, str]] = []
    distributed = 0

    for creditor_id, debt_cents in debt_cents_by_creditor.items():
        raw = Decimal(applied_cents) * Decimal(debt_cents) / Decimal(total_debt_cents)
        base = int(raw.to_integral_value(rounding=ROUND_DOWN))
        bases[creditor_id] = base
        distributed += base
        fractions.append((raw - Decimal(base), creditor_id))

    remaining = applied_cents - distributed
    fractions.sort(key=lambda item: (-item[0], item[1]))

    idx = 0
    while remaining > 0 and idx < len(fractions):
        _, creditor_id = fractions[idx]
        if bases[creditor_id] < debt_cents_by_creditor[creditor_id]:
            bases[creditor_id] += 1
            remaining -= 1
        idx += 1
        if idx == len(fractions) and remaining > 0:
            idx = 0

    allocations = [
        Allocation(
            creditor_id=creditor_id,
            creditor_name=name_by_creditor[creditor_id],
            amount=(Decimal(cents) / Decimal("100")).quantize(MONEY_Q),
        )
        for creditor_id, cents in bases.items()
        if cents > 0
    ]
    allocations.sort(key=lambda a: a.creditor_name.lower())
    applied = (Decimal(applied_cents) / Decimal("100")).quantize(MONEY_Q)
    return applied, allocations


class DebtStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = {"version": 1, "debtors": []}
        self.load_error: str | None = self.load()

    def load(self) -> str | None:
        if not self.path.exists():
            return None
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if "debtors" not in self.data:
                self.data = {"version": 1, "debtors": []}
            return None
        except (json.JSONDecodeError, OSError):
            self.data = {"version": 1, "debtors": []}
            return f"Не удалось прочитать {self.path.name}. Будет использована пустая база."

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def debtors(self) -> list[dict[str, Any]]:
        return self.data["debtors"]

    def debtor_by_id(self, debtor_id: str) -> dict[str, Any] | None:
        for debtor in self.debtors():
            if debtor["id"] == debtor_id:
                return debtor
        return None

    def add_debtor(self, name: str) -> str:
        debtor_id = str(uuid.uuid4())
        self.debtors().append({"id": debtor_id, "name": name, "creditors": [], "history": []})
        self.save()
        return debtor_id

    def rename_debtor(self, debtor_id: str, new_name: str) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            return
        debtor["name"] = new_name
        self.save()

    def delete_debtor(self, debtor_id: str) -> None:
        self.data["debtors"] = [d for d in self.debtors() if d["id"] != debtor_id]
        self.save()

    def add_creditor(self, debtor_id: str, name: str, amount: Decimal) -> str:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        creditor_id = str(uuid.uuid4())
        debtor["creditors"].append({"id": creditor_id, "name": name, "amount": money_to_str(amount)})
        self.save()
        return creditor_id

    def update_creditor(self, debtor_id: str, creditor_id: str, name: str, amount: Decimal) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        for creditor in debtor["creditors"]:
            if creditor["id"] == creditor_id:
                creditor["name"] = name
                creditor["amount"] = money_to_str(amount)
                self.save()
                return
        raise ValueError("Creditor not found")

    def delete_creditor(self, debtor_id: str, creditor_id: str) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        debtor["creditors"] = [c for c in debtor["creditors"] if c["id"] != creditor_id]
        self.save()

    def total_debt(self, debtor_id: str) -> Decimal:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            return Decimal("0.00")
        total = Decimal("0.00")
        for creditor in debtor["creditors"]:
            total += to_decimal(creditor.get("amount", 0))
        return total.quantize(MONEY_Q)

    def preview_payment(self, debtor_id: str, payment: Decimal) -> tuple[Decimal, list[Allocation]]:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        return allocate_proportionally(debtor["creditors"], payment)

    def apply_payment(self, debtor_id: str, payment: Decimal) -> tuple[Decimal, list[Allocation]]:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")

        applied, allocations = allocate_proportionally(debtor["creditors"], payment)
        if applied <= 0:
            return Decimal("0.00"), []

        total_claims_before_payment = self.total_debt(debtor_id)
        amount_by_creditor = {a.creditor_id: a.amount for a in allocations}
        allocation_meta_by_creditor: dict[str, dict[str, str]] = {}
        for creditor in debtor["creditors"]:
            current = to_decimal(creditor["amount"])
            allocated = amount_by_creditor.get(creditor["id"], Decimal("0.00"))
            new_amount = (current - allocated).quantize(MONEY_Q)
            if new_amount < 0:
                new_amount = Decimal("0.00")
            creditor["amount"] = money_to_str(new_amount)
            if allocated > 0:
                allocation_meta_by_creditor[creditor["id"]] = {
                    "percentage_of_queue": f"{percent_of(allocated, total_claims_before_payment):.2f}",
                    "remaining_claim": money_to_str(new_amount),
                }

        payment_timestamp = now_iso()
        history_row = {
            "timestamp": payment_timestamp,
            "requested_payment": money_to_str(payment),
            "applied_payment": money_to_str(applied),
            "allocations": [
                {
                    "creditor_id": a.creditor_id,
                    "creditor_name": a.creditor_name,
                    "amount": money_to_str(a.amount),
                    "percentage_of_queue": allocation_meta_by_creditor.get(a.creditor_id, {}).get(
                        "percentage_of_queue", "0.00"
                    ),
                    "payment_date": payment_timestamp,
                    "remaining_claim": allocation_meta_by_creditor.get(a.creditor_id, {}).get(
                        "remaining_claim", "0.00"
                    ),
                }
                for a in allocations
            ],
        }
        debtor["history"].insert(0, history_row)
        self.save()
        return applied, allocations

    def delete_payment(self, debtor_id: str, history_index: int) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        history = debtor.get("history", [])
        if history_index < 0 or history_index >= len(history):
            raise ValueError("History record not found")

        event = history[history_index]
        creditors = debtor["creditors"]

        for allocation in event.get("allocations", []):
            allocated = to_decimal(allocation.get("amount", 0))
            if allocated <= 0:
                continue

            creditor_id = allocation.get("creditor_id")
            creditor_name = allocation.get("creditor_name", "Неизвестный кредитор")

            target = None
            if creditor_id:
                target = next((c for c in creditors if c["id"] == creditor_id), None)
            if target is None and creditor_name:
                target = next((c for c in creditors if c["name"] == creditor_name), None)

            if target is None:
                creditors.append(
                    {
                        "id": creditor_id or str(uuid.uuid4()),
                        "name": creditor_name,
                        "amount": money_to_str(allocated),
                    }
                )
            else:
                current = to_decimal(target.get("amount", 0))
                target["amount"] = money_to_str((current + allocated).quantize(MONEY_Q))

        del history[history_index]
        self.save()

    def export_excel(self, output_path: Path) -> None:
        wb = Workbook()
        ws_state = wb.active
        ws_state.title = "CurrentState"
        ws_state.append(["Debtor", "Creditor", "DebtAmount"])

        for debtor in self.debtors():
            if not debtor["creditors"]:
                ws_state.append([debtor["name"], "", 0.0])
                continue
            for creditor in debtor["creditors"]:
                ws_state.append(
                    [debtor["name"], creditor["name"], float(to_decimal(creditor.get("amount", "0.00")))]
                )

        ws_history = wb.create_sheet("History")
        ws_history.append(
            [
                "Debtor",
                "Creditor",
                "PaymentDate",
                "RepaymentAmount",
                "RepaymentSharePercent",
                "RemainingClaim",
                "RequestedPayment",
                "AppliedPayment",
            ]
        )
        for debtor in self.debtors():
            for event in debtor.get("history", []):
                requested = float(to_decimal(event.get("requested_payment", "0.00")))
                applied = float(to_decimal(event.get("applied_payment", "0.00")))
                allocations = event.get("allocations", [])
                if not allocations:
                    ws_history.append(
                        [
                            debtor["name"],
                            "",
                            event.get("timestamp", ""),
                            applied,
                            None,
                            None,
                            requested,
                            applied,
                        ]
                    )
                    continue

                for allocation in allocations:
                    percent_raw = allocation.get("percentage_of_queue")
                    percent_value = None
                    if percent_raw not in (None, ""):
                        try:
                            percent_value = float(to_decimal(percent_raw))
                        except Exception:
                            percent_value = None

                    remaining_raw = allocation.get("remaining_claim")
                    remaining_value = None
                    if remaining_raw not in (None, ""):
                        try:
                            remaining_value = float(to_decimal(remaining_raw))
                        except Exception:
                            remaining_value = None

                    ws_history.append(
                        [
                            debtor["name"],
                            allocation.get("creditor_name", ""),
                            allocation.get("payment_date") or event.get("timestamp", ""),
                            float(to_decimal(allocation.get("amount", "0.00"))),
                            percent_value,
                            remaining_value,
                            requested,
                            applied,
                        ]
                    )

        for ws in (ws_state, ws_history):
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

        wb.save(output_path)


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

        top_bar = QHBoxLayout()
        self.total_label = QLabel("Общий долг: 0.00")
        self.export_btn = QPushButton("Экспорт в Excel")
        self.export_btn.clicked.connect(self.on_export_excel)
        top_bar.addWidget(self.total_label)
        top_bar.addStretch()
        top_bar.addWidget(self.export_btn)
        root_layout.addLayout(top_bar)

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

        self.selected_debtor_label = QLabel("Выберите должника")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.selected_debtor_label.setFont(font)
        right_layout.addWidget(self.selected_debtor_label)

        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setChildrenCollapsible(False)
        right_layout.addWidget(right_splitter, 1)

        creditors_box = QGroupBox("Кредиторы")
        creditors_layout = QVBoxLayout(creditors_box)
        self.creditors_table = QTableWidget(0, 2)
        self.creditors_table.setHorizontalHeaderLabels(["Кредитор", "Долг"])
        self.creditors_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.creditors_table.setSelectionMode(QTableWidget.SingleSelection)
        self.creditors_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.creditors_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.creditors_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
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
        self.payment_input = QLineEdit("0.00")
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
        self.preview_table.setMinimumHeight(260)
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
            self.total_label.setText("Общий долг: 0.00")
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
        self.total_label.setText(f"Общий долг: {money_to_str(self.store.total_debt(debtor['id']))}")

        creditors = sorted(debtor["creditors"], key=lambda c: c["name"].lower())
        self.creditors_table.setRowCount(len(creditors))
        for row, creditor in enumerate(creditors):
            name_item = QTableWidgetItem(creditor["name"])
            name_item.setData(Qt.UserRole, creditor["id"])
            amount_item = QTableWidgetItem(money_to_str(creditor.get("amount", 0)))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.creditors_table.setItem(row, 0, name_item)
            self.creditors_table.setItem(row, 1, amount_item)

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
            remaining_raw = allocation.get("remaining_claim")

            amount_item = QTableWidgetItem(money_to_str(amount_raw))
            percentage_item = QTableWidgetItem("—")
            if percentage_raw not in (None, ""):
                try:
                    percentage_item.setText(f"{to_decimal(percentage_raw):.2f}%")
                except Exception:
                    percentage_item.setText(str(percentage_raw))

            remaining_item = QTableWidgetItem("—")
            if remaining_raw not in (None, ""):
                try:
                    remaining_item.setText(money_to_str(remaining_raw))
                except Exception:
                    remaining_item.setText(str(remaining_raw))

            creditor_item = QTableWidgetItem(creditor_name)
            creditor_item.setData(Qt.UserRole, event_index)
            payment_date_item = QTableWidgetItem(payment_date)

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
        self, title: str, initial_name: str = "", initial_amount: str = "0.00"
    ) -> tuple[str, Decimal] | None:
        name, ok = QInputDialog.getText(self, title, "Название кредитора:", text=initial_name)
        if not ok:
            return None
        name = name.strip()
        if not name:
            QMessageBox.critical(self, "Ошибка", "Название кредитора не может быть пустым.")
            return None

        amount_raw, ok = QInputDialog.getText(
            self, title, "Сумма долга (например 12500.75):", text=initial_amount
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
            initial_amount=money_to_str(creditor.get("amount", 0)),
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

        self.preview_table.setRowCount(len(allocations))
        for row, allocation in enumerate(allocations):
            creditor_item = QTableWidgetItem(allocation.creditor_name)
            amount_item = QTableWidgetItem(money_to_str(allocation.amount))
            percentage_item = QTableWidgetItem(f"{percent_of(allocation.amount, total_claims):.2f}%")
            payment_date_item = QTableWidgetItem(payment_date)
            remaining = (
                current_by_creditor_id.get(allocation.creditor_id, Decimal("0.00")) - allocation.amount
            ).quantize(MONEY_Q)
            if remaining < 0:
                remaining = Decimal("0.00")
            remaining_item = QTableWidgetItem(money_to_str(remaining))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            percentage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            remaining_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.preview_table.setItem(row, 0, creditor_item)
            self.preview_table.setItem(row, 1, amount_item)
            self.preview_table.setItem(row, 2, percentage_item)
            self.preview_table.setItem(row, 3, payment_date_item)
            self.preview_table.setItem(row, 4, remaining_item)

        self.preview_label.setText(
            f"Запрошено: {money_to_str(payment)} | Будет применено: {money_to_str(applied)}"
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
        details = ", ".join(f"{a.creditor_name}: {money_to_str(a.amount)}" for a in allocations)
        QMessageBox.information(
            self,
            "Платеж применен",
            f"Списано: {money_to_str(applied)}\nРаспределение: {details}",
        )

    def on_export_excel(self) -> None:
        default_name = f"debt_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт в Excel",
            default_name,
            "Excel files (*.xlsx)",
        )
        if not file_path:
            return
        try:
            self.store.export_excel(Path(file_path))
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось выгрузить Excel:\n{exc}")
            return
        QMessageBox.information(self, "Готово", f"Данные выгружены в:\n{file_path}")

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


def main() -> None:
    app = QApplication(sys.argv)
    data_path = Path(__file__).with_name("debt_data.json")
    store = DebtStore(data_path)
    window = MainWindow(store)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
