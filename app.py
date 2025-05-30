"""
Slackモデレーションボットのメインアプリケーションファイルです。

このスクリプトは、Slack Boltアプリを初期化し、メッセージハンドラを設定し、
Socket Modeハンドラを開始してSlackイベントをリッスンします。
コンテンツモデレーションのためにOpenAIと統合し、モデレーション結果に基づいて
通知を送信します。
"""
import logging

# 最初にconfigモジュールをインポートします。これは、config.pyがロギングを初期化し、
# 他のモジュールで利用可能になるすべての環境変数を読み込むため、非常に重要です。
import config 

# Slack統合のためのSlack Boltライブラリからのインポート。
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ローカルアプリケーションモジュールからのインポート。
# これらのモジュールは、上記の'config'インポートによって読み込まれた設定に依存しています。
from config import (
    # SLACK_BOT_TOKENは、config経由でcreate_slack_appによって内部的に使用されます。
    SLACK_APP_TOKEN,      # SocketModeHandlerに必要です。
    OPENAI_API_KEY,       # モデレーションに不可欠であり、ここで読み込まれたことを確認します。
    HARASSMENT_CATEGORIES,# OpenAIモデレーションからチェックするカテゴリのリスト。
    SLACK_NOTIFICATION_CHANNEL_ID # 通知用のオプションチャネル。
)
from slack_integration import create_slack_app, register_message_handler
from openai_integration import moderate_text


# このモジュール（app.py）用のロガーインスタンスを取得します。
# ロギング設定（レベル、フォーマット）は既にconfig.pyによって設定されています。
logger = logging.getLogger(__name__)

# slack_integrationの関数を使用してSlack Boltアプリインスタンスを初期化します。
# この関数は内部的にconfig.pyのSLACK_BOT_TOKENを使用します。
# 'app'オブジェクトは、SlackイベントとAPI呼び出しを処理する中心的なものです。
app = create_slack_app() 

if not app:
    # この状態は、Slackアプリの初期化における重大な失敗を示しており、
    # おそらくSLACK_BOT_TOKENが設定されていないためです（ただし、config.pyがこれをキャッチするはずです）。
    # 有効な'app'インスタンスなしではアプリケーションは続行できません。
    logger.critical(
        "重大なエラー：Slackアプリ（appオブジェクト）を初期化できませんでした。"
        "これは多くの場合、SLACK_BOT_TOKENが欠落しているか無効であることを意味します。アプリケーションを開始できません。"
    )
    # 本番シナリオでは終了を検討してください：exit(1)
    # config.pyは既に不可欠なキーの欠落に対してValueErrorを発生させており、これにより実行が停止するはずです。


