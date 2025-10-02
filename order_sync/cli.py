from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .amazon import AmazonConfig, AmazonOrderFetcher
from .csv_writer import CsvWriter
from .gmail_client import GmailClient, GmailConfig, StatusDetector
from .processing import OrderProcessor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Amazon注文とGmail通知をCSVにエクスポートします。")
    parser.add_argument("start_date", help="取得開始日 (YYYY-MM-DD)")
    parser.add_argument("end_date", help="取得終了日 (YYYY-MM-DD)")
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


def main() -> None:
    args = parse_args()
    start = datetime.strptime(args.start_date, "%Y-%m-%d")
    end = datetime.strptime(args.end_date, "%Y-%m-%d")

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
