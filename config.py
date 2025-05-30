"""
環境変数から設定を読み込むことで、アプリケーションの設定を処理します。
ローカル開発用に .env ファイルからの読み込みをサポートし、
不可欠なAPIキーの検証を実行します。また、アプリケーションの基本的なログ設定も行います。
"""
import os
import logging
from dotenv import load_dotenv

# .env ファイルが存在する場合、そこから環境変数を読み込みます。
# これはローカル開発に役立ちます。本番環境では、通常、変数は直接設定されます。
load_dotenv()

# --- APIキーとトークン ---
# SLACK_BOT_TOKEN: SlackボットユーザーのOAuthトークン。ほとんどのボット操作に必要です。
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
# SLACK_APP_TOKEN: Slackソケットモード用のアプリレベルトークン。ソケットモード接続に必要です。
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
# OPENAI_API_KEY: OpenAIサービス用のAPIキー。Moderation APIへのアクセスに必要です。
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- 通知設定 ---
# SLACK_NOTIFICATION_CHANNEL_ID: モデレーション通知が送信されるオプションのSlackチャンネルID。
# 設定されていない場合、通知は元のメッセージがあったチャンネルへのスレッド返信として送信されます。
SLACK_NOTIFICATION_CHANNEL_ID = os.environ.get("SLACK_NOTIFICATION_CHANNEL_ID")

# --- モデレーション設定 ---
# HARASSMENT_CATEGORIES: OpenAI Moderation APIのカテゴリ名のリスト（属性スタイル）。
# アプリケーションがコンテンツをフラグ付けするために特に検索するものです。
# これらはOpenAI SDKのカテゴリオブジェクトのブール属性に対応します（例: result.categories.harassment）。
HARASSMENT_CATEGORIES = [
    'harassment',               # 個人またはグループを対象とした虐待的なコンテンツを表現するコンテンツ。
    'harassment_threatening',  # 脅迫的な言葉も含むハラスメント。
    'hate',                     # 保護された特性に基づいて憎悪を表現、扇動、または助長するコンテンツ。
    'hate_threatening',       # 脅迫的な言葉も含むヘイトスピーチ。
    'self_harm',                # 自傷行為を助長、奨励、または描写するコンテンツ。
    'self_harm_intent',         # ユーザーが自傷の意図を表明するコンテンツ。
    'self_harm_instructions',   # 自傷行為の方法を提供するコンテンツ。
    'sexual',                   #性的興奮を引き起こすことを意図したコンテンツ（例：性的活動の描写）。
    'sexual_minors',            #未成年者を含む性的コンテンツ。
    'violence',                 #暴力を助長または美化したり、他者の苦しみや屈辱を称賛したりするコンテンツ。
    'violence_graphic'          # 死、流血、または極端な暴力の描写を含むグラフィックな暴力。
]

# --- ログ設定 ---
# LOGGING_LEVEL: ログに記録するメッセージの最小重要度レベルを決定します。
# 環境で設定されていない場合、デフォルトは "INFO" です。
LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "INFO").upper()

# アプリケーション全体の基本的なログ設定を行います。
# この設定は、このモジュールが最初にインポートされるときに一度だけ行われます。
logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # ログフォーマット
    datefmt='%Y-%m-%d %H:%M:%S'  # ログエントリの日付フォーマット
)
# このモジュール（config.py）用のロガーを取得します。
logger = logging.getLogger(__name__)


# --- 不可欠な設定の検証 ---
# 起動時に不可欠なAPIキーを確認することが重要です。
# これらが欠落している場合、アプリケーションは正しく機能できません。
# ここでValueErrorを発生させると、重要な設定が欠落している場合にアプリケーションが停止します。
if not SLACK_BOT_TOKEN:
    logger.critical("CRITICAL: .env ファイルまたは環境に SLACK_BOT_TOKEN がありません。")
    raise ValueError(".env ファイルまたは環境に SLACK_BOT_TOKEN がありません。")
if not SLACK_APP_TOKEN:
    logger.critical("CRITICAL: .env ファイルまたは環境に SocketModeHandler 用の SLACK_APP_TOKEN がありません。")
    raise ValueError(".env ファイルまたは環境に SocketModeHandler 用の SLACK_APP_TOKEN がありません。")
if not OPENAI_API_KEY:
    logger.critical("CRITICAL: .env ファイルまたは環境に OPENAI_API_KEY がありません。")
    raise ValueError(".env ファイルまたは環境に OPENAI_API_KEY がありません。")

# 読み込まれた設定を検証のためにログに記録します（将来的にキーの機密部分を除外する必要があるかもしれません）。
logger.info("設定が正常に読み込まれました。")
logger.info(f"  SLACK_BOT_TOKEN: {'設定済み' if SLACK_BOT_TOKEN else '未設定'}")
logger.info(f"  SLACK_APP_TOKEN: {'設定済み' if SLACK_APP_TOKEN else '未設定'}")
logger.info(f"  OPENAI_API_KEY: {'設定済み' if OPENAI_API_KEY else '未設定'}")
logger.info(f"  SLACK_NOTIFICATION_CHANNEL_ID: {SLACK_NOTIFICATION_CHANNEL_ID if SLACK_NOTIFICATION_CHANNEL_ID else '未設定（スレッド/チャンネルで返信）'}")
# logger.debug(f"  HARASSMENT_CATEGORIES: {HARASSMENT_CATEGORIES}") # 長くなる可能性があるためデバッグとして
logger.info(f"  LOGGING_LEVEL: {LOGGING_LEVEL}")
