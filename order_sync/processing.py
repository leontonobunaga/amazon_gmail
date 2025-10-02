from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List

from dateutil import parser as date_parser

from .models import Order, OrderRecord

DATE_FORMAT = "%Y-%m-%d"
LOCKER_TEMPLATE = """お世話になっております。
お待たせしており申し訳ございません。

弊店ではAmazonFBA（フルフィルメント by Amazon）を利用しており、配送はAmazon指定の業者によって行われております。
お調べしましたところ、
ご注文商品はお住まいの建物内の宅配ボックスに配達となっておりました。

ボックス番号
{box}

暗証番号
{pin}

こちらお試し頂けますでしょうか。
どうぞよろしくお願いいたします。"""

ARRIVAL_KEYWORDS = (
    ("お届け済み", "到着済"),
    ("配達済み", "到着済"),
    ("お届け予定", "到着予定"),
    ("配達予定", "到着予定"),
)


class OrderProcessor:
    def __init__(self, detector, gmail_client):
        self.detector = detector
        self.gmail_client = gmail_client

    def _format_arrival(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "不明"

        normalized = text.replace("までにお届け", "にお届け")
        for keyword, replacement in ARRIVAL_KEYWORDS:
            if keyword in normalized:
                normalized = normalized.replace("にお届け済み", "到着済")
                normalized = normalized.replace(keyword, replacement)
                break

        explicit_date = self._extract_explicit_date(normalized)
        if explicit_date:
            suffix = "到着済" if "到着済" in normalized else "到着予定"
            return f"{explicit_date.month}月{explicit_date.day}日{suffix}"

        relative = self._resolve_relative_date(normalized)
        if relative:
            return relative

        if "到着" in normalized:
            return normalized
        return "不明"

    def _format_date(self, date: datetime) -> str:
        return date.strftime(DATE_FORMAT)

    def _build_template(self, box: str | None, pin: str | None) -> str | None:
        if not box and not pin:
            return None
        return LOCKER_TEMPLATE.format(box=box or "不明", pin=pin or "不明")

    def process_orders(self, orders: Iterable[Order]) -> List[OrderRecord]:
        records: List[OrderRecord] = []
        for order in orders:
            arrival = self._format_arrival(order.arrival_raw)
            status = ""
            box = None
            pin = None
            if order.order_number:
                status, box, pin = self.gmail_client.find_status(order.order_number, self.detector)
            if arrival != "不明" and "到着済" in arrival:
                status = "到着済"
            for item in order.items or [None]:
                title = item.title if item else ""
                quantity = item.quantity if item else "1"
                locker_message = ""
                template = None
                if status == "宅配ボックス":
                    locker_parts: list[str] = []
                    if box:
                        locker_parts.append(f"ボックス番号: {box}")
                    if pin:
                        locker_parts.append(f"暗証番号: {pin}")
                    locker_message = "、".join(locker_parts) if locker_parts else "情報なし"
                    template = self._build_template(box, pin)
                elif box or pin:
                    locker_parts = []
                    if box:
                        locker_parts.append(f"ボックス番号: {box}")
                    if pin:
                        locker_parts.append(f"暗証番号: {pin}")
                    locker_message = "、".join(locker_parts)
                    template = self._build_template(box, pin)

                records.append(
                    OrderRecord(
                        order_date=self._format_date(order.order_date),
                        price=order.price,
                        delivery_name=order.delivery_name,
                        delivery_address=order.delivery_address,
                        title=title,
                        quantity=quantity,
                        order_number=order.order_number,
                        arrival=arrival,
                        status=status or "不明",
                        locker_message=locker_message,
                        template_message=template,
                    )
                )
        return records

    def _extract_explicit_date(self, text: str) -> datetime | None:
        try:
            parsed = date_parser.parse(text, fuzzy=True)
            return parsed
        except (ValueError, OverflowError):
            return None

    def _resolve_relative_date(self, text: str) -> str | None:
        base = datetime.today()
        if "明日" in text:
            target = base + timedelta(days=1)
            return f"{target.month}月{target.day}日到着予定"
        if "今日" in text:
            return f"{base.month}月{base.day}日到着予定"

        weekday_map = {
            "月曜日": 0,
            "月曜": 0,
            "火曜日": 1,
            "火曜": 1,
            "水曜日": 2,
            "水曜": 2,
            "木曜日": 3,
            "木曜": 3,
            "金曜日": 4,
            "金曜": 4,
            "土曜日": 5,
            "土曜": 5,
            "日曜日": 6,
            "日曜": 6,
        }
        for label, weekday in weekday_map.items():
            if label in text:
                target = self._next_weekday(base, weekday)
                return f"{target.month}月{target.day}日到着予定"
        return None

    @staticmethod
    def _next_weekday(base: datetime, weekday: int) -> datetime:
        days_ahead = (weekday - base.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return base + timedelta(days=days_ahead)
