# -*- coding: utf-8 -*-
import time
start = time.time() 
from tqdm import tqdm
print("起動中...")
import openai
openai.api_key="PUT YOUR API KEY HERE"
import os
import datetime
import json

def zenkaku_to_hankaku(text):
    # 全角数字のUnicodeコードポイント
    zenkaku = "０１２３４５６７８９"
    # 半角数字のUnicodeコードポイント
    hankaku = "0123456789"
    # 翻訳テーブルを作成
    translation_table = str.maketrans(zenkaku, hankaku)
    # 翻訳を適用
    return text.translate(translation_table)

# 保存先ディレクトリとファイルの基本名
directory = "./"
base_name = "GeneratedTextforARUKIKATA"
extension = ".xml"
#旅行記のファイルのパス
file_num = input('分析を行うファイルの番号を入力：')
path_journal = f'{file_num}.sch.json'
#タイムスタンプからファイル名を作成
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"{base_name}{file_num}_{timestamp}{extension}"
#書き込みを行うファイル(.xml)のパス
path_w = filename
#図のサンプル
path_example_diagram = './example_diagram3.xml'
#プレフィックスとサフィックス
prefix = '```xml'
suffix = '```'
#旅行記ファイルを読み込み
json_open = open(path_journal, 'r')
json_load = json.load(json_open)

#初期メッセージ
messages = [
    {"role": "system", "content": "あなたは旅行雑誌編集者の優秀なアシスタントで、旅行記に基づくパンフレットの作成を任されています。"},
]

#最初の指示：descriptionへの統合
messages.append({"role": "user", "content": "以下のjsonファイルの内容について，timeの情報がない項目のplaceの値を周辺の値と比較して，特に関連性の高いもののdescriptionの値に挿入して．"})
#旅行記データを与える
messages.append({"role": "user", "content": "処理するデータは以下の通り．"})
messages.append({"role": "user", "content": json.dumps(json_load, ensure_ascii=False)})
#サンプルを与える
messages.append({"role": "user", "content": """以下にその例を示します． 元のデータ： {       "time": "10:50 11:00",       "place": "移動（車）",       "description": "_"     },     {       "time": "11:00 13:10",       "place": "ふぐ館　魚平",       "description": "_"     },     {       "time": "xx:xx xx:xx",       "place": "魚平では、新鮮で美味しいふぐが食べれます。（皿の上でまだ動いてました・・・）　値段もお手ごろで、「てっさ」、「てっちり」など、おなかいっぱい食べて、1人7,000円ぐらいでした。",       "description": "_"     },     {       "time": "13:10 13:20",       "place": "移動（車）",       "description": "_"     }  例(処理結果)： {       "time": "10:50 11:00",       "place": "移動（車）",       "description": "_"     },     {       "time": "11:00 13:10",       "place": "ふぐ館　魚平",       "description": "魚平では、新鮮で美味しいふぐが食べれます。（皿の上でまだ動いてました・・・）　値段もお手ごろで、「てっさ」、「てっちり」など、おなかいっぱい食べて、1人7,000円ぐらいでした。"     },     {       "time": "13:10 13:20",       "place": "移動（車）",       "description": "_"     }"""})

print("データを整形中...(1/2)")
#APIにリクエストを送信
response = openai.chat.completions.create(
  model="gpt-4o",
  messages=messages,
  temperature=0
)
#モデルの回答を取得
assistant_message = response.choices[0].message.content
#履歴をクリア
messages.clear()

messages.append({"role": "system", "content": "mxCell idの値は命名規則がある．2-1,2-2,...のように設定して．"})
#次の指示を追加：XMLへの変換
messages.append({"role": "user", "content": "以下のjsonファイルからtime, place, descriptionの情報を読み取って，横一列に並ぶようにdrawio形式(.xml)にして．"})
messages.append({"role": "assistant", "content": assistant_message})#回答を履歴に追加
messages.append({"role": "user", "content": """以下にdrawio形式の例を示す．移動に関する記述を行うときは，通常のボックスを生成せず，例にならってstyle="shape=singleArrow;whiteSpace=wrap;html=1;arrowWidth=0.55;arrowSize=0.2;を使用して．"""})
with open(path_example_diagram, encoding='utf-8') as e:
    example_diagram = e.read()
messages.append({"role": "user", "content": example_diagram})
messages.append({"role": "system", "content": "drawio形式(.xml)のテキストを回答する場合，コードのみを回答して．"})
messages.append({"role": "system", "content": "旅行記のファイルを処理する場合，すべてのイベントを含めて．"})



print("図面ファイルを作成中...(2/2)")
#APIに再びリクエストを送信
response = openai.chat.completions.create( model="gpt-4o", messages=messages, temperature=0 )
#モデルの回答を取得
assistant_message = response.choices[0].message.content
#回答を履歴に追加
messages.append({"role": "assistant", "content": assistant_message})

textforarukikata= response.choices[0].message.content
textforarukikata = textforarukikata.removeprefix(prefix)
textforarukikata = textforarukikata.removesuffix(suffix)
textforarukikata = textforarukikata.strip()

#ファイルに書き込み
with open(path_w, mode='w', encoding='utf-8') as f:
  f.write(textforarukikata)

end = time.time()
time_diff = end - start  # 処理完了後の時刻から処理開始前の時刻を減算する
print(time_diff)

print("図面ファイルの生成が完了しました．")