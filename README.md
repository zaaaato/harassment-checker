# Slackモデレーションボット

このボットはSlackメッセージを監視し、OpenAI Moderation APIを使用して潜在的にハラスメントのあるコンテンツを検出し、通知します。

## 主な機能

*   Slackワークスペース内の参加しているチャンネルのメッセージを監視します。
*   コンテンツ分析にOpenAIのModeration APIを使用します。
*   設定可能なカテゴリリスト（例：ハラスメント、ヘイトスピーチ）に基づいてメッセージにフラグを立てます。
*   指定されたSlackチャンネルまたは元のメッセージへのスレッド返信として通知を送信します。
*   環境変数（`.env`ファイルをサポート）による設定。
*   監視とデバッグのための構造化されたロギング。

## プロジェクト構成

```
.
├── app.py                   # メインアプリケーションロジック、メッセージ処理、Socket Modeランナー
├── config.py                # 設定読み込み（.envから）、ロギング設定、ハラスメントカテゴリ
├── openai_integration.py    # OpenAI API通信処理
├── slack_integration.py     # Slack Boltアプリ設定およびメッセージ登録処理
├── requirements.txt         # Python依存関係
├── .env.example             # 環境ファイル例（ローカル開発用）
└── README.md                # このファイル
```

## 前提条件

*   Python 3.8以降
*   アプリをインストールする権限を持つSlackワークスペース。
*   Moderation APIにアクセスできるOpenAI APIキー。

## セットアップ手順

### 1. リポジトリのクローン

リポジトリへのアクセス権がある場合は、クローンします。そうでない場合は、プロジェクトファイルがあることを確認してください。
```bash
# 例:
# git clone <your_repository_url>
# cd <repository_directory_name>
```

### 2. Slackアプリの作成

