import json
import random

def split_dataset(input_filepath, train_filepath, val_filepath, test_filepath, train_ratio=0.8, val_ratio=0.1):
    """
    .jsonlファイルを読み込み、ランダムにシャッフルして3つに分割し、
    それぞれ別の.jsonlファイルとして保存する関数。
    """
    # --- 1. 全てのデータをメモリに読み込む ---
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            all_data = f.readlines() # 1行ずつ読み込む
        print(f"入力ファイル '{input_filepath}' から {len(all_data)} 件のデータを読み込みました。")
    except FileNotFoundError:
        print(f"エラー: 入力ファイル '{input_filepath}' が見つかりません。")
        return

    # --- 2. データをランダムにシャッフル ---
    random.shuffle(all_data)
    print("データセットをシャッフルしました。")

    # --- 3. 分割点を計算 ---
    total_size = len(all_data)
    train_end_index = int(total_size * train_ratio)
    val_end_index = int(total_size * (train_ratio + val_ratio))

    # --- 4. データを3つのリストに分割 ---
    train_data = all_data[:train_end_index]
    val_data = all_data[train_end_index:val_end_index]
    test_data = all_data[val_end_index:]

    # --- 5. 各データセットをファイルに書き出す ---
    try:
        with open(train_filepath, 'w', encoding='utf-8') as f:
            f.writelines(train_data)
        print(f"訓練データ {len(train_data)} 件を '{train_filepath}' に保存しました。")

        with open(val_filepath, 'w', encoding='utf-8') as f:
            f.writelines(val_data)
        print(f"検証データ {len(val_data)} 件を '{val_filepath}' に保存しました。")

        with open(test_filepath, 'w', encoding='utf-8') as f:
            f.writelines(test_data)
        print(f"テストデータ {len(test_data)} 件を '{test_filepath}' に保存しました。")
    except IOError as e:
        print(f"エラー: ファイルの書き込みに失敗しました。 {e}")


if __name__ == '__main__':
    # --- 設定項目 ---
    INPUT_FILE = "training_dataset_all.jsonl"  # 作成した70,000件のデータセットファイル
    
    TRAIN_FILE = "train.jsonl"
    VALIDATION_FILE = "validation.jsonl"
    TEST_FILE = "test.jsonl"

    # --- 処理の実行 ---
    split_dataset(INPUT_FILE, TRAIN_FILE, VALIDATION_FILE, TEST_FILE)