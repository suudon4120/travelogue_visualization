import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def create_unified_timeline(schedule_data, travelogue_data, model):
    """セマンティック類似度に基づき、スケジュールと旅行記を統合する"""
    # 1. スケジュールデータを前処理し、イベントリストとテキストリストを作成
    schedule_events = []
    schedule_texts = []
    for day_key, day_schedule in schedule_data.items():
        i = 0
        while i < len(day_schedule):
            current_event = day_schedule[i]
            description = current_event["place"]
            j = i + 1
            while j < len(day_schedule) and day_schedule[j]["time"] == "xx:xx - xx:xx":
                description += "。" + day_schedule[j]["place"]
                j += 1
            
            if current_event["time"] != "xx:xx - xx:xx":
                schedule_events.append({
                    "time": current_event["time"],
                    "place": current_event["place"],
                    "full_text": description
                })
                schedule_texts.append(description)
            i = j
    
    # 2. 旅行記データのテキストリストを作成
    travelogue_texts = ["。".join(item['text']) for item in travelogue_data]

    if not travelogue_texts or not schedule_texts:
        return schedule_events

    # 3. 文章をベクトルに変換
    schedule_embeddings = model.encode(schedule_texts)
    travelogue_embeddings = model.encode(travelogue_texts)

    # 4. コサイン類似度を計算し、最も関連性の高いペアをマッピング
    similarity_matrix = cosine_similarity(travelogue_embeddings, schedule_embeddings)
    
    for i in range(len(travelogue_texts)):
        best_match_index = np.argmax(similarity_matrix[i])
        if similarity_matrix[i][best_match_index] > 0.4: # 類似度の閾値(0.4)
            schedule_events[best_match_index]["full_text"] += "。" + travelogue_texts[i]
            
    return schedule_events

def format_events_to_text(events, key_events_only=False):
    """
    イベントのリストを一つの文章にまとめる。
    key_events_only=Trueの場合、重要度の低いイベントを省略する。
    """
    if not events: return ""
    
    texts_to_join = []
    for event in events:
        is_simple_move = '移動' in event['place'] and len(event['full_text']) < 20 # 20文字未満の単純な移動か
        if key_events_only and is_simple_move:
            continue # 重要度が低いのでスキップ
        texts_to_join.append(event['full_text'])
        
    return "。".join(texts_to_join) + "。"

def generate_training_data(schedule_filepath, travelogue_filepath, model):
    """
    2つのファイルからモデル学習用のデータセットを生成するメイン関数
    """
    if not os.path.exists(schedule_filepath) or not os.path.exists(travelogue_filepath): return []
    with open(schedule_filepath, 'r', encoding='utf-8') as f: schedule_data = json.load(f)
    with open(travelogue_filepath, 'r', encoding='utf-8') as f: travelogue_data = json.load(f)
    unified_timeline = create_unified_timeline(schedule_data, travelogue_data, model)
    if len(unified_timeline) < 3: return []

    training_samples = []
    experience_keywords = ['温泉', '食事', '体験', '道場', '館', '神宮', '工房', 'ふぐ', 'そば', 'かまぼこ', '宿', 'ケーキ']

    # 1. まず「体験」のアンカーとなるイベントのインデックスを全て見つける
    anchor_indices = [i for i, event in enumerate(unified_timeline) 
                    if any(keyword in event['full_text'] for keyword in experience_keywords)]

    if not anchor_indices:
        print("警告: キーワードに合致する体験イベントが見つかりませんでした。")
        return []

    # 2. 各アンカーポイントを中心に三つ組を生成
    for i in range(len(anchor_indices)):
        start_anchor_index = anchor_indices[i]
        
        # Middleの終わりを次のアンカーの手前、または旅の終わりとする
        if i + 1 < len(anchor_indices):
            end_anchor_index = anchor_indices[i+1]
        else:
            end_anchor_index = len(unified_timeline)

        # 1. Prefixを直前の1〜2イベントに限定する (ここでは直前のイベントのみ)
        if start_anchor_index > 0:
            prefix_events = [unified_timeline[start_anchor_index - 1]]
        else:
            prefix_events = [] # 旅の始まりならPrefixは無し

        # 2. Middleを定義
        middle_events = unified_timeline[start_anchor_index:end_anchor_index]
        
        # 3. Suffixを直後の1〜2イベントに限定する
        if end_anchor_index < len(unified_timeline):
            suffix_events = [unified_timeline[end_anchor_index]]
        else:
            suffix_events = [] # 旅の終わりならSuffixは無し

        if prefix_events and suffix_events and middle_events:
            # 4. 各パートのテキストを生成 (フィルタリングは不要に)
            prefix_text = format_events_to_text(prefix_events)
            middle_text = format_events_to_text(middle_events)
            suffix_text = format_events_to_text(suffix_events)
            
            # 5. target_textの末尾から不要な「移動」を削除
            if middle_text.endswith("。移動（車）。"):
                middle_text = middle_text[:-6]

            input_text = f"文頭: {prefix_text} 文末: {suffix_text}"
            target_text = middle_text
            
            # target_textが空でなければサンプルを追加
            if target_text:
                training_samples.append({
                    "input_text": input_text,
                    "target_text": target_text
                })
            
    return training_samples

if __name__ == '__main__':
    schedule_file = '../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules/00018.sch.json'
    travelogue_file = '../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules/00018.tra.json'

    print("Loading sentence-transformer model... (初回は時間がかかります)")
    model = SentenceTransformer('stsb-xlm-r-multilingual')
    print("Model loaded.")

    training_data = generate_training_data(schedule_file, travelogue_file, model)

    if training_data:
        print(f"\n生成された学習サンプル数: {len(training_data)}")
        print("\n--- 生成されたデータセットの最初のサンプル ---")
        print(json.dumps(training_data[0], indent=2, ensure_ascii=False))
        
        # 結果をファイルに保存
        output_filename = 'training_dataset_00018.json'
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)
        print(f"\nデータセットを '{output_filename}' に保存しました。")