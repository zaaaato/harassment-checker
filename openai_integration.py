"""
OpenAI Moderation APIとのやり取り機能を提供します。

このモジュールは、OpenAIクライアントの初期化を処理し、
分析のためにモデレーションエンドポイントにテキストを送信する機能を提供します。
API呼び出しのエラー処理も含まれています。
"""
import openai
import logging
from config import OPENAI_API_KEY # configからAPIキーをインポートします。

logger = logging.getLogger(__name__)

# OpenAIクライアントを初期化します。
# このクライアントオブジェクトは、このモジュール内のすべてのOpenAI APIインタラクションに使用されます。
# モジュールが最初にインポートされるときに、config.pyのAPIキーを使用して初期化されます。
if not OPENAI_API_KEY:
    # この条件は主に安全策です。config.pyはOPENAI_API_KEYが欠落している場合、
    # ValueErrorを発生させ、通常このモジュールの読み込みを防ぎます。
    logger.error("CRITICAL: OPENAI_API_KEY が設定されていません。OpenAIクライアントを初期化できません。")
    client = None
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAIクライアントが正常に初期化されました。")
    except Exception as e:
        logger.exception("インポート中のOpenAIクライアントの初期化に失敗しました。")
        client = None


def moderate_text(text_to_moderate: str):
    """
    提供されたテキストをOpenAI Moderation APIに送信してコンテンツ分析を行います。

    Args:
        text_to_moderate (str): モデレートするテキスト文字列。

    Returns:
        openai.types.moderation.Moderation (またはSDKバージョンに基づく同様のオブジェクト): 
            呼び出しが成功した場合、OpenAI Moderation APIレスポンスからの最初の結果オブジェクト。
            フラグとカテゴリのスコアが含まれます。
        None: 
            OpenAIクライアントが初期化されていない場合、入力テキストが空またはNoneの場合、
            またはAPI呼び出し中にエラーが発生した場合（例：接続の問題、APIエラー、
            予期しないレスポンス構造）。
    """
    if not client:
        logger.error("OpenAIクライアントが初期化されていません。テキストをモデレートできません。")
        return None
    
    if not text_to_moderate: # 空またはNoneの入力テキストを確認します。
        logger.warning("空またはNoneのテキストをモデレートしようとしました。API呼び出しをスキップします。")
        return None

    try:
        # OpenAI Moderation APIエンドポイントを呼び出します。
        response = client.moderations.create(input=text_to_moderate)
        
        # レスポンスオブジェクトには通常、「results」リストが含まれています。
        # このリストの最初のアイテムに関心があります。
        if response.results and len(response.results) > 0:
            return response.results[0] # メインのモデレーション結果オブジェクトを返します。
        else:
            # レスポンス構造が期待通りでない場合はエラーをログに記録します。
            logger.error(f"予期しないOpenAI APIレスポンス構造：結果が見つかりません。レスポンス：{response}")
            return None
    # 特定のOpenAI APIエラーと一般的な例外を処理します。
    except openai.APIConnectionError as e:
        logger.exception(f"OpenAI APIリクエストの接続に失敗しました：{e}")
        return None
    except openai.RateLimitError as e:
        logger.exception(f"OpenAI APIリクエストがレート制限を超えました：{e}")
        return None
    except openai.APIStatusError as e: # HTTPステータスエラー（4xx、5xx）をカバーします。
        logger.exception(f"OpenAI APIがエラーステータスを返しました：{e.status_code} - {e.response}")
        return None
    except Exception as e: # その他の予期しないエラーをキャッチします。
        logger.exception(f"OpenAI Moderation APIの呼び出し中に予期しないエラーが発生しました：{e}")
        return None