1.  [https://api.slack.com/apps](https://api.slack.com/apps) にアクセスし、「Create New App」をクリックします。
2.  「From scratch」を選択します。
3.  アプリに名前を付け（例：「Moderation Bot」）、ワークスペースを選択します。「Create App」をクリックします。
4.  **ボットトークンスコープの追加**:
    *   アプリ設定ページのサイドバーで「OAuth & Permissions」に移動します。
    *   「Scopes」 > 「Bot Token Scopes」までスクロールダウンします。
    *   「Add an OAuth Scope」をクリックし、以下を追加します:
        *   `chat:write` （メッセージと通知を送信するため）
        *   `channels:history` （ボットが参加しているパブリックチャンネルのメッセージを読むため）
        *   `groups:history` （ボットが招待されたプライベートチャンネルのメッセージを読むため）
        *   `mpim:history` （ボットが招待されたグループDMのメッセージを読むため）
        *   `im:history` （ボットが参加しているDMを読むため、ダイレクトメッセージングを意図している場合）
        *   `channels:read` （チャンネル名を取得するため、ボットがチャンネルに参加/退出する際のロギング/通知に役立ちます）
        *   `users:read` （オプション、ユーザーメンションを名前に解決するため - 現在の機能では厳密には必要ないかもしれませんが、将来の機能拡張に役立ちます）
5.  **ワークスペースへのアプリのインストール**:
    *   引き続き「OAuth & Permissions」で、上にスクロールして「Install to Workspace」をクリックします。
    *   プロンプトに従ってアプリを承認します。
    *   インストール後、**Bot User OAuth Token**（`xoxb-`で始まります）をコピーします。これが`SLACK_BOT_TOKEN`です。
6.  **Socket Modeの有効化とアプリレベルトークンの生成**:
    *   サイドバーで「Basic Information」に移動します。
    *   「App-Level Tokens」までスクロールダウンします。
    *   「Generate Token and Scopes」をクリックします。
    *   トークンに名前を付け（例：`socket-mode-token`）、`connections:write`スコープを追加します。「Generate」をクリックします。
    *   このトークン（`xapp-`で始まります）をコピーします。これが`SLACK_APP_TOKEN`です。
    *   サイドバーの「Socket Mode」（「Settings」の下）に移動します。
    *   スイッチを切り替えてSocket Modeを有効にします。`xapp-`トークンがリストされているはずです。
7.  **ボットをチャンネルに招待する**:
    *   Slackクライアントで、監視したいパブリックまたはプライベートチャンネルにボットユーザー（例：「@Moderation Bot」）を招待します。ボットはメンバーになっているチャンネルのメッセージのみを処理します。

### 3. OpenAI APIキーの取得

1.  [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys) にアクセスします。
2.  OpenAIアカウントにログインまたはサインアップします。
3.  「Create new secret key」をクリックします。
4.  生成されたキーをコピーします。これが`OPENAI_API_KEY`です。安全に保管してください。

### 4. 環境変数の設定

1.  プロジェクトのルートディレクトリに`.env`という名前のファイルを作成します（例：`.env.example`をコピー）。
    ```bash
    cp .env.example .env
    ```
2.  取得したトークンとキーで`.env`ファイルを編集します。
    ```ini
    SLACK_BOT_TOKEN="xoxb-your-bot-user-oauth-token"
    SLACK_APP_TOKEN="xapp-your-app-level-socket-mode-token"
    OPENAI_API_KEY="sk-your-openai-api-key"

    # オプション：すべての通知を送信する特定のチャンネルIDを指定します。
    # コメントアウトされているか空の場合、通知は元のメッセージが投稿された
    # チャンネルへのスレッド返信として送信されます。
    # チャンネルIDは、Slackでチャンネルを右クリックし、「リンクをコピー」を選択し、
    # URLからID（Cで始まる）を抽出することで見つけられます。
    # 例：SLACK_NOTIFICATION_CHANNEL_ID="C0123ABCXYZ"

    # オプション：ロギングレベルを設定します（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    # 設定されていない場合、デフォルトはINFOです。
    # 例：LOGGING_LEVEL="DEBUG"
    ```
    プレースホルダの値を実際の認証情報に置き換えてください。

### 5. 依存関係のインストール

Python 3.8以降がインストールされていることを確認してください。仮想環境の使用をお勧めします:
```bash
python3 -m venv venv
source venv/bin/activate  # Windowsでは `venv\Scripts\activate` を使用
```
次に、必要なパッケージをインストールします:
```bash
pip install -r requirements.txt
```

## アプリケーションの実行

セットアップが完了したら、ボットを実行できます:
```bash
python app.py
```
ボットはSocket Modeを使用してSlackに接続します。コンソールに起動し、メッセージをリッスンしていることを示すログメッセージが表示されるはずです。

ボットを停止するには、コンソールで`Ctrl+C`を押します。

## ユニットテストの実行

ユニットテストは`tests/`ディレクトリにあります。実行するには：
```bash
python -m unittest discover -s tests
```
このコマンドは`tests`ディレクトリ内のすべてのテストを検出し、実行します。テスト設定が環境変数に依存している場合は、必要な環境変数が設定されていることを確認してください（ただし、理想的にはテストは外部サービスと設定をモックする必要があります）。

（`slack_integration.py`や`app.py`など、他のモジュールのさらなるテストは将来追加される予定です。）

## 設定変数

アプリケーションは以下の環境変数を使用します（通常は`.env`ファイルで設定されます）：

*   `SLACK_BOT_TOKEN`（必須）：SlackボットユーザーOAuthトークン（`xoxb-`で始まります）。
*   `SLACK_APP_TOKEN`（必須）：Socket Mode用のSlackアプリレベルトークン（`xapp-`で始まります）。
*   `OPENAI_API_KEY`（必須）：OpenAI APIキー（`sk-`で始まります）。
*   `SLACK_NOTIFICATION_CHANNEL_ID`（オプション）：設定されている場合、すべてのモデレーション通知がこの特定のSlackチャンネルIDに送信されます。設定されていないかコメントアウトされている場合、通知は元のメッセージが投稿されたチャンネルへのスレッド返信として送信されます。
*   `LOGGING_LEVEL`（オプション）：アプリケーションのロギングレベルを設定します。デフォルトは`INFO`です。有効な値：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`。

## ハラスメントカテゴリ

ボットは現在、以下のOpenAI Moderation APIカテゴリをチェックします。これらは`config.py`で定義されており、OpenAI SDKのモデレーションレスポンスの属性に基づいています:
```python
# config.py内にあります
HARASSMENT_CATEGORIES = [
    'harassment',               # 個人またはグループを対象とした虐待的なコンテンツ
    'harassment_threatening',   # 脅迫的な言葉も含むハラスメント
    'hate',                     # 保護された特性に基づく憎悪表現、扇動、助長
    'hate_threatening',         # 脅迫的な言葉も含むヘイトスピーチ
    'self_harm',                # 自傷行為の助長、奨励、描写
    'self_harm_intent',         # 自傷の意図を表明するコンテンツ
    'self_harm_instructions',   # 自傷行為の方法を提供するコンテンツ
    'sexual',                   # 性的興奮を意図したコンテンツ（例：性的活動の描写）
    'sexual_minors',            # 未成年者を含む性的コンテンツ
    'violence',                 # 暴力の助長・美化、他者の苦痛・屈辱の称賛
    'violence_graphic'          # 死、流血、極度の暴力描写を含むグラフィックな暴力
]
```
OpenAI Moderation APIが提供する異なるカテゴリセットに焦点を合わせたい場合は、このリストを`config.py`で直接変更できます。
```
