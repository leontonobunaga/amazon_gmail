from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import tomllib

from .amazon import AmazonConfig, AmazonOrderFetcher
from .csv_writer import CsvWriter
from .gmail_client import GmailClient, GmailConfig, StatusDetector
from .processing import OrderProcessor

DATE_FORMAT = "%Y-%m-%d"
DEFAULT_CONFIG_FILE = Path("config.toml")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amazon注文とGmail通知をCSVにエクスポートします。",
        epilog="開始日と終了日を指定しなかった場合は、実行時に入力を求めます。",
    )
    parser.add_argument(
        "start_date",
        nargs="?",
        help="取得開始日 (YYYY-MM-DD)。省略すると実行時に入力できます。",
    )
    parser.add_argument(
        "end_date",
        nargs="?",
        help="取得終了日 (YYYY-MM-DD)。省略すると実行時に入力できます。",
    )
    parser.add_argument(
        "--start-date",
        dest="start_date_override",
        help="取得開始日 (YYYY-MM-DD)。引数で指定しない場合は実行時に入力できます。",
    )
    parser.add_argument(
        "--end-date",
        dest="end_date_override",
        help="取得終了日 (YYYY-MM-DD)。引数で指定しない場合は実行時に入力できます。",
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
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_FILE,
        help="設定値を上書きするTOMLファイル (デフォルト: config.toml)",
    )
    parser.add_argument(
        "--chrome-driver",
        dest="chrome_driver",
        type=Path,
        default=None,
        help="既存のChromeDriverバイナリへのパス (指定すると自動ダウンロードをスキップ)",
    )
    return parser.parse_args(argv)


def _load_settings(config_file: Path) -> dict[str, Any]:
    if not config_file.exists():
        return {}
    try:
        with config_file.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:  # pragma: no cover - config errors exit early
        raise SystemExit(
            f"設定ファイルの読み込みに失敗しました ({config_file}): {exc}"
        ) from exc


def _get_path_setting(
    settings: dict[str, Any], config_file: Path, *keys: str
) -> Path | None:
    if not settings:
        return None

    node: Any = settings
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)

    if node in (None, ""):
        return None

    path = Path(str(node)).expanduser()
    if not path.is_absolute():
        path = (config_file.parent / path).expanduser()
    return path


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
            return datetime.strptime(value, DATE_FORMAT)
        except ValueError:
            print("日付の形式が正しくありません。例: 2023-09-01")
            value = None


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    start_input = args.start_date_override or args.start_date
    end_input = args.end_date_override or args.end_date

    start = _resolve_date(start_input, "開始日")
    end = _resolve_date(end_input, "終了日")

    while end < start:
        print("終了日は開始日以降の日付を入力してください。再入力します。")
        start = _resolve_date(None, "開始日")
        end = _resolve_date(None, "終了日")

    settings = _load_settings(args.config)
    driver_path = args.chrome_driver or _get_path_setting(
        settings, args.config, "amazon", "chrome_driver"
    )

    amazon_config = AmazonConfig(
        cookie_file=args.cookies,
        driver_path=driver_path,
    )
    gmail_config = GmailConfig(
        credentials_file=args.credentials,
        token_file=args.token,
    )

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
