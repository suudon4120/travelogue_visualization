import openai
import os
from dotenv import load_dotenv
import json
import folium
from geopy.geocoders import Nominatim
from collections import defaultdict
import time

# .envファイルから環境変数を読み込む
load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    raise ValueError("OpenAIのAPIキーが設定されていません。.envファイルを確認してください。")
openai.api_key = API_KEY

# ========== 設定 ==========
# データセットのディレクトリとファイルの基本名
directory = "../../2022-地球の歩き方旅行記データセット/data_arukikata/data/domestic/with_schedules/"
base_name = "visited_places_map_"
extension = ".html"

# 各旅行記の経路に適用する色のリスト
COLORS = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'lightgray']

WAIT_TIME = 1  # Geocoding APIへのリクエスト間隔 (秒)
MODEL = "gpt-4o"  # 使用するモデル

#プレフィックスとサフィックス
prefix = '```json'
suffix = '```'
# ==========================

# Geopyの設定
geolocator = Nominatim(user_agent="travel-map-approach2")

# 地名の緯度経度取得関数
def geocode_place(name, region_hint):
    """Geopyを使って地名の緯度経度を取得する"""
    try:
        # ヒントを追加して検索精度を向上
        query = f"{name}, {region_hint}"
        print(f"🗺️ Geocoding (Geopy): '{query}'...")
        location = geolocator.geocode(query, timeout=10)
        time.sleep(WAIT_TIME) # APIへの負荷を考慮
        if location:
            print(f"✅ Geopy Success: {name} → {location.latitude}, {location.longitude}")
            return location.latitude, location.longitude
    except Exception as e:
        print(f"[ERROR] Geopyでのジオコーディング中にエラーが発生しました: {name}: {e}")
    print(f"❌ Geopy Failed: {name}")
    return None

# OpenAI APIを使って地名を抽出する関数
def extract_places(texts, region_hint):
    """GPTを使って旅行記から地名と体験、フォールバック用の座標を抽出する"""
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
        messages=[{"role": "system", "content": f"あなたは旅行記から訪問地を正確に抽出する優秀な旅行ガイドです。日本の「{region_hint}」に関する地理に詳しいです。"},
                  {"role": "user", "content": prompt}],
        temperature=0.5
    )
    
    print("🔍 OpenAI Response (地名抽出):")
    textforarukikata = response.choices[0].message.content
    textforarukikata = textforarukikata.strip()
    if textforarukikata.startswith(prefix):
        textforarukikata = textforarukikata[len(prefix):]
    if textforarukikata.endswith(suffix):
        textforarukikata = textforarukikata[:-len(suffix)]
    textforarukikata = textforarukikata.strip()
    print(textforarukikata)

    try:
        result = json.loads(textforarukikata)
        if isinstance(result, list) and all(isinstance(item, dict) for item in result):
            for item in result:
                item['latitude'] = float(item.get('latitude', 0.0))
                item['longitude'] = float(item.get('longitude', 0.0))
            return result
        else:
            print("[ERROR] 形式がリストではありません")
            return []
    except Exception as e:
        print(f"[ERROR] OpenAIの応答解析に失敗しました: {e}")
        return []

# 地名のヒントを検出する関数
def get_visit_hint(visited_places_text):
    """旅行記テキストから訪問した都道府県のヒントを取得する"""
    if not visited_places_text.strip():
        return "日本"
    messages = [
        {"role": "system", "content": "都道府県名を答えるときは，県名のみを答えてください．"},
        {"role": "user", "content": f"以下の旅行記データから筆者が訪れたと考えられる都道府県を1つだけ答えてください．\n\n{visited_places_text}"}
    ]
    try:
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=messages,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return "日本"

