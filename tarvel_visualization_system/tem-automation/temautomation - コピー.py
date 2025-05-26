# -*- coding: utf-8 -*-
import time
start = time.time() 
from tqdm import tqdm
print("起動中...")
import openai
openai.api_key="PUT YOUR API KEY HERE"
import os
import datetime

# 保存先ディレクトリとファイルの基本名
directory = "./"
base_name = "GeneratedTextforTEM"
extension = ".xml"

# 連番でファイル名を作成
# currentversion = 1501
# while True:
#     filename = os.path.join(directory, f"{base_name}_{currentversion}{extension}")
#     if not os.path.exists(filename):  # ファイルが存在しない場合
#         break
#     currentversion += 1

#タイムスタンプからファイル名を作成
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"{base_name}_{timestamp}{extension}"

#書き込みを行うファイル(.xml)のパス
path_w = filename
#文字起こしのファイルのパス
path_transcription = './interviewdata.txt'
#TEM図のサンプル
path_example_diagram = './example_diagram2.xml'

prefix = '```xml'
suffix = '```'

def zenkaku_to_hankaku(text):
    # 全角数字のUnicodeコードポイント
    zenkaku = "０１２３４５６７８９"
    # 半角数字のUnicodeコードポイント
    hankaku = "0123456789"
    # 翻訳テーブルを作成
    translation_table = str.maketrans(zenkaku, hankaku)
    # 翻訳を適用
    return text.translate(translation_table)

#初期メッセージ
messages = [
    {"role": "system", "content": "あなたは心理学研究者の優秀なアシスタントで、インタビューデータに基づく年表の作成を任されています。"},
]

#最初の指示：切片化
messages.append({"role": "user", "content": "以下のインタビューデータからインタビュイーが経験した出来事を30個抽出し，箇条書きにして．"})
messages.append({"role": "user", "content": "インタビューデータの中で話されているインタビュイーの経験を5つの期間に分割して．例:高校以前・大学1年・大学2年・大学3年・大学4年・今後"})

#文字起こしデータを読み込み
with open(path_transcription, encoding='utf-8') as t:
    transcription = t.read()
#文字起こしデータを与える
messages.append({"role": "user", "content": transcription})

print("切片を生成中...(1/2)")
#APIにリクエストを送信
response = openai.chat.completions.create(
  model="gpt-4o",
  messages=messages,
  temperature=0
)

# def make_api_request(messages):
#     estimated_time = 180  #プログレスバーを表示するための目標時間（秒）
#     with tqdm(total=estimated_time, desc="Processing request", unit="s") as pbar:
#         start_time = time.time()
#         # 非同期処理の代わりに疑似プログレスバーを更新
#         while time.time() - start_time < estimated_time:
#             time.sleep(0.1)  # プログレス更新間隔
#             pbar.update(0.1)  # プログレスを0.1秒分進める
#         # 実際のAPIリクエスト
#         response = openai.chat.completions.create( model="gpt-4o", messages=messages, temperature=0 )
#         pbar.update(estimated_time - (time.time() - start_time))  # 最終調整
#     return response


#モデルの回答を取得
assistant_message = response.choices[0].message.content
#回答を履歴に追加
messages.append({"role": "assistant", "content": assistant_message})

#次の指示を追加：並び替え
messages.append({"role": "user", "content": "箇条書きにした30個の項目を実際に起きたと考えられる時系列順に並べ替えて．"})

print("切片を時系列順に並び替えています...(2/2)")
#APIに再びリクエストを送信
response = openai.chat.completions.create( model="gpt-4o", messages=messages, temperature=0 )
#モデルの回答を取得
assistant_message = response.choices[0].message.content
#回答を履歴に追加
messages.append({"role": "assistant", "content": assistant_message})

efp_list = []
end_flag = False
#EFPを自分で設定するかどうか決める
while True: 
  print("等至点(EFP)の設定を行いますか？y/n")
  efp_choice = input()
  if efp_choice == 'y':
    #ユーザに切片を提示
    print(assistant_message)
    while True:
      if end_flag:
         break
      input_data = input("生成した切片は以上の通りです．等至点 (EFP) を表す番号を1つ選んで入力してください: ")
      converted_input_data = zenkaku_to_hankaku(input_data)
      print(f"あなたが選んだ番号は: {converted_input_data}")
      efp_list.append(converted_input_data)
      # 次の入力を求める
      while True:
        continue_input = input("他に入力する数字はありますか？yかnを入力してください: ").lower()
        print(f"今までに選ばれた番号は{efp_list}です．")
        if continue_input == 'y':
            break  # 外側のループに戻って再度入力を求める
        elif continue_input == 'n':
            print("EFPの選択を終了します．")
            end_flag = True
            break
        else:
          print("yまたはnを入力してください．")  # 無効な入力の場合は再度尋ねる
      efp_message = f"並べ替えた項目のうち{efp_list}番目の項目に対し，EFPというタグを付けて．"
      pefp_message = f"EFPと逆の意味をもつ文章をEFPの個数分生成し，{efp_list}番目のそれぞれの項目の次に追加して．また，P-EFPというタグを付けて．"
    break
  elif efp_choice == 'n':
    efp_message = "並べ替えた項目のうちインタビュイーにとってのゴールと考えられるものに対し，EFPというタグを付けて．"
    pefp_message = "EFPと逆の意味をもつ文章を生成し，EFPのタグがついた項目の次に追加して．また，P-EFPというタグを付けて．"
    break
  else:
    print("無効な入力です．y または n を入力してください．")

