from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import OrderRecord


class CsvWriter:
    def __init__(self, output_file: Path = Path("orders.csv")):
        self.output_file = output_file

    def write(self, records: Iterable[OrderRecord]) -> None:
        fieldnames = [
            "年月日",
            "金額",
            "お届け先（名前）",
            "お届け先（住所）",
            "商品名",
            "個数",
            "注文番号",
            "到着日",
            "ステータス",
            "宅配ボックス情報",
            "テンプレート文",
        ]
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with self.output_file.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "年月日": record.order_date,
                        "金額": record.price,
                        "お届け先（名前）": record.delivery_name,
                        "お届け先（住所）": record.delivery_address,
                        "商品名": record.title,
                        "個数": record.quantity,
                        "注文番号": record.order_number,
                        "到着日": record.arrival,
                        "ステータス": record.status,
                        "宅配ボックス情報": record.locker_message,
                        "テンプレート文": record.template_message or "",
                    }
                )
