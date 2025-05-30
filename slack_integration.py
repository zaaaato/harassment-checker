"""
モデレーションボットのSlack API接続、アプリ初期化、およびイベント処理登録を管理します。

このモジュールは以下の機能を提供します:
- Slack Boltアプリインスタンスの作成と設定。
- Slackメッセージイベントのハンドラ登録。
"""
import logging
from slack_bolt import App
# SLACK_APP_TOKENは、ここのコア関数ではなく、__main__ブロックの例のためにインポートされます。
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN 

logger = logging.getLogger(__name__)

def create_slack_app():
    """
    Slack Boltアプリインスタンスを初期化して返します。

    この関数は、アプリケーションの設定（`config.py`経由で読み込まれる）で
    `SLACK_BOT_TOKEN`が利用可能であることに依存しています。Boltアプリインスタンスは、
    Slack APIとのやり取り（イベント受信、メッセージ送信など）を行う中心的なオブジェクトです。

    Returns:
        slack_bolt.App: 初期化されたSlack Boltアプリのインスタンス。
                        SLACK_BOT_TOKENが設定されていない場合はNoneを返しますが、
                        その前にconfig.pyがValueErrorを発生させるはずです。
    """
    if not SLACK_BOT_TOKEN:
        # このチェックは安全策です。config.pyはSLACK_BOT_TOKENが欠落している場合、
        # ValueErrorを発生させ、実行をこのポイントより前に停止することが期待されます。
        logger.critical("SLACK_BOT_TOKENが設定されていません。Slackアプリを作成できません。")
        return None
    
    # Slack Boltアプリをボットトークンで初期化します。
    app = App(token=SLACK_BOT_TOKEN)
    logger.info("SLACK_BOT_TOKENを使用してSlack Boltアプリが正常に初期化されました。")
    return app

def register_message_handler(app: App, handler_function):
    """
    指定された関数をSlackの受信メッセージイベントを処理するために登録します。

    この関数は、Slack Boltの`@app.message("")`デコレータパターンを使用して、
    ボットが存在するチャンネルのすべてのメッセージをリッスンします。提供された
    `handler_function`は、新しいメッセージが受信されたときに呼び出されます。

    Args:
        app (slack_bolt.App): ハンドラを登録する初期化済みSlack Boltアプリインスタンス。
        handler_function (callable): メッセージイベント発生時に実行される関数。
                                     この関数は通常、Slack Boltによって提供される
                                     `message`および`say`引数を受け入れる必要があります。
    """
    if not app:
        logger.error("SlackアプリインスタンスがNoneです。メッセージハンドラを登録できません。")
        return

    # @app.message("")デコレータは、すべての非サブタイプメッセージをリッスンします。
    # パターンとして空文字列""はすべてのメッセージに一致します。
    # Slack Boltは、ラップされたハンドラに'message'（ペイロード）と'say'（ユーティリティ関数）を渡します。
    @app.message("") 
    def message_wrapper(message, say):
        # このラッパーは、ユーザー提供のhandler_function内で発生した例外をキャッチしてログに記録し、
        # メインアプリのイベントループがクラッシュするのを防ぎます。
        try:
            handler_function(message, say)
        except Exception as e:
            logger.exception(f"登録されたメッセージハンドラでエラーが発生しました：{e}")
            # オプションで、適切であれば`say`経由でSlackに一般的なエラーメッセージを送信することもできますが、
            # エラーループや詳細の過度の公開には注意してください。
            # try:
            #     say(text="メッセージ処理中に予期しないエラーが発生しました。管理者に通知されました。")
            # except Exception as say_error:
            #     logger.error(f"Slackチャンネルへのエラーメッセージ送信に失敗しました：{say_error}")

    logger.info(f"メッセージハンドラ '{handler_function.__name__}' がすべてのメッセージをリッスンするために正常に登録されました。")


# このブロックは、このモジュールの関数の基本的な検証または直接テスト用です。
# 完全なアプリケーションの実行を目的としたものではありません（それはapp.py経由で行われます）。
if __name__ == "__main__":
    # config.pyが読み込まれ、ロギングが設定され、環境変数が利用可能になるようにします。
    try:
        import config # これにより、ロギング設定や環境変数読み込みを含むconfig.pyが実行されます。
        logger.info("slack_integration.pyの直接実行用にconfigモジュールが正常に読み込まれました。")
    except ValueError as e:
        # これは通常、.envまたは環境に不可欠なAPIキーが欠落している場合に発生します。
        logger.critical(f"環境変数の欠落によりconfigの読み込みに失敗しました：{e}")
        logger.warning("不可欠なAPIキーなしではslack_integration.pyの__main__ブロックを実行できません。")
        exit(1) # モジュールの関数が期待通りに動作しない可能性があるため終了します。

    logger.info("--- Slack Integration Direct Test ---") # Slack統合ダイレクトテスト
    logger.info("基本的なチェックのためにSlackアプリの初期化を試みています...")
    
    # SLACK_BOT_TOKENが利用可能かどうかを確認します（config.pyのインポートにより利用可能であるはずです）。
    if not SLACK_BOT_TOKEN:
        logger.error("configインポート後もSLACK_BOT_TOKENが見つかりません。configが正しければこれは発生しないはずです。")
    else:
        # アプリインスタンスの作成をテストします。
        app_instance = create_slack_app()
        if app_instance:
            logger.info("slack_integration.create_slack_app()が__main__で正常に実行されました。")
            
            # 登録テスト用のダミーハンドラ
            def _dummy_test_handler(message, say):
                logger.info(f"__main__の_dummy_test_handlerがメッセージで呼び出されました：{message.get('text')}")
            
            register_message_handler(app_instance, _dummy_test_handler)
            logger.info("slack_integration.register_message_handler()が__main__で呼び出されました。")
            logger.info("注意：これはSlack接続やイベントリスナーを開始しません。")
            logger.info("完全なボットを実行してSlackに接続するには、app.pyを実行してください。")

            # SLACK_APP_TOKENも設定されている場合、理論的にはここでSocketModeHandlerを開始してより詳細なテストを行うことができますが、
            # それはこのスクリプトをブロックし、Slackへの接続を試みます。
            if SLACK_APP_TOKEN:
                logger.info("SLACK_APP_TOKENも設定されています。")
                logger.info("SocketModeHandlerを使用した完全なテストについては、app.pyを実行してください。")
            else:
                logger.warning("SLACK_APP_TOKENが設定されていません。app.py経由での完全なアプリ実行にはソケットモードのためにそれが必要です。")
        else:
            logger.error("__main__の直接実行でSlackアプリインスタンスの作成に失敗しました。")
    logger.info("--- End of Slack Integration Direct Test ---") # Slack統合ダイレクトテスト終了