print("図面ファイルを作成します．しばらくお待ち下さい．(この処理には時間がかかる場合があります)")
messages.append({"role": "system", "content": "タグ付けのルールとして，1つの項目には1つのタグしかつけることができず，既にタグ付けされている項目にあとからタグを上書きすることはできない．"})
#次の指示を追加：タグ付け
messages.append({"role": "user", "content": efp_message})
messages.append({"role": "user", "content": "並べ替えた項目のうち，EFPへ向かうように影響する文化的・社会的な力をすべて選び，SGというタグを付けて．ただし，インタビュイー自身の行動は含まれない．"})
messages.append({"role": "user", "content": "並べ替えた項目のうち，EFPへ向かうのを妨げるように影響する文化的・社会的な力をすべて選び，SDというタグを付けて．ただし，インタビュイー自身の行動は含まれない．"})
messages.append({"role": "user", "content": "並べ替えた項目のうち，インタビュイーの意思に関係なく選択された行動を選び，OPPというタグを付けて．これには，社会的慣習や天災が含まれる．"})
messages.append({"role": "user", "content": "並べ替えた項目のうち，インタビュイーが自ら選択した行動に対してBFPというタグを付けて．"})
messages.append({"role": "user", "content": "並べ替えた項目のうち，いかなるタグも付いていないものに対し，eventというタグを付けて．"})
messages.append({"role": "user", "content": pefp_message} )
messages.append({"role": "user", "content": "EFPとP-EFPを除くすべての項目について，EFPとの関連性の高さを評価し，-10(最も関連性が低い)から10(最も関連性が高い)までの値を付加して．これを類似度と呼ぶ．"})

print("切片を分類中...(1/3)")
#APIに再びリクエストを送信
response = openai.chat.completions.create( model="gpt-4o", messages=messages, temperature=0 )
#モデルの回答を取得
assistant_message = response.choices[0].message.content
#回答を履歴に追加
messages.append({"role": "assistant", "content": assistant_message})

messages.append({"role": "system", "content": "drawio形式(.xml)のテキストを回答する場合，コードのみを回答して．"})
messages.append({"role": "system", "content": "mxCell idの値は命名規則がある．2-1,2-2,...のように設定して．"})
messages.append({"role": "system", "content": "EFPのタグがついている項目とP-EFPのタグがついている項目のx座標は800離れている必要がある．"})
messages.append({"role": "system", "content": "EFPとP-EFPを直接矢印で結んではいけない．"})
messages.append({"role": "system", "content": "類似度の値はvalueに含めない．"})
#次の指示を追加：xml化
messages.append({"role": "user", "content": "並べ替えた全ての項目が縦に並ぶようにdrawio形式(.xml)で記述して．すべての項目について，mxGeometryのxの値を0にして．"})
messages.append({"role": "user", "content": "EFPのタグがついている場合はshapeをshape=ext;double=1;として．"})
messages.append({"role": "user", "content": "BFPのタグがついている場合はshapeをrounded=1として．"})
messages.append({"role": "user", "content": "SDのタグがついている場合はshapeをshape=singleArrow;direction=west;とし，mxGeometryのxの値を+250して．SGのタグがついている場合はshapeをshape=singleArrow;direction=east;とし，mxGeometryのxの値を-250して．また，これらについてarrowWidth=1として．"})
messages.append({"role": "user", "content": "P-EFPのタグがついている場合，yの値をEFPのタグがついている項目と等しくして"})
messages.append({"role": "user", "content": "SDおよびSG以外の項目が矢印で結ばれるように矢印を追加して．"})
messages.append({"role": "user", "content": "例を示します："})
with open(path_example_diagram, encoding='utf-8') as e:
    example_diagram = e.read()
messages.append({"role": "user", "content": example_diagram})

print("図形を配置中...(2/3)")
#APIに再びリクエストを送信
response = openai.chat.completions.create( model="gpt-4o", messages=messages, temperature=0 )

#次の指示を追加：レイアウト
messages.append({"role": "user", "content": "生成したxmlファイルについて，EFPのタグを含む部分についてmxGeometryのxの値を+250して．"})
messages.append({"role": "user", "content": "生成したxmlファイルについて，各項目のmxGeometryのxの値を類似度*25に設定して．"})
messages.append({"role": "user", "content": "生成したxmlファイルについて，すべてのBFP,EFPおよびeventが矢印で結ばれるように修正して．"})
messages.append({"role": "user", "content": "P-EFPのタグを含む部分に対し，直前のBFPまたはeventから繋がるように矢印を追加して．"})
messages.append({"role": "user", "content": "P-EFPのタグを含む項目のmxGeometryのxの値は-250して．"})

print("図形を調整中...(3/3)")
#APIに再びリクエストを送信
response = openai.chat.completions.create( model="gpt-4o", messages=messages, temperature=0 )

textfortem = response.choices[0].message.content
textfortem = textfortem.removeprefix(prefix)
textfortem = textfortem.removesuffix(suffix)
textfortem = textfortem.strip()
#print(textfortem)

#ファイルに書き込み
with open(path_w, mode='w', encoding='utf-8') as f:
  f.write(textfortem)

end = time.time()
time_diff = end - start  # 処理完了後の時刻から処理開始前の時刻を減算する
print(time_diff)

print("図面ファイルの生成が完了しました．")