from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class OrderItem:
    title: str
    quantity: str


@dataclass
class Order:
    order_date: datetime
    order_number: str
    price: str
    arrival_raw: str
    delivery_name: str
    delivery_address: str
    items: list[OrderItem] = field(default_factory=list)


@dataclass
class OrderRecord:
    order_date: str
    price: str
    delivery_name: str
    delivery_address: str
    title: str
    quantity: str
    order_number: str
    arrival: str
    status: str
    locker_message: str
    template_message: Optional[str] = None