# 複数の旅行記データを受け取り、地図を生成する関数
def map_multiple_travels(travels_data, output_html):
    """
    複数の旅行記データを地図上に描画する。
    Geopyでの座標取得を優先し、失敗したらGPTの座標を使用する。
    """
    if not travels_data:
        print("[ERROR] 地図に描画するデータがありません。")
        return

    # 地図の中心を決定
    try:
        first_travel = travels_data[0]
        # ### アプローチ2の変更点 ###: 最初の場所をGeopyで取得して中心にする
        first_place = first_travel["places"][0]
        region_hint = first_travel["region_hint"]
        start_coords = geocode_place(first_place['place'], region_hint)
        if not start_coords:
             start_coords = (first_place['latitude'], first_place['longitude'])
        m = folium.Map(location=start_coords, zoom_start=10)
    except (IndexError, KeyError):
        print("[ERROR] 地図の中心座標を決定できませんでした。東京駅をデフォルトにします。")
        m = folium.Map(location=[35.6812, 139.7671], zoom_start=10)

    # 各旅行記を地図に描画
    for travel in travels_data:
        file_num = travel["file_num"]
        places = travel["places"]
        color = travel["color"]
        region_hint = travel["region_hint"] # ヒントを取得
        locations = []

        grouped = defaultdict(list)
        for item in places:
            grouped[item['place']].append(item['experience'])

        for place, experiences in grouped.items():
            # ### アプローチ2の変更点 ###: ここからが座標決定のメインロジック
            # 1. まずGeopyでジオコーディングを試みる
            coords = geocode_place(place, region_hint)
            
            # 2. Geopyで失敗した場合、GPTが生成した座標をフォールバックとして使用
            if not coords:
                print(f"[!] Geopyに失敗。GPTの推定座標を利用します: {place}")
                for item in places:
                    if item['place'] == place:
                        gpt_coords = (item['latitude'], item['longitude'])
                        # GPTの座標が(0,0)でないことを確認
                        if gpt_coords[0] != 0.0 or gpt_coords[1] != 0.0:
                            coords = gpt_coords
                        break
            # ### アプローチ2の変更点（ここまで） ###

            if coords:
                folium.Marker(
                    location=coords,
                    popup=folium.Popup(f"<b>{place} (旅行記: {file_num})</b><br>{'<br>'.join(experiences)}", max_width=350),
                    tooltip=f"{place} ({file_num})",
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(m)
                locations.append(coords)
            else:
                print(f"[!] 緯度経度が最終的に取得できませんでした: {place} (旅行記: {file_num})")

        if len(locations) > 1:
            folium.PolyLine(locations, color=color, weight=5, opacity=0.7).add_to(m)
    
    m.save(output_html)
    print(f"\n🌐 複数の旅行記の地図を {output_html} に保存しました。")

def main():
    """メイン処理"""
    file_nums_str = input('分析を行うファイルの番号をカンマ区切りで入力してください（例: 1,5,10）：')
    file_nums = [num.strip() for num in file_nums_str.split(',')]

    all_travels_data = []

    for i, file_num in enumerate(file_nums):
        path_journal = f'{directory}{file_num}.tra.json'
        print(f"\n{'='*20} [{file_num}] の処理を開始 {'='*20}")

        if not os.path.exists(path_journal):
            print(f"[WARNING] ファイルが見つかりません: {path_journal}")
            continue
        
        try:
            with open(path_journal, "r", encoding="utf-8") as f:
                travel_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] JSONファイルの読み込みに失敗しました: {e}")
            continue

        texts = []
        for entry in travel_data:
            texts.extend(entry['text'])
        full_text = " ".join(texts)

        if not full_text.strip():
            print(f"[WARNING] 旅行記 {file_num} にはテキストデータがありません。")
            continue

        region_hint = get_visit_hint(full_text)
        print(f"💡 訪問地のヒント: {region_hint}")

        visited_places = extract_places(full_text, region_hint)
        if not visited_places:
            print(f"[WARNING] 旅行記 {file_num} から訪問地を抽出できませんでした。")
            continue
        
        print(f"📌 抽出された訪問地 ({file_num}): {len(visited_places)}件")
        
        # ### アプローチ2の変更点 ###: `region_hint`もデータに含めて後続の関数に渡す
        all_travels_data.append({
            "file_num": file_num,
            "places": visited_places,
            "color": COLORS[i % len(COLORS)],
            "region_hint": region_hint 
        })

    if all_travels_data:
        output_filename = f"{base_name}{'_'.join(file_nums)}{extension}"
        map_multiple_travels(all_travels_data, output_filename)
    else:
        print("\n地図を生成するためのデータがありませんでした。")

if __name__ == '__main__':
    main()