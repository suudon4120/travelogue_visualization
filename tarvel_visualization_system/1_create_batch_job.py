import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# --- 設定 ---
# .envファイルからAPIキーを読み込み、クライアントを初期化
load_dotenv()
client = OpenAI()

# 入力・出力ファイルの設定
INPUT_TXT = 'test5.txt'  # 分析したい旅行記番号のリスト
BATCH_INPUT_FILE = 'batch_input.jsonl' # OpenAIにアップロードするリクエストファイル
DIRECTORY = "../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules/"
MODEL_TO_USE = "gpt-4o"
MOVE_TAGS = ["徒歩", "車椅子", "自転車(電動)", "自転車(非電動)", "バイク", "バス", "タクシー", "自動車(運転)", "自動車(同乗)"]
ACTION_TAGS = ["食事(飲酒あり)", "食事(飲酒なし・不明)", "軽食(カフェなど)", "買い物(日用品)", "買い物(お土産)", "ジョギング", "ウォーキング", "ハイキング", "散歩", "スポーツ", "レジャー", "ドライブ", "景色鑑賞", "名所観光", "休養・くつろぎ", "仕事", "介護・看護", "育児", "通院・療養"]

def create_combined_prompt(travelogue_text):
    """1つの旅行記から全ての情報を抽出するための統合プロンプトを作成する"""
    return f"""
    以下の旅行記のテキストを時系列に沿って分析し、「滞在（stop）」と「移動（move）」のイベントを抽出し、さらに各滞在イベントの詳細な分析を同時に行ってください。

    **タスク:**
    1.  **イベント抽出**: テキストから「滞在(stop)」と「移動(move)」のイベントを時系列で抽出する。
        - `stop`の場合: `place`, `experience`を抽出。
        - `move`の場合: `means`（移動手段）, `experience`を抽出。
    2.  **詳細分析**: 各`stop`イベントの`experience`に対し、以下の分析を行う。
        - `per_tag_emotions`: 関連する「行動タグ」をすべて特定し、タグごとに感情スコア（-1.0～1.0）を算出する。
        - `latitude`, `longitude`: 旅行記全体の文脈を考慮した座標を推定する。
        - `reasoning`, `location_context`: 座標推定の理由と、ジオコーディング用の地名コンテキストを抽出する。

    **出力形式:**
    - 必ず、イベントのリストを含む単一のJSONオブジェクトとしてください。キーは "events" とします。
    - 各`stop`イベントオブジェクトには、`type`, `place`, `experience`, `latitude`, `longitude`, `reasoning`, `location_context`, `per_tag_emotions` を含めてください。
    - 各`move`イベントオブジェクトには、`type`, `means`, `experience` を含めてください。

    ---
    「移動手段」リスト: {MOVE_TAGS}
    「行動」タグリスト: {ACTION_TAGS}
    ---
    旅行記テキスト:
    {travelogue_text}
    """

def main():
    """メイン処理：バッチファイルの作成とアップロード"""
    print("ステップ1: バッチ入力ファイルの作成を開始します。")
    try:
        with open(INPUT_TXT, 'r', encoding='utf-8') as f:
            content = f.read()
        file_nums = [num.strip() for num in content.strip().split(',') if num.strip()]
    except Exception as e:
        print(f"[ERROR] {INPUT_TXT}の読み込みに失敗しました: {e}")
        return

    requests_to_batch = []
    for file_num in file_nums:
        path_tra = os.path.join(DIRECTORY, f"{file_num}.tra.json")
        if not os.path.exists(path_tra):
            print(f"[WARNING] .tra.jsonが見つかりません: {file_num}")
            continue

        with open(path_tra, "r", encoding="utf-8") as f:
            travelogue_data = json.load(f)
        full_text = " ".join(sum([e['text'] for e in travelogue_data if e.get('text')], []))
        if not full_text.strip():
            print(f"[WARNING] テキストデータがありません: {file_num}")
            continue

        prompt = create_combined_prompt(full_text)
        
        requests_to_batch.append({
            "custom_id": file_num, # 結果と突き合わせるためのID
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": MODEL_TO_USE,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
        })

    # JSONLファイルとして書き出し
    with open(BATCH_INPUT_FILE, 'w', encoding='utf-8') as f:
        for req in requests_to_batch:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")
    print(f"✅ {len(requests_to_batch)}件のリクエストを '{BATCH_INPUT_FILE}' に書き出しました。")

    # ファイルをOpenAIにアップロード
    print("\nステップ2: ファイルをOpenAIにアップロードします...")
    try:
        batch_file = client.files.create(
            file=open(BATCH_INPUT_FILE, "rb"),
            purpose="batch"
        )
        print(f"✅ ファイルをアップロードしました。File ID: {batch_file.id}")

        # バッチジョブを作成
        print("\nステップ3: バッチジョブを作成します...")
        batch_job = client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        print("\n🎉 バッチジョブが正常に作成されました！")
        print("以下のIDを次のプログラムで使用します。処理完了まで数分～数時間かかる場合があります。")
        print(f"Batch Job ID: {batch_job.id}")

    except Exception as e:
        print(f"[FATAL ERROR] OpenAI APIとの通信中にエラーが発生しました: {e}")

if __name__ == '__main__':
    main()