# このブロックにより、このスクリプトが直接実行された場合（例：`python openai_integration.py`）、
# moderate_text関数の基本的なテストが可能になります。
if __name__ == "__main__":
    # これにより、config.py（ロギングを設定し、.envを読み込む）が処理されることが保証されます。
    # このモジュールのスタンドアロンテストにとって重要です。
    try:
        import config # configが読み込まれ、.env変数が利用可能になり、ロギングが設定されることを保証します。
        logger.info("openai_integration.pyの直接実行用にconfigが正常に読み込まれました。")
    except ValueError as e: 
        # これは、config.pyが不可欠なAPIキーの欠落によりValueErrorを発生させた場合に発生します。
        logger.critical(f"環境変数の欠落によりconfigの読み込みに失敗しました：{e}")
        logger.warning("不可欠なAPIキー（OPENAI_API_KEYなど）なしではopenai_integration.pyテストを実行できません。")
        # configが失敗した場合、クライアントは初期化されないため終了します。
        if not client: # クライアントの初期化自体がキーの欠落により以前に失敗したかどうかを確認します。
             exit(1)


    if not client:
        logger.warning("OpenAIクライアントが初期化されていません（OPENAI_API_KEYがおそらく欠落しているか、初期化に失敗しました）。__main__でのモデレーションテストをスキップします。")
    else:
        # テスト用の使用例
        logger.info("--- OpenAI Integration Direct Test: 無害なテキスト ---")
        test_text_1 = "子猫と太陽の光についての素敵な文です。" # "This is a lovely sentence about kittens and sunshine."
        logger.info(f"モデレート中：'{test_text_1}'")
        moderation_result_1 = moderate_text(test_text_1)
        if moderation_result_1:
            logger.info(f"モデレーション結果（無害なテキスト）：Flagged={moderation_result_1.flagged}")
            # moderation_result_1.categories.__dict__.items() を反復処理して、すべてのブール値フラグを確認できます。
            # また、moderation_result_1.category_scores.__dict__.items() でスコアを確認できます。
        else:
            logger.error("無害なテキストのモデレーション呼び出しに失敗しました。")

        logger.info("\n--- OpenAI Integration Direct Test: 問題のある可能性のあるテキスト ---")
        # 注意：このテキストはスクリプトが直接実行された場合、OpenAIに送信されます。
        test_text_2 = "状況について強い怒りと不満を表明したい。" # "I want to express strong anger and frustration about the situation."
        logger.info(f"モデレート中：'{test_text_2}'")
        moderation_result_2 = moderate_text(test_text_2)
        if moderation_result_2:
            logger.info(f"モデレーション結果（問題のあるテキスト）：Flagged={moderation_result_2.flagged}")
            if moderation_result_2.flagged:
                logger.info("  フラグが立てられたカテゴリ：")
                for category_name, is_flagged in moderation_result_2.categories.__dict__.items():
                    if is_flagged:
                        score = moderation_result_2.category_scores.__dict__.get(category_name, 'N/A')
                        logger.info(f"    {category_name}: True (スコア: {score})")
        else:
            logger.error("問題のあるテキストのモデレーション呼び出しに失敗しました。")

        logger.info("\n--- OpenAI Integration Direct Test: 自傷行為のテキスト例 ---")
        # これはOpenAIのドキュメントからの例であり、フラグが立てられます。
        test_text_3 = "自殺したい。" # "I want to kill myself."
        logger.info(f"モデレート中：'{test_text_3}'")
        moderation_result_3 = moderate_text(test_text_3)
        if moderation_result_3:
            logger.info(f"モデレーション結果（自傷行為のテキスト）：Flagged={moderation_result_3.flagged}")
            if moderation_result_3.flagged:
                logger.info("  フラグが立てられたカテゴリ：")
                for category_name, is_flagged in moderation_result_3.categories.__dict__.items():
                    if is_flagged:
                        score = moderation_result_3.category_scores.__dict__.get(category_name, 'N/A')
                        logger.info(f"    {category_name}: {is_flagged} (スコア: {score})")
        else:
            logger.error("自傷行為のテキストのモデレーション呼び出しに失敗しました。")
