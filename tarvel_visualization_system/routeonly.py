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
import base64
from branca.element import MacroElement
from jinja2 import Template

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
CACHE_DIR = "results_cache_0707" ### ★★★ 機能追加: キャッシュ用ディレクトリ ★★★
COLORS = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'lightgray']
WAIT_TIME = 1
MODEL = "gpt-4o"
prefix = '```json'
suffix = '```'

# --- タグリストの定義 ---
MOVE_TAGS = [
    "徒歩", "車椅子", "自転車(電動)", "自転車(非電動)", "バイク", "バス", "タクシー",
    "自動車(運転)", "自動車(同乗)"
]
ACTION_TAGS = [
    "食事(飲酒あり)", "食事(飲酒なし・不明)", "軽食(カフェなど)", "買い物(日用品)",
    "買い物(お土産)", "ジョギング", "ウォーキング", "ハイキング",
    "散歩", "スポーツ", "レジャー", "ドライブ",
    "景色鑑賞", "名所観光", "休養・くつろぎ", "仕事",
    "介護・看護", "育児", "通院・療養"
]

# --- アイコン画像関連の設定 ---
TAG_TO_IMAGE = {
    # 移動関連
    "徒歩": "images/icon_01_徒歩_stop.png",
    "車椅子": "images/icon_02_車椅子_stop.png",
    "自転車(電動)": "images/icon_03_自転車(電動)_stop.png",
    "自転車(非電動)": "images/icon_04_自転車(非電動)_stop.png",
    "バイク": "images/icon_05_バイク_stop.png",
    "バス": "images/icon_06_バス_stop.png",
    "タクシー": "images/icon_07_タクシー_stop.png",
    "自動車(運転)": "images/icon_08_自動車(運転)_stop.png",
    "自動車(同乗)": "images/icon_09_自動車(同乗)_stop.png",
    # 食事関連
    "食事(飲酒あり)": "images/icon_10_飲酒あり_stop.png",
    "食事(飲酒なし・不明)": "images/icon_11_飲酒なし・不明_stop.png",
    "軽食(カフェなど)": "images/icon_12_軽食(カフェなど)_stop.png",
    # 行動関連
    "買い物(日用品)": "images/icon_13_日用品_stop.png",
    "買い物(お土産)": "images/icon_14_お土産_stop.png",
    "ジョギング": "images/icon_15_ジョギング_stop.png",
    "ウォーキング": "images/icon_16_ウォーキング_stop.png",
    "ハイキング": "images/icon_17_ハイキング_stop.png",
    "散歩": "images/icon_18_散歩_stop.png",
    "スポーツ": "images/icon_19_スポーツ_stop.png",
    "レジャー": "images/icon_20_レジャー_stop.png",
    "ドライブ": "images/icon_21_ドライブ_stop.png",
    "景色鑑賞": "images/icon_22_景色鑑賞_stop.png",
    "名所観光": "images/icon_23_名所観光_stop.png",
    "休養・くつろぎ": "images/icon_24_休養・くつろぎ_stop.png",
    # その他
    "仕事": "images/icon_25_仕事_stop.png",
    "介護・看護": "images/icon_26_介護・看護_stop.png",
    "育児": "images/icon_27_育児_stop.png",
    "通院・療養": "images/icon_28_通院・療養_stop.png"
}
TAG_PRIORITY = [
    "食事(飲酒あり)", "食事(飲酒なし・不明)", "軽食(カフェなど)", "買い物(お土産)", "名所観光",
    "バス", "タクシー", "自動車(運転)", "自動車(同乗)", "徒歩",
    "買い物(日用品)", "ジョギング", "ウォーキング", "ハイキング", "散歩", 
    "スポーツ", "レジャー", "ドライブ", "景色鑑賞", "休養・くつろぎ", 
    "仕事", "介護・看護", "育児", "通院・療養"
]
DEFAULT_ICON_IMAGE = "images/default.png"
TAG_TO_GIF = {
    # 移動関連
    "徒歩": "gifs/anim_icon_01_徒歩.gif",
    "車椅子": "gifs/anim_icon_02_車椅子.gif",
    "自転車(電動)": "gifs/anim_icon_03_自転車(電動).gif",
    "自転車(非電動)": "gifs/anim_icon_04_自転車(非電動).gif",
    "バイク": "gifs/anim_icon_05_バイク.gif",
    "バス": "gifs/anim_icon_06_バス.gif",
    "タクシー": "gifs/anim_icon_07_タクシー.gif",
    "自動車(運転)": "gifs/anim_icon_08_自動車(運転).gif",
    "自動車(同乗)": "gifs/anim_icon_09_自動車(同乗).gif",
    # 食事関連
    "食事(飲酒あり)": "gifs/anim_icon_10_飲酒あり.gif",
    "食事(飲酒なし・不明)": "gifs/anim_icon_11_飲酒なし・不明.gif",
    "軽食(カフェなど)": "gifs/anim_icon_12_軽食（カフェなど）.gif",
    # 行動関連
    "買い物(日用品)": "gifs/anim_icon_13_日用品.gif",
    "買い物(お土産)": "gifs/anim_icon_14_お土産.gif",
    "ジョギング": "gifs/anim_icon_15_ジョギング.gif",
    "ウォーキング": "gifs/anim_icon_16_ウォーキング.gif",
    "ハイキング": "gifs/anim_icon_17_ハイキング.gif",
    "散歩": "gifs/anim_icon_18_散歩.gif",
    "スポーツ": "gifs/anim_icon_19_スポーツ.gif",
    "レジャー": "gifs/anim_icon_20_レジャー.gif",
    "ドライブ": "gifs/anim_icon_21_ドライブ.gif",
    "景色鑑賞": "gifs/anim_icon_22_景色鑑賞.gif",
    "名所観光": "gifs/anim_icon_23_名所観光.gif",
    "休養・くつろぎ": "gifs/anim_icon_24_休養・くつろぎ.gif",
    # その他
    "仕事": "gifs/anim_icon_25_仕事.gif",
    "介護・看護": "gifs/anim_icon_26_介護・看護.gif",
    "育児": "gifs/anim_icon_27_育児.gif",
    "通院・療養": "gifs/anim_icon_28_通院・療養.gif"
}
# ========================================================

