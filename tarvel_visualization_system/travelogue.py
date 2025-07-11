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

class LayerToggleButtons(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
            var toggleControl = L.Control.extend({
                onAdd: function(map) {
                    var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
                    container.style.display = 'flex';
                    container.style.flexDirection = 'column';
                    container.style.gap = '3px';

                    // --- 全表示ボタン ---
                    var showButton = L.DomUtil.create('div', '', container);
                    showButton.style.backgroundColor = 'white';
                    showButton.style.padding = '5px';
                    showButton.style.border = '2px solid #ccc';
                    showButton.style.borderRadius = '5px';
                    showButton.style.cursor = 'pointer';
                    showButton.innerHTML = '全表示'; // テキストをより汎用的に変更
                    
                    showButton.onclick = function(e) {
                        e.stopPropagation();
                        document.querySelectorAll('.leaflet-control-layers-overlays label').forEach(function(labelDiv) {
                            const span = labelDiv.querySelector('span');
                            const checkbox = labelDiv.querySelector('input[type="checkbox"]');
                            if (span && checkbox) {
                                const labelText = span.textContent.trim();
                                // ★★★ 修正箇所 ★★★
                                // 「旅行記ルート」または「移動手段」で始まるレイヤーを対象にする
                                if (labelText.startsWith('旅行記ルート') || labelText.startsWith('移動手段')) {
                                    if (!checkbox.checked) {
                                        checkbox.click();
                                    }
                                }
                            }
                        });
                    };

                    // --- 全非表示ボタン ---
                    var hideButton = L.DomUtil.create('div', '', container);
                    hideButton.style.backgroundColor = 'white';
                    hideButton.style.padding = '5px';
                    hideButton.style.border = '2px solid #ccc';
                    hideButton.style.borderRadius = '5px';
                    hideButton.style.cursor = 'pointer';
                    hideButton.innerHTML = '全非表示'; // テキストをより汎用的に変更

                    hideButton.onclick = function(e) {
                        e.stopPropagation();
                        document.querySelectorAll('.leaflet-control-layers-overlays label').forEach(function(labelDiv) {
                            const span = labelDiv.querySelector('span');
                            const checkbox = labelDiv.querySelector('input[type="checkbox"]');
                            if (span && checkbox) {
                                const labelText = span.textContent.trim();
                                // ★★★ 修正箇所 ★★★
                                // 「旅行記ルート」または「移動手段」で始まるレイヤーを対象にする
                                if (labelText.startsWith('旅行記ルート') || labelText.startsWith('移動手段')) {
                                    if (checkbox.checked) {
                                        checkbox.click();
                                    }
                                }
                            }
                        });
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
    
def analyze_stop_emotions_by_tag(text, action_tags_list):
    """
    1回のAPIコールで、関連する行動タグを抽出し、タグごとの感情スコアを算出する
    """
    if not text or not text.strip():
        return {}

    print(f"⚡️ Analyzing (Per-Tag Emotions) for: '{text[:40]}...'")
    
    prompt = f"""
    以下のテキストは、旅行中のある「滞在」場所での経験を記述したものです。
    このテキストを分析し、以下のステップを同時に実行してください。

    1.  **タグ抽出**: 提示された「行動」タグリストの中から、テキスト内容に最も関連性の高いタグをすべて選択してください。
    2.  **タグ別感情分析**: ステップ1で選択した各タグについて、そのタグに関連するテキスト部分の感情を個別に分析し、0.0（非常にネガティブ）から1.0（非常にポジティブ）のスコアを算出してください。

    関連性の高いタグが一つもなければ、空のオブジェクト `{{}}` を返してください。
    出力は必ず、キーが「タグ名」、値が「感情スコア」のJSONオブジェクト形式で返してください。

    例:
    {{
        "食事(飲酒なし・不明)": 0.85,
        "景色鑑賞": 1.0
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
                {"role": "system", "content": "あなたはテキストを多角的に分析し、関連する行動タグとそのタグに対応する個別の感情スコアをJSONオブジェクトとして正確に出力する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        # resultは {"タグ1": スコア1, "タグ2": スコア2, ...} という形式
        result = json.loads(response.choices[0].message.content)
        
        print(f"✅ Per-tag analysis successful. Result: {result}")
        return result
        
    except openai.error.AuthenticationError as e:
        print(f"[FATAL ERROR] OpenAI認証エラー: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] タグ別感情分析中にエラーが発生しました: {e}")
        return {}

def map_emotion_and_routes(travels_data, output_html):
    """訪問地、移動手段、およびタグ別感情ヒートマップをレイヤー化して地図を生成する"""
    if not travels_data: print("[ERROR] 地図に描画するデータがありません。"); return
    try:
        first_stop = next((p for t in travels_data for p in t['events'] if p.get('type') == 'stop' and 'latitude' in p), None)
        start_coords = (first_stop['latitude'], first_stop['longitude']) if first_stop else (35.6812, 139.7671)
        m = folium.Map(location=start_coords, zoom_start=10)
    except (IndexError, KeyError):
        m = folium.Map(location=[35.6812, 139.7671], zoom_start=10)
    
    heatmap_data_by_tag = defaultdict(list)

    for travel in travels_data:
        file_num, color, events = travel["file_num"], travel["color"], travel.get("events", [])
        
        route_group = folium.FeatureGroup(name=f"旅行記ルート: {file_num}", show=True)
        move_group = folium.FeatureGroup(name=f"移動手段: {file_num}", show=True)

        stop_events = [e for e in events if e.get('type') == 'stop' and 'latitude' in e]
        
        for stop_data in stop_events:
            coords = (stop_data['latitude'], stop_data['longitude'])
            per_tag_emotions = stop_data.get('per_tag_emotions', {})

            ### ★★★ ここが修正箇所です ★★★
            # per_tag_emotions 辞書のキー（＝タグ名）からタグのリストを作成
            tags = list(per_tag_emotions.keys())
            
            # --- アイコンを決定するロジック ---
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
            
            # --- ポップアップHTMLの組み立て ---
            popup_html = f"<b>{stop_data['place']}</b> (旅行記: {file_num})<br>"
            if per_tag_emotions:
                popup_html += f"<hr style='margin: 3px 0;'>"
                popup_html += "<b>タグ別感情スコア:</b><br>"
                tag_html = ""
                for tag, score in per_tag_emotions.items():
                    tag_style = "display:inline-block; background-color:#E0E0E0; color:#333; padding:2px 6px; margin:2px; border-radius:4px; font-size:12px;"
                    tag_html += f"<span style='{tag_style}'>{tag} ({score:.2f})</span>"
                popup_html += tag_html
            
            gif_html = ""
            if tags: # tags変数が存在することを確認
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
            
            # --- ヒートマップ用データの集計 ---
            for tag, score in per_tag_emotions.items():
                heatmap_data_by_tag[tag].append([coords[0], coords[1], score])
        
        # --- 軌跡と移動手段の描画ロジック ---
        for i in range(len(stop_events) - 1):
            start_stop = stop_events[i]
            end_stop = stop_events[i+1]
            
            point1 = (start_stop['latitude'], start_stop['longitude'])
            point2 = (end_stop['latitude'], end_stop['longitude'])

            dist = distance(point1, point2).km
            
            if dist <= MAX_DISTANCE_KM:
                folium.PolyLine([point1, point2], color=color, weight=5, opacity=0.7).add_to(route_group)

                start_index_in_events = -1
                try: start_index_in_events = events.index(start_stop)
                except ValueError: continue
                
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

    # --- タグごとのヒートマップレイヤーを生成 ---
    for tag, data_points in heatmap_data_by_tag.items():
        if data_points:
            heatmap_layer = folium.FeatureGroup(name=f"感情ヒートマップ: {tag}", show=False)
            HeatMap(data_points, radius=20).add_to(heatmap_layer)
            heatmap_layer.add_to(m)

    folium.LayerControl().add_to(m)
    m.add_child(LayerToggleButtons())
    
    m.save(output_html)
    print(f"\n🌐 タグ別感情分析付きの地図を {output_html} に保存しました。")

def main():
    """メイン処理"""
    if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)
    input_file_path = input('ファイル番号が記載された.txtファイルのパスを入力してください: ')
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f: content = f.read()
        file_nums = [num.strip() for num in content.strip().split(',') if num.strip()]
    except Exception as e: print(f"[ERROR] 入力ファイルの読み込みに失敗: {e}"); return

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

                # タグ別感情分析
                experience_text = stop_event.get('experience', '')
                # 新しい分析関数を呼び出す
                per_tag_emotions = analyze_stop_emotions_by_tag(experience_text, ACTION_TAGS)
                stop_event['per_tag_emotions'] = per_tag_emotions

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