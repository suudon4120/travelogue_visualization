import openai
import os
from dotenv import load_dotenv
import json
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from collections import defaultdict
import time
import requests
import urllib.parse
from datetime import datetime

# .envファイルから環境変数を読み込む
load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    raise ValueError("OpenAIのAPIキーが設定されていません。.envファイルを確認してください。")
openai.api_key = API_KEY

# ========== 設定 ==========
directory = "../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules/"
base_name = "visited_places_map_emotion_"
extension = ".html"
COLORS = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'lightgray']
WAIT_TIME = 1
MODEL = "gpt-4o"
prefix = '```json'
suffix = '```'
# ==========================

### ★★★ 機能追加: タグリストの定義 ★★★
MOVE_TAGS = [
    "徒歩", "車椅子", "自転車(電動)", "自転車(非電動)", "バイク", "バス", "タクシー", 
    "自動車(運転)", "自動車(同乗)"
]
ACTION_TAGS = [
    "食事(飲酒あり)", "食事(飲酒なし・不明)", "軽食(カフェなど)", "買い物(日用品)", 
    "買い物(お土産)", "娯楽(ジョギング)", "娯楽(ウォーキング)", "娯楽(ハイキング)", 
    "娯楽(散歩)", "娯楽(スポーツ)", "娯楽(レジャー)", "娯楽(ドライブ)", 
    "娯楽(景色鑑賞)", "娯楽(名所観光)", "娯楽(休養・くつろぎ)", "その他(仕事)", 
    "その他(介護・看護)", "その他(育児)", "その他(通院・療養)"
]
# =======================================

geolocator = Nominatim(user_agent="travel-map-final")

# --- 座標取得・テキスト抽出・感情分析の各関数 ---
def geocode_gsi(name):
    """【最終手段】国土地理院APIを使って地名の緯度経度を取得する"""
    try:
        query = urllib.parse.quote(name)
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={query}"
        print(f"🗺️ Geocoding (GSI): '{name}'...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            coords = data[0]['geometry']['coordinates']
            lon, lat = coords[0], coords[1]
            return lat, lon
    except: return None

def geocode_place(name, region_hint):
    """【最優先】Geopyを使って地名の緯度経度を取得する"""
    try:
        query = f"{name}, {region_hint}"
        print(f"🗺️ Geocoding (Geopy): '{query}'...")
        location = geolocator.geocode(query, timeout=10)
        time.sleep(WAIT_TIME)
        if location:
            return location.latitude, location.longitude
    except: return None

def extract_places(texts, region_hint):
    """GPTを使って旅行記から地名と体験、フォールバック用の座標を抽出する"""
    print("📌 訪問地抽出のプロンプトを[出力例付き]の完全なバージョンで実行します...")
    prompt = f"""
    以下の旅行記のテキストから、訪れた場所の情報を抽出してください。
    出力には "place"（地名）、"latitude"（緯度）、"longitude"（経度）、"experience"（その場所での経験）、"reasoning"（その座標だと推定した理由）を必ず含めてください。
    緯度経度は、日本の「{region_hint}」周辺の地理情報と、テキスト内の文脈（例：「〇〇駅から徒歩5分」「△△の隣」など）を最大限考慮して、非常に高い精度で推定してください。
    出力は**絶対にJSON形式のリスト**として返してください。
    例:
    [
        {{"place": "草津温泉バスターミナル", "latitude": 36.6222, "longitude": 138.5964, "experience": "草津温泉バスターミナルに到着しました。", "reasoning": "テキストに「草津温泉バスターミナルに到着」と明記されており、その名称でジオコーディングした結果です。"}},
        {{"place": "湯畑", "latitude": 36.6214, "longitude": 138.5968, "experience": "湯畑を散策しました。", "reasoning": "草津温泉の中心的な観光スポットであり、旅行記の文脈から草津温泉への訪問が明らかなため、湯畑の座標を指定しました。"}}
    ]
    テキスト: {texts}
    """
    response = openai.ChatCompletion.create(model=MODEL, messages=[{"role": "system", "content": f"あなたは旅行記から訪問地を正確に抽出する優秀な旅行ガイドです。日本の「{region_hint}」に関する地理に詳しいです。"}, {"role": "user", "content": prompt}], temperature=0.5)
    textforarukikata = response.choices[0].message.content.strip()
    if prefix in textforarukikata: textforarukikata = textforarukikata.split(prefix, 1)[1]
    if suffix in textforarukikata: textforarukikata = textforarukikata.rsplit(suffix, 1)[0]
    try:
        result = json.loads(textforarukikata.strip())
        if isinstance(result, list) and all(isinstance(item, dict) for item in result):
            for item in result:
                item['latitude'] = float(item.get('latitude', 0.0))
                item['longitude'] = float(item.get('longitude', 0.0))
            return result
        else: return []
    except: return []

def get_visit_hint(visited_places_text):
    if not visited_places_text.strip(): return "日本"
    messages = [{"role": "system", "content": "都道府県名を答えるときは，県名のみを答えてください．"}, {"role": "user", "content": f"以下の旅行記データから筆者が訪れたと考えられる都道府県を1つだけ答えてください．\n\n{visited_places_text}"}]
    try:
        response = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages, temperature=0.2)
        return response.choices[0].message.content.strip()
    except: return "日本"

