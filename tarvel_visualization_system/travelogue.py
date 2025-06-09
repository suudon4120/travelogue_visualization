import openai
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = API_KEY
import json
import folium
from geopy.geocoders import Nominatim
from collections import defaultdict
import time

# ========== 設定 ==========
# 保存先ディレクトリとファイルの基本名
directory = "../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules/"
base_name = "visited_places_map"
extension = ".html"

#旅行記のファイルのパス
file_num = input('分析を行うファイルの番号を入力：')
path_journal = f'{directory}{file_num}.tra.json'
JSON_FILE = path_journal       # 入力する旅行記のJSONファイル

#入力ファイルからファイル名を作成
filename = f"{base_name}{file_num}{extension}"
OUTPUT_HTML = filename  # 出力する地図のHTMLファイル

WAIT_TIME = 1  # Geocoding APIへのリクエスト間隔 (秒)
MODEL = "gpt-4o"  # 使用するモデル

#プレフィックスとサフィックス
prefix = '```json'
suffix = '```'
# ==========================
# JSONファイルの読み込み
with open(JSON_FILE, "r", encoding="utf-8") as f:
    travel_data = json.load(f)
    print(f"📜travel_data(jsonloadの結果)={travel_data}")

# テキストの連結
texts = []
for entry in travel_data:
    texts.extend(entry['text'])
print(f"📄texts(連結済みテキスト)={texts}")
# Geopyの設定
geolocator = Nominatim(user_agent="travel-map")

# 地名の緯度経度取得関数
def geocode_place(name, region_hint):
    try:
        print(f"🗺️ Geocoding: {name}...")
        location = geolocator.geocode(f"{name}, {region_hint}")
        time.sleep(WAIT_TIME)
        if location:
            print(f"✅ 成功: {name} → {location.latitude}, {location.longitude}")
            return location.latitude, location.longitude
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
    return None

# OpenAI APIを使って地名を抽出する関数
def extract_places(texts):
    prompt = f"""
    以下の旅行記のテキストから、訪れた場所の情報を抽出してください。
    出力には "place"（地名）、"latitude"（緯度）、"longitude"（経度）、"experience"（その場所での経験）、"reasoning"（その座標だと推定した理由）を必ず含めてください。
    緯度経度は、日本の「{region_hint}」周辺の地理情報と、テキスト内の文脈（例：「〇〇駅から徒歩5分」「△△の隣」など）を最大限考慮して、非常に高い精度で推定してください。

    出力は**絶対にJSON形式のリスト**として返してください。
    例:
    [
        {{
            "place": "湯畑", 
            "latitude": 36.6214, 
            "longitude": 138.5968, 
            "experience": "湯畑を散策しました。",
            "reasoning": "群馬県草津温泉の中心的な観光スポットであり、旅行記の文脈から草津温泉への訪問が明らかなため、湯畑の座標を指定しました。"
        }}
    ]

    テキスト: {texts}
    """

    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "system", "content": "あなたは旅行記から訪問地を正確に抽出する優秀な旅行ガイドです。具体的な地名、観光地、施設名を必ず抽出してください。"},
                  {"role": "user", "content": prompt}],
        temperature=0.5
    )

    # デバッグ用に出力
    print("🔍 OpenAI Response(prefix,suffix処理済みapi応答):")
    textforarukikata = response.choices[0].message.content
    textforarukikata = textforarukikata.removeprefix(prefix)
    textforarukikata = textforarukikata.removesuffix(suffix)
    textforarukikata = textforarukikata.strip()
    print(textforarukikata)

    try:
        result = json.loads(textforarukikata)
        # 正常なリスト形式かチェック
        if isinstance(result, list) and all(isinstance(item, dict) for item in result):
            return result
        else:
            print("[ERROR] 形式がリストではありません")
            return []
    except Exception as e:
        print(f"[ERROR] OpenAIの応答解析に失敗しました: {e}")
        return []

# 地名のヒントを検出する関数
def get_visit_hint(visited_places):
    # 訪問地が空の場合の処理
    if not visited_places:
        return "訪問地の情報がありません"

    messages = [
        {"role": "system", "content": "都道府県名を答えるときは，県名のみを答えてください．"},
        {"role": "user", "content": "以下の旅行記データから筆者が訪れたと考えられる都道府県を1つだけ答えてください．"},
        {"role": "user", "content": visited_places}
    ]

    try:
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=messages,
            temperature=0.2
        )
        hint = response.choices[0].message.content
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        hint = "エラーが発生しました"

    return hint

# 地図を生成する関数
def map_places(visited_places):
    #最初の地点を中心に地図作成
    start_lat, start_lon = visited_places[0]["latitude"], visited_places[0]["longitude"]
    print(f"🌅start_lat(visited_places0latitude)={start_lat}")
    m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
    print(f"👩‍💻m(foliumMapの中身)={m}")
    grouped = defaultdict(list)
    print(f"🧑‍🤝‍🧑grouped(defaultdict)={grouped}")

    locations = []#径路の座標リスト

    for item in visited_places:
        grouped[item['place']].append(item['experience'])

    for place, experiences in grouped.items():
        coords = geocode_place(place, REGION_HINT)
        print(f"🌏️coords(geocode_placeの結果格納)={coords}")
            

        if coords:
            folium.Marker(
                location=coords,
                popup=folium.Popup(f"<b>{place}</b><br>{'<br>'.join(experiences)}", max_width=350),
                tooltip=place,
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)

            #径路のために座標を保存
            locations.append(coords)
            print(f"🗾locations(径路用座標)={locations}")
        else:
            print(f"[!] 緯度経度が取得できませんでした: {place}")
            for item in visited_places:
                if item['place'] == place:
                    coords = (item['latitude'], item['longitude'])
                    print(f"📍 GPTの座標を使用: {place} → {coords}")
                    break
            # ピンの追加
            folium.Marker(
                location=coords,
                popup=folium.Popup(f"<b>{place}</b><br>{'<br>'.join(experiences)}", max_width=350),
                tooltip=place,
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)

            # 経路用に追加
            locations.append(coords)

        #径路を線で結ぶ
        folium.PolyLine(locations, color="blue", weight=5, opacity=0.7).add_to(m)    
        
    # 地図の保存
    m.save(OUTPUT_HTML)
    print(f"🌐 地図を {OUTPUT_HTML} に保存しました。")

# JSONファイルからデータを取得してヒントを生成
REGION_HINT = get_visit_hint(" ".join(texts))
print(f"💡訪問地のヒント＝{REGION_HINT}")

# 訪問地を抽出
visited_places = extract_places(" ".join(texts))
print("📌 抽出された訪問地:")
print(visited_places)

# 地図を作成
map_places(visited_places)