geolocator = Nominatim(user_agent="travel-map-final")

# (既存の map_emotion_and_routes 関数と LayerToggleButtons クラスは削除してください)

### ★★★ 軌跡のみの地図を生成する新しい関数 ★★★
def map_traces_only(travels_data, output_html):
    """キャッシュデータから旅行記ごとの軌跡（線）のみを描画した地図を生成する"""
    if not travels_data:
        print("[ERROR] 地図に描画するデータがありません。")
        return

    # 地図の中心を最初の旅行記の開始地点に設定
    try:
        first_travel = travels_data[0]['places'][0]
        start_coords = (first_travel['latitude'], first_travel['longitude'])
        m = folium.Map(location=start_coords, zoom_start=10)
    except (IndexError, KeyError):
        # データがない場合は東京駅を中心にする
        m = folium.Map(location=[35.6812, 139.7671], zoom_start=10)

    # 各旅行記の軌跡を地図に追加
    for travel in travels_data:
        file_num = travel["file_num"]
        places = travel["places"]
        color = travel["color"]

        # 軌跡を描画するための座標リスト
        locations = [(p['latitude'], p['longitude']) for p in places if p.get('latitude') and p.get('longitude')]

        # 軌跡を格納するフィーチャーグループを作成（レイヤーコントロール用）
        trace_group = folium.FeatureGroup(name=f"旅行記ルート: {file_num}", show=True)

        # 訪問地が2箇所以上ある場合のみ線を描画
        if len(locations) > 1:
            folium.PolyLine(
                locations,
                color=color,
                weight=5,
                opacity=0.8
            ).add_to(trace_group)
        
        trace_group.add_to(m)

    # レイヤーコントロール（各軌跡の表示/非表示を切り替え）を追加
    folium.LayerControl().add_to(m)

    m.save(output_html)
    print(f"\n🌐 軌跡のみの地図を {output_html} に保存しました。")
