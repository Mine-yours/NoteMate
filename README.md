# NoteMate

NoteMate は講義資料の PDF をアップロードして閲覧し、Google Gemini を用いた専門用語の自動抽出・解説を提供する学習支援ツールです。Flask ベースのシンプルな Web アプリとして構築されており、ローカル環境で手軽に動かせます。

## 特長
- PDF をブラウザ上で即座に閲覧・ダウンロード・削除
- 資料ごとのノート機能（Markdown プレビュー・装飾ボタン・画像添付に対応）
- Google Gemini API を用いた専門用語抽出とページ単位解析
- チャットサイドバー（フリーチャット / 単語解説タブの 2 モード）
- 抽出・生成した語句を辞書として保存／削除できる「保存した用語」管理
- SQLite を利用した軽量な永続化（PDF・ノート・チャット・辞書を保存）

## セットアップ
### 事前準備
- Python 3.10 以上
- Google Gemini API キー（専門用語生成機能を利用する場合）

### 手順
1. 仮想環境を用意します（推奨）。
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. 依存パッケージをインストールします。
   ```bash
   pip install Flask google-generativeai PyPDF2
   ```
3. 必要な環境変数を設定します。開発中は `.env` などを利用しても構いません。
   ```bash
   export GOOGLE_API_KEY="あなたのAPIキー"
   export GEMINI_MODEL="models/gemini-2.0-flash"  # 任意。未設定時はこの値が既定値
   export SECRET_KEY="任意のシークレットキー"     # 未設定時は開発用のデフォルト値を利用
   ```

## 実行方法
Flask の開発サーバーを起動します。
```bash
flask --app app run --debug
```
起動後、`http://127.0.0.1:5000/` にアクセスしてアプリを利用できます。初回アクセス時に `database.db`（SQLite）が自動生成されます。

## 使い方
1. トップページで PDF をアップロードします（対応形式は `.pdf` のみ）。
2. アップロード済みの資料一覧から「開く」を押すと閲覧ページが開きます。
3. 閲覧ページ右側のサポートパネルから以下の機能を利用できます。
   - **専門用語**: 「専門用語を生成」ボタンで Gemini による抽出・解説を実行。ページ指定も可能です。
   - **ノート**: Markdown プレビューや装飾ボタン、画像添付を使って講義ノートを保存できます。
   - **チャット**: 「フリーチャット」で通常の QA、「単語の解説」で単語群の JSON 解説を生成。履歴はカテゴリ別に保持し、削除も可能です。
   - **辞書**: 保存済み用語を一覧で確認・削除できます。
4. 「保存した用語を見る」ボタンから辞書専用ページに移動し、講義横断で語句を整理できます。
5. 不要になった資料は一覧の「削除」でファイルと DB レコードを一括削除できます。

## ディレクトリ構成
```text
app/
 ├─ __init__.py          Flask アプリ本体と初期化処理
 ├─ db.py                SQLite とのやり取り（資料メタ情報の永続化）
 ├─ main.py              ルーティングと機能の中核ロジック
 ├─ static/              CSS、画像、アップロードファイル
 └─ templates/           HTML テンプレート
database.db               SQLite データベース（起動時に生成）
```

## クイック起動の例
ローカルでの起動を簡略化するため、以下のような方法が利用できます。

### 1. スタートアップスクリプトを用意
プロジェクト直下に `start_notemate.sh` を作成して実行権限を付与します。

```bash
#!/usr/bin/env bash
cd "$(dirname "$0")"

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

export FLASK_APP=app
export FLASK_ENV=development

flask run --host=127.0.0.1 --port=5000
```

```bash
chmod +x start_notemate.sh
./start_notemate.sh
```

### 2. シェルエイリアスを設定
`~/.zshrc` などに以下を追記すると、ターミナルで `notemate` と入力するだけで起動できます。

```bash
alias notemate='cd /Users/mineno/project/web/NoteMate && ./start_notemate.sh'
```

### 3. macOS Automator から実行
Automator で「アプリケーション」を作成し、シェルスクリプトとして `./start_notemate.sh` を呼び出すよう設定すれば Dock からワンクリックで起動できます。

## 補足
- Google Gemini API を利用できない環境では、専門用語生成機能はエラー応答となります。
- PyPDF2 がインストールされていない場合は PDF の解析が行えません。インストールを忘れずに行ってください。
- 本番利用を想定する場合は、ファイルサイズ上限の設定や認証・認可の導入を検討してください。