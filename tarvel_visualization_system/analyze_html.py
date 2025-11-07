import re
from bs4 import BeautifulSoup

def analyze_emotion_map(html_content):
    """
    FoliumマップのHTMLコンテンツを解析し、ネガティブな体験の割合と
    該当エリアを報告します。

    Args:
        html_content (str): HTMLファイルの中身（文字列）。

    Returns:
        dict: 解析結果
    """
    
    # スクリプトタグからポップアップHTMLを抽出
    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script')
    
    popup_html_snippets = []
    for script in scripts:
        if script.string:
            # JavaScriptのバッククォート(`)で囲まれたHTMLコンテンツを正規表現で抽出
            # (var html_... = $(`...`) の形式を想定)
            matches = re.findall(r"var html_.*? = \$\(`(.*?)`\)", script.string, re.DOTALL)
            popup_html_snippets.extend(matches)

    if not popup_html_snippets:
        return {"error": "ポップアップ情報が見つかりませんでした。"}

    total_experiences = 0
    negative_experiences = 0
    negative_locations = []

    # 各ポップアップHTMLスニペットを解析
    for snippet in popup_html_snippets:
        # スニペットが空でないことを確認
        if not snippet.strip():
            continue
            
        popup_soup = BeautifulSoup(snippet, 'html.parser')
        
        # 場所名の取得 (最初の <b> タグ)
        place_name_tag = popup_soup.find('b')
        if not place_name_tag:
            continue
        
        # 場所名から (旅行記: ...) の部分を削除
        place_name = place_name_tag.get_text().split('(')[0].strip()
        
        # 感情スコアのタグ (span) を取得
        # 特有のスタイル属性で識別
        score_spans = popup_soup.find_all('span', style=lambda s: s and 'background-color:#E0E0E0' in s)
        
        if not score_spans:
            continue

        is_location_negative = False
        
        for span in score_spans:
            total_experiences += 1
            span_text = span.get_text()
            
            # スコアを正規表現で抽出 (例: "(1.00)" や "(-0.50)")
            score_match = re.search(r"\(([-+]?\d*\.?\d+)\)", span_text)
            
            if score_match:
                try:
                    score = float(score_match.group(1))
                    # ユーザーの要求通り、スコアが0以下の場合をネガティブと判定
                    if score < 0:
                        negative_experiences += 1
                        is_location_negative = True
                except ValueError:
                    continue
        
        if is_location_negative:
            negative_locations.append(place_name)

    # 結果の集計
    if total_experiences == 0:
        negative_ratio = 0.0
    else:
        negative_ratio = (negative_experiences / total_experiences) * 100

    return {
        "total_experiences": total_experiences,
        "negative_experiences": negative_experiences,
        "negative_ratio_percent": negative_ratio,
        "negative_locations": list(set(negative_locations)) # 重複を排除
    }

# --- 実行部分 ---
if __name__ == "__main__":
    # ここに解析したいHTMLファイルパスを指定してください
    # 添付されたファイル名に基づいて設定しています
    file_path = "visited_places_map_emotion_batch_20250729_184324.html"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        results = analyze_emotion_map(html_content)
        
        if "error" in results:
            print(f"エラー: {results['error']}")
        else:
            print(f"--- 感情スコア解析結果 ({file_path}) ---")
            print(f"■ 全体験タグ数: {results['total_experiences']}")
            print(f"■ ネガティブな体験タグ数 (スコア <= 0): {results['negative_experiences']}")
            print(f"■ ネガティブな体験の割合: {results['negative_ratio_percent']:.2f}%")
            
            if results['negative_experiences'] > 0:
                print("\n■ ネガティブな体験が報告されたエリア:")
                for location in results['negative_locations']:
                    print(f"  - {location}")
            else:
                print("\n■ このマップにはネガティブな体験は含まれていませんでした。")

    except FileNotFoundError:
        print(f"エラー: ファイル '{file_path}' が見つかりませんでした。")
    except Exception as e:
        print(f"解析中にエラーが発生しました: {e}")