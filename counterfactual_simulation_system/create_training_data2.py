import json
import os
from glob import glob
from tqdm import tqdm

def generate_triplets_from_travelogue(travelogue_filepath):
    """
    旅行記ファイル(.tra.json)のみを使い、section単位で三つ組を生成する。
    """
    if not os.path.exists(travelogue_filepath):
        return []

    with open(travelogue_filepath, 'r', encoding='utf-8') as f:
        # ファイルが空、または不正な形式の場合のエラーハンドリングを追加
        try:
            travelogue_data = sorted(json.load(f), key=lambda x: x['section'])
        except json.JSONDecodeError:
            print(f"警告: {travelogue_filepath} は不正なJSON形式です。スキップします。")
            return []

    if len(travelogue_data) < 3:
        return []

    section_texts = ["。".join(item['text']) for item in travelogue_data]

    training_samples = []
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
    # --- 設定項目 ---
    # 3000件の旅行記データ(.tra.json)が保存されているフォルダのパスを指定してください
    DATA_DIRECTORY = "../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules" 
    # 完成したデータセットを保存するファイル名
    OUTPUT_FILE = "training_dataset_all.jsonl"

    # --- 処理の実行 ---
    # 指定されたフォルダ内の全.tra.jsonファイルのリストを取得
    all_files = glob(os.path.join(DATA_DIRECTORY, "*.tra.json"))
    
    print(f"合計 {len(all_files)} 件のファイルを処理します...")

    # .jsonl形式でファイルに書き出す準備
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        total_samples = 0
        # tqdmを使って進捗バーを表示
        for filepath in tqdm(all_files, desc="Processing files"):
            # 各ファイルから三つ組データを生成
            triplets = generate_triplets_from_travelogue(filepath)
            
            # 生成された各サンプルをファイルに1行ずつ書き込む
            for sample in triplets:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
                total_samples += 1

    print("\n--- 処理完了 ---")
    print(f"合計 {total_samples} 件の学習データを '{OUTPUT_FILE}' に保存しました。")