def message_moderation_handler(message: dict, say: callable):
    """
    受信したSlackメッセージを処理し、OpenAIを使用してそのテキストをモデレートし、
    特定のハラスメントカテゴリが検出された場合に通知を送信します。

    この関数は、Slack Boltアプリのメッセージハンドラとして登録されます。

    Args:
        message (dict): Slackメッセージイベントのペイロード。この辞書には、
                        メッセージ、送信者、チャンネルなどの詳細が含まれています。
        say (callable): 受信メッセージが受信されたチャンネルにメッセージを返信するために
                        Slack Boltによって提供されるユーティリティ関数。
                        スレッドでの返信にも使用できます。
    
    Interactions:
    - `openai_integration.moderate_text`を呼び出してモデレーション分析を取得します。
    - 結果を`config.py`の`HARASSMENT_CATEGORIES`と照合します。
    - `say`（スレッド返信または同一チャンネルメッセージ用）または
      `app.client.chat_postMessage`（専用通知チャンネル用、
      `SLACK_NOTIFICATION_CHANNEL_ID`が設定されている場合）を使用して通知を送信します。
    """
    # メッセージペイロードからテキストコンテンツとユーザーIDを抽出します。
    # これらのフィールドが予期せず欠落している場合に備えて、ロギング用のデフォルト値を提供します。
    text_to_moderate = message.get('text')
    user_id = message.get('user', 'UnknownUser') 
    message_id = message.get('client_msg_id', 'UnknownMsgId') # メッセージの一意のID。ロギングに役立ちます。
    channel_id = message.get('channel', 'UnknownChannel')     # メッセージが投稿されたチャンネルのID。
    message_ts = message.get('ts')                            # メッセージのタイムスタンプ。スレッド返信に使用します。

    # メッセージにテキストがない場合（例：添付ファイルのみのメッセージ、または特定のイベントタイプ）、処理をスキップします。
    if not text_to_moderate:
        logger.debug(
            f"メッセージ（ID: {message_id}）をユーザー {user_id}（チャンネル: {channel_id}）からスキップします。"
            "モデレートするテキストが含まれていません。"
        )
        return

    logger.info(
        f"メッセージ（ID: {message_id}）をユーザー <@{user_id}>（チャンネル: <#{channel_id}>）からモデレート中。"
        f"テキスト：「{text_to_moderate[:100]}...」" # メッセージの一部をログに記録します。
    )

    # openai_integrationのラッパー関数を介してOpenAIモデレーションAPIを呼び出します。
    moderation_result = moderate_text(text_to_moderate)

    # モデレーション呼び出しが失敗した場合（例：APIエラー、ネットワークの問題）、moderate_textはNoneを返します。
    if moderation_result is None:
        logger.error(
            f"OpenAI Moderation APIの呼び出しがメッセージID {message_id}（ユーザー: <@{user_id}>、チャンネル: <#{channel_id}>）で失敗しました。"
            f"元のテキスト：「{text_to_moderate[:100]}...」"
        )
        # オプションで、ユーザーまたはチャンネルにエラーについて通知することもできますが、注意が必要です。
        # 例：say(text=f"申し訳ありません、<@{user_id}>さん。モデレーションシステムのエラーのため、メッセージを処理できませんでした。")
        return

    # OpenAIによってTrueとフラグ付けされ、かつHARASSMENT_CATEGORIESリストに含まれるカテゴリを収集します。
    detected_categories = []
    # OpenAI SDKのモデレーション結果オブジェクトには「categories」属性があり、
    # それ自体が各カテゴリのブール属性を持っています（例：categories.harassment）。
    # config.pyのHARASSMENT_CATEGORIESはこれらをアンダースコア区切りの文字列として保存します。
    for category_name in HARASSMENT_CATEGORIES: 
        # getattrを使用して、moderation_result.categoriesオブジェクトのカテゴリ属性に安全にアクセスします。
        # 何らかの理由でcategory_name属性が存在しない場合は、デフォルトでFalseになります。
        if getattr(moderation_result.categories, category_name, False):
            # 必要に応じて、アンダースコアスタイルをスラッシュスタイルに戻して表示するか、そのままにします。
            detected_categories.append(category_name.replace('_', '/')) 

    # 指定したハラスメントカテゴリのいずれかが検出された場合：
    if detected_categories:
        display_categories = ', '.join(detected_categories) # 通知メッセージ用にフォーマットします。
        
        # 元のメッセージへの直接Slackリンクを構築します。
        original_message_link = "元のメッセージ（リンク利用不可）"
        if channel_id != 'UnknownChannel' and message_ts:
            original_message_link = f"slack://channel/{channel_id}/p{message_ts.replace('.', '')}"

        # 通知テキストを準備します。日本語でより明確な構造化されたアプローチを使用します。
        notification_text = (
            f":warning: 不適切な可能性のあるメッセージが検出されました。\n"
            f"ユーザー: <@{user_id}>\n"
            f"チャンネル: <#{channel_id}>\n"
            f"検出カテゴリ: *{display_categories}*\n"
            f"元のメッセージへのリンク: <{original_message_link}>\n"
            f"メッセージ内容:\n> _{text_to_moderate}_"
        )
        
        logger.info(
            f"メッセージ（ID: {message_id}）がユーザー <@{user_id}>（チャンネル: <#{channel_id}>）からカテゴリ「{display_categories}」でフラグ付けされました。"
            "通知を送信しています。"
        )
        try:
            # 特定の通知チャンネルが設定されている場合は、そこにメッセージを送信します。
            if SLACK_NOTIFICATION_CHANNEL_ID:
                logger.info(
                    f"メッセージID {message_id} の通知を専用チャンネル（{SLACK_NOTIFICATION_CHANNEL_ID}）に送信しています。"
                )
                # 特定のチャンネルへの送信にはapp.client.chat_postMessageを使用します。
                # これには「chat:write」ボットスコープが必要です。
                app.client.chat_postMessage(
                    channel=SLACK_NOTIFICATION_CHANNEL_ID,
                    text=notification_text
                )
            else:
                # 専用チャンネルがない場合は、元のメッセージのスレッドに返信します（またはtsがない場合は単にチャンネルに）。
                reply_target_log = f"チャンネル {channel_id}"
                if message_ts:
                    reply_target_log = f"チャンネル {channel_id} のスレッド {message_ts}"

                logger.info(
                    f"メッセージID {message_id} のために {reply_target_log} に返信しています。"
                )
                if not message_ts: 
                     logger.warning(
                         f"メッセージ（ID: {message_id}）がユーザー {user_id} から「ts」（タイムスタンプ）が欠落しています。"
                         "スレッドに返信できません。通知を直接チャンネルに送信します。"
                     )
                     say(text=notification_text) # 'ts'がない場合はチャンネルに送信します（例：一部のイベントタイプ）。
                else:
                     say(text=notification_text, thread_ts=message_ts) # スレッドに返信します。
            logger.info(f"ユーザー <@{user_id}>（メッセージID: {message_id}）へのモデレーション通知を正常に送信しました。")
        except Exception as e:
            logger.exception(
                f"ユーザー <@{user_id}>（メッセージID: {message_id}）へのSlack通知送信中にエラーが発生しました：{e}"
            )
    else:
        # メッセージがOpenAIによって全体的にフラグ付けされたが、指定したローカルカテゴリのいずれにも該当しなかった場合にログを記録します。
        # これは、HARASSMENT_CATEGORIESリストの調整が必要かどうかを理解するのに役立ちます。
        openai_flag_status_log = "OpenAIによってフラグ付けされました" if moderation_result.flagged else "クリーン"
        if moderation_result.flagged:
            all_openai_flagged_categories = [
                cat.replace('_', '/') for cat, val in moderation_result.categories.__dict__.items() if val
            ]
            details = (
                f"（OpenAI overall_flagged: {moderation_result.flagged}。"
                f" OpenAIカテゴリ：{all_openai_flagged_categories if all_openai_flagged_categories else '特定のものなし'}）"
            )
        else:
            details = f"（OpenAI overall_flagged: {moderation_result.flagged}）"
            
        logger.info(
            f"メッセージ（ID: {message_id}）がユーザー <@{user_id}>（チャンネル: <#{channel_id}>）からローカルポリシーによって「{openai_flag_status_log}」と判断されました。"
            f"{details} "
            f"テキスト：「{text_to_moderate[:50]}...」"
        )