def analyze_emotion(text):
    if not text or not text.strip(): return 0.5
    print(f"🧠 Analyzing emotion for: '{text[:40]}...'")
    prompt = f'以下のテキストは、旅行中のある場所での経験を記述したものです。このテキストから感情を分析し、「ポジティブ」「ニュートラル」「ネガティブ」の3段階で評価してください。そして、その感情の度合いを0.0（非常にネガティブ）から1.0（非常にポジティブ）の間の数値（スコア）で表現してください。ニュートラルな感情は0.5とします。出力は必ず以下のJSON形式で返してください。\n{{"sentiment": "（ここに評価）", "score": （ここにスコア）}}\n\nテキスト：「{text}」'
    try:
        response = openai.ChatCompletion.create(model="gpt-4o", messages=[{"role": "system", "content": "あなたはテキストから感情を読み取り、0.0から1.0の数値で定量化する優秀な感情分析アシスタントです。"}, {"role": "user", "content": prompt}], temperature=0.1, response_format={"type": "json_object"})
        result = json.loads(response.choices[0].message.content)
        return float(result.get("score", 0.5))
    except: return 0.5

### ★★★ 機能追加: タグ抽出関数 ★★★
def extract_tags(text, tag_list, tag_category):
    """GPTを使ってテキストから指定されたリストのタグを抽出する"""
    if not text or not text.strip():
        return []

    print(f"🏷️ Extracting '{tag_category}' tags for: '{text[:40]}...'")
    prompt = f"""
    以下のテキストは、旅行中のある場所での経験を記述したものです。
    提示された「{tag_category}」のタグリストの中から、このテキスト内容に最も関連性の高いタグをすべて選択してください。
    関連性の高いタグが一つもなければ、空のリストを返してください。

    出力は必ずJSON形式のタグ名のリストとして返してください。
    例: ["バス", "徒歩"]

    「{tag_category}」タグリスト:
    {tag_list}

    テキスト:
    「{text}」
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"あなたはテキストの内容を分析し、与えられたリストから関連する「{tag_category}」タグを正確に抽出する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        # GPTの応答が {"tags": ["..."]} のようになることを想定
        result = json.loads(response.choices[0].message.content)
        # "tags"キーや他の可能性のあるキーを探す
        tags = []
        for key in result:
            if isinstance(result[key], list):
                tags = result[key]
                break
        return tags
    except Exception as e:
        print(f"[ERROR] タグ抽出中にエラーが発生しました: {e}")
        return []

### ★★★ 機能追加: ポップアップにタグ表示機能を追加 ★★★
def map_emotion_and_routes(travels_data, output_html):
    """感情ヒートマップと訪問経路をレイヤー切り替え可能な地図として生成する"""
    if not travels_data: print("[ERROR] 地図に描画するデータがありません。"); return
    try:
        first_travel = travels_data[0]['places'][0]
        start_coords = (first_travel['latitude'], first_travel['longitude'])
        m = folium.Map(location=start_coords, zoom_start=10)
    except (IndexError, KeyError):
        m = folium.Map(location=[35.6812, 139.7671], zoom_start=10)
    
    heatmap_data = []
    for travel in travels_data:
        file_num, places, color = travel["file_num"], travel["places"], travel["color"]
        route_group = folium.FeatureGroup(name=f"旅行記ルート: {file_num}", show=True)
        locations = []
        for place_data in places:
            coords = (place_data['latitude'], place_data['longitude'])
            popup_html = f"<b>{place_data['place']}</b> (旅行記: {file_num})<br>"
            
            # 感情スコア表示
            popup_html += f"<b>感情スコア: {place_data.get('emotion_score', 0.5):.2f}</b><br>"
            
            # タグ表示
            tags = place_data.get('tags', [])
            if tags:
                popup_html += f"<hr style='margin: 3px 0;'>"
                popup_html += "<b>タグ:</b><br>"
                tag_html = ""
                for tag in tags:
                    tag_style = "display:inline-block; background-color:#E0E0E0; color:#333; padding:2px 6px; margin:2px; border-radius:4px; font-size:12px;"
                    tag_html += f"<span style='{tag_style}'>{tag}</span>"
                popup_html += tag_html
            
            # 推定理由表示
            if 'reasoning' in place_data and place_data['reasoning']:
                popup_html += f"<hr style='margin: 3px 0;'>"
                popup_html += f"<b>推定理由:</b><br>{place_data['reasoning']}<br>"
            
            # 体験表示
            popup_html += f"<hr style='margin: 3px 0;'>"
            popup_html += f"<b>体験:</b><br>{place_data['experience']}"

            folium.Marker(
                location=coords, popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"{place_data['place']} ({file_num})", icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(route_group)
            
            locations.append(coords)
            heatmap_data.append([coords[0], coords[1], place_data.get('emotion_score', 0.5)])
        
        if len(locations) > 1:
            folium.PolyLine(locations, color=color, weight=5, opacity=0.7).add_to(route_group)
        route_group.add_to(m)

    if heatmap_data:
        heatmap_layer = folium.FeatureGroup(name="感情ヒートマップ", show=False)
        HeatMap(heatmap_data).add_to(heatmap_layer)
        heatmap_layer.add_to(m)
    folium.LayerControl().add_to(m)
    m.save(output_html)
    print(f"\n🌐 感情・タグ分析付きの地図を {output_html} に保存しました。")

### ★★★ 機能追加: メイン処理にタグ抽出を追加 ★★★
def main():
    """メイン処理"""
    input_file_path = input('ファイル番号が記載された.txtファイルのパスを入力してください: ')
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_nums_raw = content.strip().split(',')
        file_nums = [num.strip() for num in file_nums_raw if num.strip()] 
        if not file_nums: print("[ERROR] 入力ファイルに有効なファイル番号が含まれていません。"); return
        print(f"INFO: ファイルから {len(file_nums)} 件のファイル番号を読み込みました。")
    except FileNotFoundError: print(f"[ERROR] 入力ファイルが見つかりません: {input_file_path}"); return
    except Exception as e: print(f"[ERROR] ファイルの読み込み中にエラーが発生しました: {e}"); return

    all_travels_data = []
    for i, file_num in enumerate(file_nums):
        path_journal = f'{directory}{file_num}.tra.json'
        print(f"\n{'='*20} [{file_num}] の処理を開始 {'='*20}")
        if not os.path.exists(path_journal): print(f"[WARNING] ファイルが見つかりません: {path_journal}"); continue
        try:
            with open(path_journal, "r", encoding="utf-8") as f: travel_data = json.load(f)
        except: print(f"[ERROR] JSON読み込み失敗"); continue
        texts = [];
        for entry in travel_data: texts.extend(entry['text'])
        full_text = " ".join(texts)
        if not full_text.strip(): print(f"[WARNING] 旅行記 {file_num} にはテキストデータがありません。"); continue
        
        region_hint = get_visit_hint(full_text)
        extracted_places = extract_places(full_text, region_hint)
        if not extracted_places: print(f"[WARNING] 旅行記 {file_num} から訪問地を抽出できませんでした。"); continue

        places_with_coords = []
        for place_data in extracted_places:
            place_name = place_data['place']
            coords = geocode_place(place_name, region_hint)
            if not coords:
                coords = (place_data['latitude'], place_data['longitude'])
                if coords[0] == 0.0 and coords[1] == 0.0: coords = None
            if not coords:
                coords = geocode_gsi(place_name)
            if coords:
                place_data['latitude'] = coords[0]
                place_data['longitude'] = coords[1]
                places_with_coords.append(place_data)
            else:
                print(f"[!] 全てのジオコーディングに失敗しました: {place_name}")

        # 場所ごとにまとめたexperienceから感情とタグを抽出
        grouped_experiences = defaultdict(list)
        for p in places_with_coords: grouped_experiences[p['place']].append(p['experience'])
        
        place_analysis_results = {}
        for place, experiences in grouped_experiences.items():
            combined_experience = " ".join(experiences)
            # 感情分析
            score = analyze_emotion(combined_experience)
            # タグ抽出
            move_tags = extract_tags(combined_experience, MOVE_TAGS, "移動手段")
            action_tags = extract_tags(combined_experience, ACTION_TAGS, "行動")
            all_tags = move_tags + action_tags
            
            place_analysis_results[place] = {"score": score, "tags": all_tags}

        # 感情スコアとタグを元のデータに付与
        for p in places_with_coords:
            analysis = place_analysis_results.get(p['place'], {"score": 0.5, "tags": []})
            p['emotion_score'] = analysis['score']
            p['tags'] = analysis['tags']
        
        print(f"📌 処理完了 ({file_num}): {len(places_with_coords)}件の訪問地を地図に追加します。")
        all_travels_data.append({
            "file_num": file_num, "places": places_with_coords,
            "color": COLORS[i % len(COLORS)], "region_hint": region_hint 
        })

    if all_travels_data:
        if len(file_nums) >= 4:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{base_name}{timestamp}{extension}"
        else:
            output_filename = f"{base_name}{'_'.join(file_nums)}{extension}"
        map_emotion_and_routes(all_travels_data, output_filename)
    else:
        print("\n地図を生成するためのデータがありませんでした。")

if __name__ == '__main__':
    main()