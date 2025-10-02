# Amazon & Gmail Order Synchronizer

このリポジトリには、Amazonの注文履歴とGmailの通知メールを突き合わせてCSVに書き出すスクリプトが含まれています。Amazonには初回のみ手動でログインし、セッション情報をクッキーとして保存することで、次回以降の取得を自動化できます。

## 機能概要

- 指定した日付範囲のAmazon注文履歴をSeleniumで取得
- 取得した注文番号をGmailで検索し、注文ステータスを判定
- 宅配ボックスへの配達が検出された場合はボックス番号・暗証番号を抽出
- すべての結果をUTF-8 (BOM付き) のCSVに書き出し
- 宅配ボックス用のテンプレート文を自動生成

## 事前準備

1. **Python パッケージのインストール**
   ```bash
   pip install -r requirements.txt
   ```

2. **Gmail API の設定**
   - Google Cloud Consoleでプロジェクトを作成し、Gmail APIを有効化します。
   - 認証情報から「OAuthクライアントID (デスクトップアプリ)」を作成し、`credentials.json` をリポジトリ直下に配置します。
   - 初回実行時はブラウザが起動し、Googleアカウントの認可を求められます。

3. **Amazon への手動ログイン**
   - スクリプトがSeleniumでブラウザを起動します。初回はAmazonに手動でログインし、ログイン完了後にコンソールへ戻ってEnterキーを押してください。
   - 認証済みのクッキーが `cookies.json` として保存され、以降の取得に利用されます。

## 使い方

```bash
python main.py 2023-09-01 2023-09-30 \
  --output data/orders.csv \
  --cookies data/cookies.json \
  --credentials credentials.json \
  --token data/token.json
```

- `start_date` と `end_date` はどちらも `YYYY-MM-DD` 形式です。
- `--output` でCSVの出力先を指定できます (既定値: `orders.csv`)。
- `--cookies` はAmazonセッションの保存先ファイルを指定します。
- `--credentials` はGmail APIのクライアントシークレットファイル、`--token` はアクセストークンの保存先です。

実行後、指定したCSVファイルに次の列が出力されます。

| 列名 | 説明 |
| ---- | ---- |
| 年月日 | 注文日 |
| 金額 | Amazon注文履歴に表示される金額 |
| お届け先（名前） | 配送先の氏名 |
| お届け先（住所） | 配送先の住所 |
| 商品名 | 商品のタイトル |
| 個数 | 注文数 |
| 注文番号 | Amazonの注文番号 |
| 到着日 | 「9月25日到着済」「10月2日到着予定」などに整形 |
| ステータス | Gmailから判定した注文ステータス |
| 宅配ボックス情報 | ボックス番号・暗証番号の情報 |
| テンプレート文 | 宅配ボックス用のテンプレート文章 |

## 注意事項

- Amazonのページ構造は変更される可能性があります。レイアウト変更により要素が取得できなくなった場合は、`order_sync/amazon.py` のセレクタを調整してください。
- `webdriver-manager` がブラウザドライバーをダウンロードするため、初回実行時にインターネット接続が必要です。
- Gmailの検索は最大5件のメールを対象にしています。必要に応じて `order_sync/gmail_client.py` の `find_status` 内で調整してください。
- 取得したCSVには個人情報が含まれるため、適切に管理・保管してください。

## ライセンス

このプロジェクトはMITライセンスで提供されています。
