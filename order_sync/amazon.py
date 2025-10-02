from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from .models import Order, OrderItem


@dataclass
class AmazonConfig:
    cookie_file: Path = Path("cookies.json")
    login_url: str = "https://www.amazon.co.jp/ap/signin"
    base_url: str = "https://www.amazon.co.jp"
    orders_url: str = "https://www.amazon.co.jp/gp/your-account/order-history"
    wait_seconds: float = 3.0
    driver_path: Path | None = None


class AmazonOrderFetcher:
    """Fetch order information from Amazon order history using Selenium."""

    def __init__(self, config: AmazonConfig | None = None):
        self.config = config or AmazonConfig()

    def _create_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        driver_binary = (

            Path(self.config.driver_path)
            if self.config.driver_path is not None
            else Path(ChromeDriverManager().install())
        )
        if not driver_binary.exists():
            raise RuntimeError(
                "指定された ChromeDriver が見つかりませんでした。"
                f"パスを確認してください: {driver_binary}"
            )
        try:
            driver = webdriver.Chrome(
                service=Service(str(driver_binary)),
                options=options,
            )
        except (OSError, WebDriverException) as exc:
            if self.config.driver_path is None:
                guidance = (
                    "自動ダウンロードされたバイナリが環境に対応していない可能性があります。"
                    "ChromeDriver を手動でダウンロードし、AmazonConfig.driver_path もしくは "
                    "--chrome-driver オプションでパスを指定してください。"
                )
            else:
                guidance = (
                    "指定された ChromeDriver が実行環境や Chrome のバージョンに対応しているか確認してください。"
                )
            raise RuntimeError(
                "ChromeDriver の起動に失敗しました。\n"
                f"使用したバイナリ: {driver_binary}\n"
                f"{guidance}\n"
                f"詳細: {exc}"

            str(self.config.driver_path)
            if self.config.driver_path is not None
            else ChromeDriverManager().install()
        )
        try:
            driver = webdriver.Chrome(
                service=Service(driver_binary),
                options=options,
            )
        except OSError as exc:
            raise RuntimeError(
                "ChromeDriver の起動に失敗しました。自動ダウンロードされたバイナリが環境に対応していない可能性があります。 "
                "ChromeDriver を手動でダウンロードし、AmazonConfig.driver_path もしくは --chrome-driver オプションでパスを指定してください。"

            ) from exc
        return driver

    def _load_cookies(self, driver: webdriver.Chrome) -> None:
        if self.config.cookie_file.exists():
            driver.get(self.config.base_url)
            with self.config.cookie_file.open("r", encoding="utf-8") as handle:
                cookies = json.load(handle)
            for cookie in cookies:
                cookie = {k: v for k, v in cookie.items() if k != "sameSite"}
                driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(self.config.wait_seconds)

    def _save_cookies(self, driver: webdriver.Chrome) -> None:
        cookies = driver.get_cookies()
        with self.config.cookie_file.open("w", encoding="utf-8") as handle:
            json.dump(cookies, handle, ensure_ascii=False, indent=2)

    def _ensure_logged_in(self, driver: webdriver.Chrome) -> None:
        driver.get(self.config.orders_url)
        time.sleep(self.config.wait_seconds)
        if "signin" in driver.current_url:
            print("Amazonにログインしてください。ログイン完了後にEnterキーを押してください。")
            input()
            self._save_cookies(driver)
        else:
            self._save_cookies(driver)

    def _parse_orders(self, html: str, start_date: datetime, end_date: datetime) -> Iterable[Order]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.a-box-group.a-spacing-base.order")
        for card in cards:
            order_date_element = card.select_one("span.order-date-invoice-item")
            if not order_date_element:
                continue
            order_date_text = order_date_element.get_text(strip=True)
            order_date = date_parser.parse(order_date_text.replace("注文日", "").strip())
            if not (start_date <= order_date <= end_date):
                continue

            order_number_el = card.select_one("span.value")
            order_number = order_number_el.get_text(strip=True) if order_number_el else ""

            price_el = card.select_one("span.value > span.a-color-price")
            price = price_el.get_text(strip=True) if price_el else ""

            arrival_el = card.select_one("div.a-row.a-size-base.a-color-secondary")
            arrival_raw = arrival_el.get_text(strip=True) if arrival_el else ""

            delivery_name = ""
            delivery_address = ""
            address_block = card.find("div", string=lambda text: text and "お届け先" in text)
            if address_block:
                parent = address_block.find_parent("div")
                if parent:
                    lines = parent.get_text("\n", strip=True).splitlines()
                    if len(lines) >= 2:
                        delivery_name = lines[1]
                    if len(lines) >= 3:
                        delivery_address = " ".join(lines[2:])

            items = []
            item_rows = card.select("div.a-fixed-left-grid")
            for row in item_rows:
                link = row.select_one("a.a-link-normal")
                if not link:
                    continue
                title = link.get_text(strip=True)
                qty_el = row.select_one("span.item-view-qty")
                quantity = qty_el.get_text(strip=True) if qty_el else "1"
                items.append(OrderItem(title=title, quantity=quantity))

            yield Order(
                order_date=order_date,
                order_number=order_number,
                price=price,
                arrival_raw=arrival_raw,
                delivery_name=delivery_name,
                delivery_address=delivery_address,
                items=items,
            )

    def fetch_orders(self, start_date: datetime, end_date: datetime) -> list[Order]:
        driver = self._create_driver()
        self._load_cookies(driver)
        self._ensure_logged_in(driver)

        orders: list[Order] = []
        try:
            driver.get(self.config.orders_url)
            time.sleep(self.config.wait_seconds)

            while True:
                orders.extend(self._parse_orders(driver.page_source, start_date, end_date))
                soup = BeautifulSoup(driver.page_source, "html.parser")
                next_button = soup.select_one("li.a-last a")
                if next_button:
                    href = next_button.get("href")
                    if href:
                        driver.get(f"{self.config.base_url}{href}")
                        time.sleep(self.config.wait_seconds)
                        continue
                break
        finally:
            driver.quit()
        return orders
