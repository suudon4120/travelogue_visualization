import json
import re
from itertools import groupby
import math

def get_original_text(data):
    """
    jsonオブジェクト（辞書）から元の完全な文章を復元します。
    'input_text'に含まれる「文頭」と「文末」、そして'target_text'を結合します。

    Args:
        data (dict): jsonlの1行をパースした辞書。

    Returns:
        str: 復元された元の文章。不明な場合は空文字を返す。
    """
    try:
        input_text = data.get('input_text', '')
        target_text = data.get('target_text', '')

        # 正規表現を使用して「文頭」と「文末」のテキストを抽出
        # re.DOTALLフラグにより、改行が含まれていてもマッチします
        match = re.match(r"文頭: (.*) 文末: (.*)", input_text, re.DOTALL)
        if match:
            head = match.group(1).strip()
            tail = match.group(2).strip()
            return head + target_text + tail
        else:
            # マッチしない場合は、単純な結合を試みるか、エラーとして扱う
            # ここでは、元の文章が特定できないものとして空文字を返す
            return ""
    except (AttributeError, TypeError):
        return ""

def process_jsonl(input_path, output_path):
    """
    jsonlファイルを処理し、各文章グループの中央部分のみを抽出して保存します。

    1. jsonlファイルを読み込みます。
    2. 元の文章が同じ連続した行をグループ化します。
    3. 各グループの行数のうち、前半と後半の約30%（四捨五入）を削除します。
    4. 残った行を新しいjsonlファイルに書き出します。

    Args:
        input_path (str): 入力するjsonlファイルのパス。
        output_path (str): 出力するjsonlファイルのパス。
    """
    try:
        # 入力ファイルを読み込み、各行を辞書オブジェクトとしてリストに格納
        with open(input_path, 'r', encoding='utf-8') as f:
            lines_data = [json.loads(line) for line in f]

        processed_lines = []
        # itertools.groupbyを使用して、元の文章が同じ連続した行をグループ化
        # keyに関数を指定することで、その関数の戻り値に基づいてグループ化が行われる
        for _, group_iterator in groupby(lines_data, key=get_original_text):
            group = list(group_iterator)
            n = len(group)

            # グループの行数が少ない場合は処理をスキップすることも可能
            # 例えば、3行以下の場合は何もしないなど
            if n == 0:
                continue
            
            # 削除する行数を計算 (全体の30%を四捨五入)
            # ユーザーの例（9行->3行削除）に合わせるためroundを使用
            remove_count = round(n * 0.3)

            # 配列のスライス機能を使って、前半と後半の指定行数を削除
            # 例: group[3:-3] -> 4番目から末尾の3つ前まで
            # remove_countが0の場合、スライスは元のリスト全体を返す
            trimmed_group = group[remove_count : n - remove_count]
            
            # 処理後のリストを全体のリストに追加
            processed_lines.extend(trimmed_group)

        # 処理後のデータを新しいjsonlファイルに書き込み
        with open(output_path, 'w', encoding='utf-8') as f:
            for line_data in processed_lines:
                # json.dumpsで辞書をJSON形式の文字列に変換
                # ensure_ascii=Falseで日本語がそのまま出力されるようにする
                json_string = json.dumps(line_data, ensure_ascii=False)
                f.write(json_string + '\n')

        print(f"処理が完了しました。結果は '{output_path}' に保存されました。")
        print(f"元の行数: {len(lines_data)}, 処理後の行数: {len(processed_lines)}")

    except FileNotFoundError:
        print(f"エラー: ファイル '{input_path}' が見つかりません。")
    except json.JSONDecodeError as e:
        print(f"エラー: ファイル '{input_path}' のJSON形式が正しくありません。エラー詳細: {e}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")


if __name__ == '__main__':
    # --- 設定 ---
    # 入力ファイルと出力ファイルのパスを指定してください
    INPUT_JSONL_FILE = 'training_dataset_all.jsonl'
    OUTPUT_JSONL_FILE = 'training_dataset_middle40percent.jsonl'
    
    # --- 実行 ---
    # 注意: このスクリプトを実行する前に、
    # 'INPUT_JSONL_FILE'と同じ場所に添付のデータ例を'input.jsonl'として保存してください。
    process_jsonl(INPUT_JSONL_FILE, OUTPUT_JSONL_FILE)