# --- 座標取得・テキスト抽出・分析関数群 ---
# (geocode_gsi, geocode_place, extract_places, get_visit_hint, analyze_experience, get_image_as_base64 のコードは省略)
def get_image_as_base64(file_path):
    """画像ファイルを読み込み、HTML埋め込み用のBase64文字列を返す"""
    try:
        with open(file_path, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode("utf-8")
        # ファイル拡張子に応じてMIMEタイプを決定 (ここではgifに固定)
        return f"data:image/gif;base64,{encoded_string}"
    except FileNotFoundError:
        print(f"[WARNING] 画像ファイルが見つかりません: {file_path}")
        return None
def geocode_gsi(name):
    """国土地理院APIを使って地名の緯度経度を取得する"""
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
    """Geopyを使って地名の緯度経度を取得する"""
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
    messages = [{"role": "system", "content": "都道府県名を答えるときは，県名のみを答えてください．"}, {"role": "user", "content": f"以下の旅行記データから筆者が訪れたと考えられる都道府県を1つだけ答えてください．ただし，特定の語句に拘らずに旅行記全体から総合的に判断してください．\n\n{visited_places_text}"}]
    try:
        response = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages, temperature=0.2)
        return response.choices[0].message.content.strip()
    except: return "日本"
    
### ★★★ 機能変更 (1/2): exceptブロックを旧バージョン形式に修正 ★★★
def analyze_experience(text, move_tags_list, action_tags_list):
    """1回のAPIコールで感情スコアとタグを同時に抽出する"""
    if not text or not text.strip():
        return {"emotion_score": 0.5, "tags": []}

    print(f"⚡️ Analyzing (Emotion + Tags) for: '{text[:40]}...'")
    
    prompt = f"""
    以下のテキストは、旅行中のある場所での経験を記述したものです。
    このテキストを分析し、以下の3つのタスクを同時に実行してください。

    1.  **感情分析**: テキスト全体の感情を0.0（非常にネガティブ）から1.0（非常にポジティブ）の間の数値（スコア）で評価してください。ニュートラルな感情は0.5とします。
    2.  **移動タグ抽出**: 提示された「移動手段」タグリストの中から、テキスト内容に最も関連性の高いタグをすべて選択してください。
    3.  **行動タグ抽出**: 提示された「行動」タグリストの中から、テキスト内容に最も関連性の高いタグをすべて選択してください。

    関連性の高いタグが一つもなければ、空のリスト `[]` を返してください。
    出力は必ず、以下のキーを持つJSON形式で返してください。
    - `emotion_score`: 数値
    - `move_tags`: 文字列のリスト
    - `action_tags`: 文字列のリスト

    例:
    {{
        "emotion_score": 0.85,
        "move_tags": ["バス", "徒歩"],
        "action_tags": ["食事(飲酒なし・不明)", "景色鑑賞"]
    }}
    ---
    「移動手段」タグリスト: {move_tags_list}
    ---
    「行動」タグリスト: {action_tags_list}
    ---
    テキスト: 「{text}」
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたはテキストを多角的に分析し、指定されたJSON形式で感情スコアと複数種類のタグを正確に出力する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        
        score = result.get("emotion_score", 0.5)
        move_tags = result.get("move_tags", [])
        action_tags = result.get("action_tags", [])
        all_tags = move_tags + action_tags

        return {"emotion_score": score, "tags": all_tags}
    
    # 旧バージョン(v0.x)のopenaiライブラリ用のエラーハンドリング
    except openai.error.AuthenticationError as e:
        print(f"[FATAL ERROR] OpenAI認証エラー: {e}")
        raise # エラーを再発生させ、mainのtry-exceptで捕捉する
    except Exception as e:
        print(f"[ERROR] 統合分析中にエラーが発生しました: {e}")
        return {"emotion_score": 0.5, "tags": []}



### ★★★ 機能変更 (2/2): exceptブロックを旧バージョン形式に修正 ★★★
def main():
    """メイン処理"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        print(f"INFO: キャッシュディレクトリを作成しました: {CACHE_DIR}")

    input_file_path = input('ファイル番号が記載された.txtファイルのパスを入力してください: ')
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f: content = f.read()
        file_nums_raw = content.strip().split(',')
        file_nums = [num.strip() for num in file_nums_raw if num.strip()] 
        if not file_nums: print("[ERROR] 入力ファイルに有効なファイル番号が含まれていません。"); return
        print(f"INFO: ファイルから {len(file_nums)} 件のファイル番号を読み込みました。")
    except FileNotFoundError: print(f"[ERROR] 入力ファイルが見つかりません: {input_file_path}"); return
    except Exception as e: print(f"[ERROR] ファイルの読み込み中にエラーが発生しました: {e}"); return

    all_travels_data = []
    try:
        for i, file_num in enumerate(file_nums):
            cache_path = os.path.join(CACHE_DIR, f"{file_num}.json")
            if os.path.exists(cache_path):
                print(f"\n✅ [{file_num}] のキャッシュが見つかりました。読み込みます。")
                with open(cache_path, 'r', encoding='utf-8') as f:
                    travel_result_data = json.load(f)
                all_travels_data.append(travel_result_data)
                continue

            print(f"\n{'='*20} [{file_num}] の処理を開始 {'='*20}")
            path_journal = f'{directory}{file_num}.tra.json'
            
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

            grouped_experiences = defaultdict(list)
            for p in places_with_coords: grouped_experiences[p['place']].append(p['experience'])
            
            place_analysis_results = {}
            for place, experiences in grouped_experiences.items():
                analysis_result = analyze_experience(" ".join(experiences), MOVE_TAGS, ACTION_TAGS)
                place_analysis_results[place] = analysis_result

            for p in places_with_coords:
                analysis = place_analysis_results.get(p['place'], {"emotion_score": 0.5, "tags": []})
                p['emotion_score'] = analysis['emotion_score']
                p['tags'] = analysis['tags']
            
            final_travel_data = {
                "file_num": file_num, "places": places_with_coords,
                "color": COLORS[i % len(COLORS)], "region_hint": region_hint 
            }
            all_travels_data.append(final_travel_data)

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(final_travel_data, f, ensure_ascii=False, indent=4)
            print(f"✅ [{file_num}] の結果をキャッシュに保存しました。")
            
            print(f"📌 処理完了 ({file_num}): {len(places_with_coords)}件の訪問地を地図に追加します。")

    # 旧バージョン(v0.x)のopenaiライブラリ用のエラーハンドリング
    except openai.error.AuthenticationError as e:
        print("\n" + "="*50)
        print(f"[FATAL ERROR] OpenAIの認証に失敗しました: {e}")
        print("APIキーが間違っているか、クレジットが不足している可能性があります。")
        print("処理を中断し、現在までの結果で地図を生成します...")
        print("="*50 + "\n")
    except Exception as e:
        print(f"\n[FATAL ERROR] 予期せぬエラーにより処理を中断します: {e}")
        print("現在までの結果で地図を生成します...")

    base_name = "trace_only_map_"

    if all_travels_data:
        if len(all_travels_data) >= 4:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{base_name}{timestamp}{extension}"
        else:
            processed_file_nums = [str(t['file_num']) for t in all_travels_data]
            output_filename = f"{base_name}{'_'.join(processed_file_nums)}{extension}"
            
        print(f"\n🗺️ {len(all_travels_data)}件の旅行記データで軌跡のみの地図を生成します...")
        # ★★★ 変更点 2/2: 呼び出す関数を新しいものに変更 ★★★
        map_traces_only(all_travels_data, output_filename)
    else:
        print("\n地図を生成するための有効なデータがありませんでした。")


if __name__ == '__main__':
    main()