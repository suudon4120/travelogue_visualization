import openai
import os
from dotenv import load_dotenv
import json
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from geopy.distance import distance ### ★★★ 機能追加 ★★★
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
CACHE_DIR = "results_cache" ### ★★★ 機能追加: キャッシュ用ディレクトリ ★★★
MAX_DISTANCE_KM = 100  ### ★★★ 機能追加: 線を描画する最大距離(km) ★★★
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

### ★★★表示・非表示ボタンを1つに統合したクラス ★★★
class LayerToggleButtons(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
            var toggleControl = L.Control.extend({
                onAdd: function(map) {
                    var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
                    // ボタンを縦に並べるためのスタイル
                    container.style.display = 'flex';
                    container.style.flexDirection = 'column';
                    container.style.gap = '3px'; // ボタン間の隙間

                    // --- 全ルート表示ボタン ---
                    var showButton = L.DomUtil.create('div', 'leaflet-control-button', container);
                    showButton.style.backgroundColor = 'white';
                    showButton.style.padding = '5px';
                    showButton.style.border = '2px solid #ccc';
                    showButton.style.borderRadius = '5px';
                    showButton.style.cursor = 'pointer';
                    showButton.innerHTML = '全ルート表示';
                    
                    showButton.onclick = function(e) {
                        e.stopPropagation();
                        var checkboxes = document.querySelectorAll('.leaflet-control-layers-overlays .leaflet-control-layers-selector');
                        var labels = document.querySelectorAll('.leaflet-control-layers-overlays span');
                        for (var i = 0; i < labels.length; i++) {
                            if (labels[i].textContent.trim().startsWith('旅行記ルート')) {
                                // もしチェックが外れていれば、クリックする
                                if (checkboxes[i] && !checkboxes[i].checked) {
                                    checkboxes[i].click();
                                }
                            }
                        }
                    };

                    // --- 全ルート非表示ボタン ---
                    var hideButton = L.DomUtil.create('div', 'leaflet-control-button', container);
                    hideButton.style.backgroundColor = 'white';
                    hideButton.style.padding = '5px';
                    hideButton.style.border = '2px solid #ccc';
                    hideButton.style.borderRadius = '5px';
                    hideButton.style.cursor = 'pointer';
                    hideButton.innerHTML = '全ルート非表示';

                    hideButton.onclick = function(e) {
                        e.stopPropagation();
                        var checkboxes = document.querySelectorAll('.leaflet-control-layers-overlays .leaflet-control-layers-selector');
                        var labels = document.querySelectorAll('.leaflet-control-layers-overlays span');
                        for (var i = 0; i < labels.length; i++) {
                            if (labels[i].textContent.trim().startsWith('旅行記ルート')) {
                                // もしチェックが入っていれば、クリックする
                                if (checkboxes[i] && checkboxes[i].checked) {
                                    checkboxes[i].click();
                                }
                            }
                        }
                    };
                    
                    return container;
                }
            });
            var parent_map = {{ this._parent.get_name() }};
            parent_map.addControl(new toggleControl({ position: 'topright' }));
        {% endmacro %}
    """)

    def __init__(self):
        super(LayerToggleButtons, self).__init__()
        self._name = 'LayerToggleButtons'

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

### ★★★ 機能変更: extract_placesをextract_eventsに改名し、プロンプトを刷新 ★★★
def extract_events(texts, region_hint):
    """GPTを使って旅行記から「滞在」と「移動」のイベントを時系列で抽出する"""
    print("📌 イベント抽出（滞在・移動）のプロンプトを実行します...")
    prompt = f"""
    以下の旅行記のテキストを時系列に沿って分析し、「滞在（stop）」と「移動（move）」のイベントを交互に抽出してください。

    **抽出ルール:**
    - イベントは必ずリスト形式で、`"type"`キーを持つオブジェクトとしてください。
    - `"type": "stop"`: ある場所での行動や体験。
        - `"place"`: 地名
        - `"latitude"`, `"longitude"`: GPTによる推定座標（フォールバック用）
        - `"experience"`: その場所での具体的な体験
        - `"reasoning"`: 座標推定の理由
    - `"type": "move"`: 場所から場所への移動。
        - `"means"`: 移動手段（以下のリストから選択）
        - `"experience"`: 移動中の具体的な体験

    **移動手段リスト:** {MOVE_TAGS}

    **出力形式の厳守:**
    - 必ずJSON形式のリストとしてください。
    - 最初と最後のイベントは、多くの場合`"stop"`になります。
    - `"stop"`と`"move"`は交互に現れるのが基本ですが、テキストに記述がなければ片方が連続しても構いません。

    **出力例:**
    [
        {{
            "type": "stop",
            "place": "新宿駅",
            "latitude": 35.6909,
            "longitude": 139.7004,
            "experience": "新宿駅に到着し、友人とおちあった。",
            "reasoning": "テキストの出発点であり、新宿駅の座標を指定した。"
        }},
        {{
            "type": "move",
            "means": "バス",
            "experience": "高速バスで草津温泉に向かった。車窓からの景色がきれいだった。"
        }},
        {{
            "type": "stop",
            "place": "草津温泉バスターミナル",
            "latitude": 36.6222,
            "longitude": 138.5964,
            "experience": "草津温泉バスターミナルに到着。あたりは硫黄の匂いがした。",
            "reasoning": "テキストの記述と地名から座標を推定した。"
        }}
    ]

    ---
    **分析対象テキスト（日本の「{region_hint}」周辺）:**
    {texts}
    """
    # (openai.ChatCompletion.createの呼び出し部分は変更なし)
    response = openai.ChatCompletion.create(model=MODEL, messages=[{"role": "system", "content": f"あなたは旅行記を時系列で分析し、滞在（stop）と移動（move）のイベントを正確に抽出する専門家です。"}, {"role": "user", "content": prompt}], temperature=0.5)
    textforarukikata = response.choices[0].message.content.strip()
    if prefix in textforarukikata: textforarukikata = textforarukikata.split(prefix, 1)[1]
    if suffix in textforarukikata: textforarukikata = textforarukikata.rsplit(suffix, 1)[0]
    try:
        result = json.loads(textforarukikata.strip())
        if isinstance(result, list) and all(isinstance(item, dict) for item in result):
            return result
        else: return []
    except Exception as e:
        print(f"[ERROR] イベント抽出のJSON解析に失敗: {e}")
        return []


def get_visit_hint(visited_places_text):
    if not visited_places_text.strip(): return "日本"
    messages = [{"role": "system", "content": "都道府県名を答えるときは，県名のみを答えてください．"}, {"role": "user", "content": f"以下の旅行記データから筆者が訪れたと考えられる都道府県を1つだけ答えてください．ただし，特定の語句に拘らずに旅行記全体から総合的に判断してください．\n\n{visited_places_text}"}]
    try:
        response = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages, temperature=0.2)
        return response.choices[0].message.content.strip()
    except: return "日本"
    
### ★★★ 機能変更: analyze_experienceをanalyze_stop_detailsに書き換え ★★★
def analyze_stop_details(text, action_tags_list):
    """1回のAPIコールで感情スコアと「行動」タグを同時に抽出する"""
    if not text or not text.strip():
        return {"emotion_score": 0.5, "tags": []}

    print(f"⚡️ Analyzing (Emotion + Action Tags) for: '{text[:40]}...'")
    
    prompt = f"""
    以下のテキストは、旅行中のある「滞在」場所での経験を記述したものです。
    このテキストを分析し、以下の2つのタスクを同時に実行してください。

    1.  **感情分析**: テキスト全体の感情を0.0（非常にネガティブ）から1.0（非常にポジティブ）の間の数値（スコア）で評価してください。
    2.  **行動タグ抽出**: 提示された「行動」タグリストの中から、テキスト内容に最も関連性の高いタグをすべて選択してください。

    関連性の高いタグがなければ、空のリスト `[]` を返してください。
    出力は必ず、以下のキーを持つJSON形式で返してください。
    - `emotion_score`: 数値
    - `action_tags`: 文字列のリスト

    例:
    {{
        "emotion_score": 0.85,
        "action_tags": ["食事(飲酒なし・不明)", "景色鑑賞"]
    }}
    ---
    「行動」タグリスト: {action_tags_list}
    ---
    テキスト: 「{text}」
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたはテキストを多角的に分析し、指定されたJSON形式で感情スコアと行動タグを正確に出力する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        
        score = result.get("emotion_score", 0.5)
        action_tags = result.get("action_tags", [])

        return {"emotion_score": score, "tags": action_tags}
        
    except openai.error.AuthenticationError as e:
        print(f"[FATAL ERROR] OpenAI認証エラー: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] 滞在詳細の分析中にエラーが発生しました: {e}")
        return {"emotion_score": 0.5, "tags": []}


### ★★★ 機能変更: 軌跡描画ロジックを修正 ★★★
def map_emotion_and_routes(travels_data, output_html):
    """感情ヒートマップ、訪問地、移動手段をレイヤー化して地図を生成する"""
    if not travels_data: print("[ERROR] 地図に描画するデータがありません。"); return
    try:
        first_stop = next((p for t in travels_data for p in t['events'] if p.get('type') == 'stop'), None)
        if first_stop and 'latitude' in first_stop:
            start_coords = (first_stop['latitude'], first_stop['longitude'])
        else:
            start_coords = (35.6812, 139.7671)
        m = folium.Map(location=start_coords, zoom_start=10)
    except (IndexError, KeyError):
        m = folium.Map(location=[35.6812, 139.7671], zoom_start=10)

    heatmap_data = []
    for travel in travels_data:
        file_num, color, events = travel["file_num"], travel["color"], travel.get("events", [])
        
        route_group = folium.FeatureGroup(name=f"旅行記ルート: {file_num}", show=True)
        move_group = folium.FeatureGroup(name=f"移動手段: {file_num}", show=True)

        stop_events = [e for e in events if e.get('type') == 'stop' and 'latitude' in e]
        
        for stop_data in stop_events:
            coords = (stop_data['latitude'], stop_data['longitude'])
            tags = stop_data.get('tags', [])
            
            icon_to_use = None
            place_tags_set = set(tags)
            for tag in TAG_PRIORITY:
                if tag in place_tags_set and tag in TAG_TO_IMAGE:
                    image_path = TAG_TO_IMAGE[tag]
                    if os.path.exists(image_path):
                        icon_to_use = folium.features.CustomIcon(image_path, icon_size=(35, 35))
                        break
            if icon_to_use is None:
                if os.path.exists(DEFAULT_ICON_IMAGE):
                    icon_to_use = folium.features.CustomIcon(DEFAULT_ICON_IMAGE, icon_size=(30, 30))
                else:
                    icon_to_use = folium.Icon(color="gray", icon="question-sign")
            
            popup_html = f"<b>{stop_data['place']}</b> (旅行記: {file_num})<br>"
            popup_html += f"<b>感情スコア: {stop_data.get('emotion_score', 0.5):.2f}</b><br>"
            if tags:
                popup_html += f"<hr style='margin: 3px 0;'>"
                popup_html += "<b>タグ:</b><br>"
                tag_html = ""
                for tag in tags:
                    tag_style = "display:inline-block; background-color:#E0E0E0; color:#333; padding:2px 6px; margin:2px; border-radius:4px; font-size:12px;"
                    tag_html += f"<span style='{tag_style}'>{tag}</span>"
                popup_html += tag_html
            
            gif_html = ""
            for tag in tags:
                if tag in TAG_TO_GIF:
                    gif_path = TAG_TO_GIF[tag]
                    base64_gif = get_image_as_base64(gif_path)
                    if base64_gif:
                        if not gif_html:
                            gif_html += f"<hr style='margin: 3px 0;'>"
                            gif_html += "<b>関連画像:</b><br>"
                        gif_html += f'<img src="{base64_gif}" alt="{tag}" style="max-width: 95%; height: auto; margin-top: 5px; border-radius: 4px;">'
            popup_html += gif_html

            if 'reasoning' in stop_data and stop_data['reasoning']:
                popup_html += f"<hr style='margin: 3px 0;'>"
                popup_html += f"<b>推定理由:</b><br>{stop_data['reasoning']}<br>"
            popup_html += f"<hr style='margin: 3px 0;'>"
            popup_html += f"<b>体験:</b><br>{stop_data['experience']}"

            folium.Marker(
                location=coords, popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"{stop_data['place']} ({file_num})", icon=icon_to_use
            ).add_to(route_group)
            
            heatmap_data.append([coords[0], coords[1], stop_data.get('emotion_score', 0.5)])
        
        # --- 軌跡と移動手段の描画ロジック ---
        for i in range(len(stop_events) - 1):
            start_stop = stop_events[i]
            end_stop = stop_events[i+1]
            
            point1 = (start_stop['latitude'], start_stop['longitude'])
            point2 = (end_stop['latitude'], end_stop['longitude'])

            # 2点間の距離を計算
            dist = distance(point1, point2).km
            
            # 距離が上限値以下の場合のみ線を描画
            if dist <= MAX_DISTANCE_KM:
                folium.PolyLine([point1, point2], color=color, weight=5, opacity=0.7).add_to(route_group)

                # 移動イベントを探して中間ピンを配置
                start_index_in_events = -1
                for idx, event in enumerate(events):
                    if event == start_stop:
                        start_index_in_events = idx
                        break
                
                if start_index_in_events != -1:
                    move_event = next((e for e in events[start_index_in_events+1:] if e.get('type') == 'move'), None)
                    if move_event:
                        mid_lat = (point1[0] + point2[0]) / 2
                        mid_lon = (point1[1] + point2[1]) / 2
                        move_means = move_event.get('means', '不明')
                        
                        move_icon = None
                        if move_means in TAG_TO_IMAGE and os.path.exists(TAG_TO_IMAGE[move_means]):
                            move_icon = folium.features.CustomIcon(TAG_TO_IMAGE[move_means], icon_size=(30, 30))
                        else:
                            move_icon = folium.Icon(color='black', icon='arrow-right', prefix='fa')
                        
                        move_popup = f"<b>移動: {move_means}</b><br><hr>"
                        move_popup += move_event.get('experience', '記述なし')

                        folium.Marker(
                            location=[mid_lat, mid_lon],
                            popup=move_popup,
                            tooltip=f"移動: {move_means}",
                            icon=move_icon
                        ).add_to(move_group)

        route_group.add_to(m)
        move_group.add_to(m)

    if heatmap_data:
        heatmap_layer = folium.FeatureGroup(name="感情ヒートマップ", show=False)
        HeatMap(heatmap_data).add_to(heatmap_layer)
        heatmap_layer.add_to(m)

    folium.LayerControl().add_to(m)
    m.add_child(LayerToggleButtons())
    
    m.save(output_html)
    print(f"\n🌐 滞在・移動を可視化した地図を {output_html} に保存しました。")

def main():
    """メイン処理"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    input_file_path = input('ファイル番号が記載された.txtファイルのパスを入力してください: ')
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f: content = f.read()
        file_nums = [num.strip() for num in content.strip().split(',') if num.strip()]
    except Exception as e:
        print(f"[ERROR] 入力ファイルの読み込みに失敗: {e}"); return

    all_travels_data = []
    try:
        for i, file_num in enumerate(file_nums):
            cache_path = os.path.join(CACHE_DIR, f"{file_num}.json")
            if os.path.exists(cache_path):
                print(f"\n✅ [{file_num}] のキャッシュを読み込みます。")
                with open(cache_path, 'r', encoding='utf-8') as f:
                    all_travels_data.append(json.load(f))
                continue

            print(f"\n{'='*20} [{file_num}] の処理を開始 {'='*20}")
            path_journal = f'{directory}{file_num}.tra.json'
            if not os.path.exists(path_journal): print(f"[WARNING] ファイルが見つかりません: {path_journal}"); continue
            
            with open(path_journal, "r", encoding="utf-8") as f: travel_data = json.load(f)
            texts = [entry['text'] for entry in travel_data if entry.get('text')]
            full_text = " ".join(sum(texts, []))
            if not full_text.strip(): print(f"[WARNING] テキストデータがありません。"); continue
            
            region_hint = get_visit_hint(full_text)
            events = extract_events(full_text, region_hint)
            if not events: print(f"[WARNING] イベントを抽出できませんでした。"); continue

            stop_events_to_process = [e for e in events if e.get('type') == 'stop']
            
            for stop_event in stop_events_to_process:
                place_name = stop_event.get('place')
                if not place_name: continue

                coords = geocode_place(place_name, region_hint)
                if not coords:
                    coords = (stop_event.get('latitude', 0.0), stop_event.get('longitude', 0.0))
                    if coords[0] == 0.0 and coords[1] == 0.0: coords = None
                if not coords:
                    coords = geocode_gsi(place_name)
                
                if coords:
                    stop_event['latitude'] = coords[0]
                    stop_event['longitude'] = coords[1]
                else:
                    print(f"[!] ジオコーディング失敗: {place_name}")
                    if 'latitude' in stop_event: del stop_event['latitude']

            # 場所ごとにまとめたexperienceから感情と行動タグを抽出
            grouped_experiences = defaultdict(list)
            for e in stop_events_to_process:
                if e.get('place'): # placeキーがあるもののみ
                    grouped_experiences[e['place']].append(e.get('experience', ''))
            
            place_analysis_results = {}
            for place, experiences in grouped_experiences.items():
                combined_experience = " ".join(experiences)
                ### ★★★ ここが修正箇所です ★★★
                # 正しい関数名 analyze_stop_details を使用する
                analysis_result = analyze_stop_details(combined_experience, ACTION_TAGS)
                place_analysis_results[place] = analysis_result

            # 感情スコアとタグを元のstop_eventに付与
            for stop_event in stop_events_to_process:
                if stop_event.get('place') in place_analysis_results:
                    analysis = place_analysis_results[stop_event['place']]
                    stop_event['emotion_score'] = analysis['emotion_score']
                    stop_event['tags'] = analysis['tags']
                else: # 分析結果がない場合（ほぼあり得ないが安全のため）
                    stop_event['emotion_score'] = 0.5
                    stop_event['tags'] = []
            
            final_travel_data = {
                "file_num": file_num, "events": events,
                "color": COLORS[i % len(COLORS)], "region_hint": region_hint 
            }
            all_travels_data.append(final_travel_data)

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(final_travel_data, f, ensure_ascii=False, indent=4)
            print(f"✅ [{file_num}] の結果をキャッシュに保存しました。")

    except openai.error.AuthenticationError as e:
        print(f"\n[FATAL ERROR] OpenAI認証エラー。処理を中断します。: {e}")
    except Exception as e:
        print(f"\n[FATAL ERROR] 予期せぬエラーで処理を中断します: {e}")

    if all_travels_data:
        if len(all_travels_data) >= 4:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{base_name}{timestamp}{extension}"
        else:
            processed_file_nums = [str(t['file_num']) for t in all_travels_data]
            output_filename = f"{base_name}{'_'.join(processed_file_nums)}{extension}"
            
        map_emotion_and_routes(all_travels_data, output_filename)
    else:
        print("\n地図を生成するための有効なデータがありませんでした。")

if __name__ == '__main__':
    main()