# Slackアプリインスタンスにmessage_moderation_handlerを登録します。
# これにより、新しいメッセージイベントが受信されるたびにこの関数を呼び出すようアプリに指示します。
if app:
    register_message_handler(app, message_moderation_handler)
else:
    # このケースは、理想的にはconfig.py/create_slack_appでの以前のチェックまたはエラーによって防止されるべきです。
    logger.critical(
        "重大なエラー：SlackアプオブジェクトがNoneです。メッセージハンドラを登録できません。アプリケーションはメッセージを処理しません。"
    )

# このブロックは、スクリプトが直接実行された場合（例：`python app.py`）にのみ実行されます。
if __name__ == "__main__":
    logger.info("Slackモデレーションボットアプリケーションを開始しています...")
    
    # 開始前に最終チェックを実行します。
    # 不可欠なAPIキー（SLACK_BOT_TOKEN、OPENAI_API_KEY）はconfig.pyで検証されます。
    # SLACK_APP_TOKENも、SocketModeHandlerに不可欠であるため、config.pyで検証されます。
    if not app:
        # これは最終的な安全策です。ここで「app」がNoneの場合、create_slack_app()が失敗したことを意味します。
        logger.critical(
            "アプリケーションを開始できません：Slackアプリインスタンス（「app」）が初期化されていません。"
            "以前のログ、特にSLACK_BOT_TOKENに関するエラーを確認してください。"
        )
    # SLACK_APP_TOKENはSocketModeHandlerに特に必要です。
    # config.pyは、欠落している場合に既にエラーを発生させているはずです。
    elif not SLACK_APP_TOKEN: 
        logger.critical(
            "アプリケーションを開始できません：SLACK_APP_TOKENが設定されていません。"
            "SocketModeHandlerにはそれが必要です。.envファイルまたは環境変数を確認してください。"
        )
    else:
        logger.info("Slackボットトークン、アプリトークン、およびOpenAI APIキーが設定されています。")
        logger.info("Slack SocketModeHandlerの開始を試みています...")
        try:
            # Socket Modeハンドラを開始します。これによりSlackに接続し、イベントのリッスンを開始します。
            # これはブロッキング呼び出しなので、アプリケーションを実行し続けます。
            SocketModeHandler(app, SLACK_APP_TOKEN).start()
        except Exception as e:
            # SocketModeHandlerの開始を妨げる重大なエラーをログに記録します。
            logger.critical(f"致命的：SocketModeHandlerの開始に失敗しました：{e}", exc_info=True)
            logger.critical(
                "SLACK_APP_TOKENが正しいこと、およびSlackアプリがその設定でソケットモード用に設定されていることを確認してください。"
                "また、ネットワーク接続も確認してください。"
            )
