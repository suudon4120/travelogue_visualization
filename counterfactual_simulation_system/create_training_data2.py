import json
import os

def generate_triplets_from_travelogue(travelogue_filepath):
    """
    旅行記ファイル(.tra.json)のみを使い、section単位で三つ組を生成する。
    """
    if not os.path.exists(travelogue_filepath):
        return []

    with open(travelogue_filepath, 'r', encoding='utf-8') as f:
        travelogue_data = sorted(json.load(f), key=lambda x: x['section']) # section番号でソート

    if len(travelogue_data) < 3:
        return []

    # 各セクションのテキストを結合しておく
    section_texts = ["。".join(item['text']) for item in travelogue_data]

    training_samples = []
    # 各セクションをMiddleとして三つ組を生成
    for i in range(1, len(section_texts) - 1):
        prefix_text = "。".join(section_texts[:i]) + "。"
        middle_text = section_texts[i] + "。"
        suffix_text = "。".join(section_texts[i+1:]) + "。"
        
        input_text = f"文頭: {prefix_text} 文末: {suffix_text}"
        target_text = middle_text
        
        training_samples.append({
            "input_text": input_text,
            "target_text": target_text
        })

    return training_samples

if __name__ == '__main__':
    travelogue_file = '../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules/00018.tra.json'
    
    training_data = generate_triplets_from_travelogue(travelogue_file)

    if training_data:
        print(f"生成された学習サンプル数: {len(training_data)}")
        print("\n--- 生成されたデータセットの最初のサンプル ---")
        print(json.dumps(training_data[0], indent=2, ensure_ascii=False))