from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .amazon import AmazonConfig, AmazonOrderFetcher
from .csv_writer import CsvWriter
from .gmail_client import GmailClient, GmailConfig, StatusDetector
from .processing import OrderProcessor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amazon注文とGmail通知をCSVにエクスポートします。",
        epilog="開始日と終了日を指定しなかった場合は、実行時に入力を求めます。",
    )
    parser.add_argument(
        "--start-date",
        dest="start_date",
        help="取得開始日 (YYYY-MM-DD)。指定しない場合は起動後に入力できます。",
    )
    parser.add_argument(
        "--end-date",
        dest="end_date",
        help="取得終了日 (YYYY-MM-DD)。指定しない場合は起動後に入力できます。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("orders.csv"),
        help="書き出し先CSVファイル (デフォルト: orders.csv)",
    )
    parser.add_argument(
        "--cookies",
        type=Path,
        default=Path("cookies.json"),
        help="Amazonセッション情報を保存するファイル",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("credentials.json"),
        help="Gmail APIのクライアントシークレットファイル",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=Path("token.json"),
        help="Gmail APIのアクセストークン保存ファイル",
    )
    return parser.parse_args()


def _resolve_date(initial: str | None, label: str) -> datetime:
    value = initial
    while True:
        if not value:
            value = input(f"{label} (YYYY-MM-DD) を入力してください: ").strip()
        if not value:
            print("値が入力されませんでした。もう一度入力してください。")
            value = None
            continue
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            print("日付の形式が正しくありません。例: 2023-09-01")
            value = None


def main() -> None:
    args = parse_args()
    start = _resolve_date(args.start_date, "開始日")
    end = _resolve_date(args.end_date, "終了日")

    while end < start:
        print("終了日は開始日以降の日付を入力してください。再入力します。")
        start = _resolve_date(None, "開始日")
        end = _resolve_date(None, "終了日")

    amazon_config = AmazonConfig(cookie_file=args.cookies)
    gmail_config = GmailConfig(credentials_file=args.credentials, token_file=args.token)

    amazon_fetcher = AmazonOrderFetcher(config=amazon_config)
    gmail_client = GmailClient(config=gmail_config)
    detector = StatusDetector()
    processor = OrderProcessor(detector=detector, gmail_client=gmail_client)
    writer = CsvWriter(output_file=args.output)

    orders = amazon_fetcher.fetch_orders(start, end)
    records = processor.process_orders(orders)
    writer.write(records)
    print(f"{args.output} に {len(records)} 件のレコードを書き出しました。")


if __name__ == "__main__":
    main()
