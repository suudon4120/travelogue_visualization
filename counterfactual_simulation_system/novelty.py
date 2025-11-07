import sys
from janome.tokenizer import Tokenizer
from rouge_score import rouge_scorer

# --- 1. 必要なライブラリのインストール (初回のみ) ---
# ターミナルで以下のコマンドを実行してください
# pip install rouge-score janome

# --- 2. サンプルデータの定義 ---

# 【中間(生成テキスト)】
generated_text = """
竹林を抜けたあとは、そのまま野宮神社へ立ち寄りました。境内に入ると、苔むした黒木の鳥居がひっそりと佇んでいて、周囲は竹林のざわめきしか聞こえません。小さな社ですが、縁結びや学業成就のご利益があると聞き、苔の上に手を合わせてみました。ちょうど和装の前撮りをしているカップルがいて、朱色の衣装と竹の緑のコントラストがとても絵になっていました。
そのあと、神社近くの茶店で「よもぎ団子（3本入りで400円）」をいただきました。焼き立ての団子からは香ばしい香りが立ちのぼり、口に入れるとほのかな苦みと甘いみたらしのタレが絶妙で、思わずもう一本追加しそうになったほど。値段も観光地にしては良心的で、大満足でした。
"""

# 【教師データ(元の中間テキスト)】
reference_text = """
昼前に仁和寺に到着。。こちらは桜が有名なお寺ということで、３日目のメインスポットだったのですが、。残念ながら名物の御室桜は半分以上散っていて、葉桜になっていました･･･。３日目ではなく１日目に来ていたら、もう少し咲いていたｶﾅ～。
"""

# --- 3. 日本語の前処理（形態素解析） ---

# 形態素解析器を初期化 (初回は辞書読み込みに少し時間がかかります)
try:
    t = Tokenizer()
except Exception as e:
    print(f"エラー: Janomeの初期化に失敗しました。{e}", file=sys.stderr)
    print("ヒント: 'pip install janome' を実行しましたか？", file=sys.stderr)
    sys.exit(1)

def tokenize_japanese(text):
    """
    日本語テキストを形態素解析し、スペース区切りの文字列に変換する。
    ROUGEライブラリはスペースで単語を区切るため。
    """
    # テキストを正規化（改行や余分なスペースを削除）
    text = text.strip().replace('\n', ' ')
    # 形態素解析（Janome）
    tokens = [token.surface for token in t.tokenize(text)]
    return " ".join(tokens)

# テキストを前処理
generated_tokenized = tokenize_japanese(generated_text)
reference_tokenized = tokenize_japanese(reference_text)

print("--- 形態素解析後のテキスト（ROUGE計算用） ---")
print(f"【生成】: {generated_tokenized[:100]}...") # 長すぎるので冒頭のみ表示
print(f"【教師】: {reference_tokenized[:100]}...\n")

# --- 4. ROUGEスコアの計算 ---

# ROUGE-1 (Unigram), ROUGE-2 (Bigram), ROUGE-L (Longest Common Subsequence) を計算
rouge_types = ['rouge1', 'rouge2', 'rougeL']

# スコア計算機を初期化
# use_stemmer=False: 英語のステミング（run, running -> run）を行わない
scorer = rouge_scorer.RougeScorer(rouge_types, use_stemmer=False)

# スコアを計算
# scorer.score(target, prediction)
# target = 教師データ (reference_text)
# prediction = 生成テキスト (generated_text)
scores = scorer.score(reference_tokenized, generated_tokenized)

# --- 5. 結果の表示 ---
print("--- ROUGEスコア (教師データからの逸脱度) ---")
print("✅ 注意: このタスクではスコアが【低い】ほど「逸脱度(Novelty)が高い」ことを意味します。\n")

for rouge_type, score in scores.items():
    print(f"■ {rouge_type.upper()}")
    print(f"  Precision (適合率): {score.precision:.4f}")
    print(f"  Recall (再現率):    {score.recall:.4f}")
    print(f"  F-measure (F値):  {score.fmeasure:.4f}")