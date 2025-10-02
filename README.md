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


   > `requirements.txt` に PyInstaller も含まれているため、後述の EXE 化手順を行う場合に追加インストールは不要です。

2. **Gmail API の設定（初心者向けステップ）**
   1. [Google Cloud Console](https://console.cloud.google.com/) を開き、右上の「プロジェクトを選択」→「新しいプロジェクト」をクリックして任意の名前でプロジェクトを作成します。
   2. 左上のハンバーガーメニューから「APIとサービス」→「ライブラリ」を開き、検索ボックスで「Gmail API」を検索して「有効にする」をクリックします。
   3. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」を選択します。
      - 事前に「同意画面を構成」ボタンが出た場合は、ユーザータイプで「外部」を選び、アプリ名とサポートメールを入力して保存します。
      - アプリケーションの種類は「デスクトップアプリ」を選択し、名前は任意でOKです。
   4. 作成されたクライアントIDのダウンロードボタンから `credentials.json` を取得し、このリポジトリの直下（`main.py` と同じ階層）に保存します。
   5. 初回にスクリプトを実行するとブラウザが立ち上がるので、Googleアカウントでログインしてアクセス権限を承認してください。認可後、`token.json` が自動生成されます。

3. **Amazon への手動ログイン**
   - スクリプトがSeleniumでブラウザを起動します。初回はAmazonに手動でログインし、ログイン完了後にコンソールへ戻ってEnterキーを押してください。
   - 認証済みのクッキーが `cookies.json` として保存され、以降の取得に利用されます。

## 使い方

```bash

python main.py
```

1. 実行するとコンソールに「開始日 (YYYY-MM-DD)」「終了日 (YYYY-MM-DD)」の入力が順番に表示されるので、例 `2023-09-01` のように入力してください。
2. 空欄や形式が正しくない場合は、再入力を促すメッセージが表示されます。
3. 日付入力後は自動でAmazon→Gmail→CSV出力の処理が行われ、完了すると `orders.csv` へ件数とともに書き出し結果が表示されます。

オプションとして、以下のように引数を指定してバッチ処理も可能です。

```bash
python main.py --start-date 2023-09-01 --end-date 2023-09-30 \

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
- `--config` で設定値を記述したTOMLファイルを指定できます (既定値: `config.toml`)。
- `--chrome-driver` で既にダウンロード済みのChromeDriverバイナリを指定できます。

### config.toml での設定 (任意)

リポジトリには `config.example.toml` を用意しています。必要に応じてコピーして `config.toml` を作成し、以下のように値を編集すると毎回のコマンド入力を簡略化できます。

```toml
[amazon]
chrome_driver = "C:/tools/chromedriver.exe"
```

- `config.toml` を別の場所に置きたい場合は、`python main.py --config path/to/config.toml` のようにファイルパスを指定してください。
- コマンドライン引数 (`--chrome-driver` など) は設定ファイルの値よりも優先されます。一時的に上書きしたい場合に便利です。

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
- Windows 32bit 環境や企業ネットワークなど、`webdriver-manager` が互換性のあるChromeDriverを取得できない場合は手動でドライバーを用意してください。
  1. 使用しているChromeのバージョンを確認し、[Chrome for Testing (ChromeDriver) の公式ダウンロードページ](https://googlechromelabs.github.io/chrome-for-testing/) から対応するバージョンとプラットフォームのアーカイブを取得します。
  2. アーカイブを解凍し、`chromedriver`（Windowsでは `chromedriver.exe`）を任意のフォルダーに配置します。
  3. `config.example.toml` を `config.toml` にコピーし、`amazon.chrome_driver` に配置したファイルへのパスを記述します（例: `chrome_driver = "C:/tools/chromedriver.exe"`）。
  4. 一時的に別のバイナリを使いたい場合は、実行時に `--chrome-driver` オプションでパスを上書きできます（例: `python main.py 2023-09-01 2023-09-30 --chrome-driver C:\\tools\\chromedriver.exe`）。
- Gmailの検索は最大5件のメールを対象にしています。必要に応じて `order_sync/gmail_client.py` の `find_status` 内で調整してください。
- 取得したCSVには個人情報が含まれるため、適切に管理・保管してください。


## EXEファイルとして配布したい場合（任意）

1. 追加のライブラリは不要です（`pyinstaller` は既に `requirements.txt` に含まれています）。
2. プロジェクト直下で次のコマンドを実行すると、`dist/order_sync_tool.exe` が生成されます。
   ```bash
   pyinstaller --onefile --name order_sync_tool main.py
   ```
3. 生成された `order_sync_tool.exe` を配布し、同じフォルダに `credentials.json`（および初回実行後の `token.json`、`cookies.json`）を置いた状態で実行してください。
4. EXE 実行時もコンソールが開き、開始日と終了日の入力手順は Python 版と同じです。


## ライセンス

このプロジェクトはMITライセンスで提供されています。
