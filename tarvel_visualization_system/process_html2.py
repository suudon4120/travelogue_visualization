import re
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import numpy as np
from bs4 import BeautifulSoup

# PySALによる空間分析ライブラリ
from libpysal.weights import KNN
from esda.moran import Moran
from esda.getisord import G_Local

# 地理的加重回帰ライブラリ
from mgwr.gwr import GWR, GWRResults
from mgwr.sel_bw import Sel_BW

# 可視化ライブラリ
import matplotlib.pyplot as plt
from tqdm import tqdm # 進捗表示用

# 既存の関数はそのまま
def extract_data_from_html(file_path):
    # (変更なし)
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script')
    all_places = []
    marker_pattern = re.compile(r"L\.marker\(\s*(\[.*?\]),\s*\{")
    popup_pattern = re.compile(r"<b>タグ別感情スコア:</b><br>(.*?)<hr style='margin: 3px 0;'>", re.DOTALL)
    score_pattern = re.compile(r"\(([\d\.-]+)\)")
    def get_avg_score(popup_html):
        scores_html = popup_pattern.search(popup_html)
        if scores_html:
            scores = [float(s) for s in score_pattern.findall(scores_html.group(1))]
            return np.mean(scores) if scores else 0.5
        return 0.5
    for script in scripts:
        script_text = script.string
        if script_text:
            markers = marker_pattern.finditer(script_text)
            popups = re.finditer(r'var html_.*? = \$\(`(.*?)`\)\[0\];', script_text, re.DOTALL)
            marker_list = list(markers)
            popup_list = list(popups)
            for i in range(min(len(marker_list), len(popup_list))):
                try:
                    lat_lon_str = marker_list[i].group(1)
                    lat, lon = json.loads(lat_lon_str)
                    popup_html = popup_list[i].group(1).replace('\\n', '').replace('\\"', '"')
                    avg_score = get_avg_score(popup_html)
                    all_places.append([lat, lon, avg_score])
                except (json.JSONDecodeError, IndexError): continue
    heat_layer_pattern = re.compile(r"L.heatLayer\(\s*(\[\[.*?\]\]),\s*\{", re.DOTALL)
    heat_match = heat_layer_pattern.search(html_content)
    if heat_match:
        heat_data_str = heat_match.group(1)
        heat_data = json.loads(heat_data_str)
        all_places.extend(heat_data)
    df = pd.DataFrame(all_places, columns=['lat', 'lon', 'emotion_score'])
    df = df.drop_duplicates(subset=['lat', 'lon'])
    return df.values.tolist()


# --- メイン処理 ---
# 1. HTMLからデータを抽出
file_path = 'visited_places_map_emotion_batch_20250729_184324.html'
data = extract_data_from_html(file_path)

if not data:
    print("HTMLファイルからデータを抽出できませんでした。")
else:
    print(f"{len(data)}件のユニークな地点データを抽出しました。")
    gdf = gpd.GeoDataFrame(
        pd.DataFrame(data, columns=['latitude', 'longitude', 'emotion_score']),
        geometry=gpd.points_from_xy(pd.DataFrame(data)[1], pd.DataFrame(data)[0]),
        crs="EPSG:4326"
    )

    # (オプション) 日本国内のデータのみにフィルタリング
    # ... 以前のコードと同じ ...
    try:
        # Natural Earthからダウンロードした国のシェープファイルを読み込む
        world = gpd.read_file("./shapefiles/ne_110m_admin_0_countries.shp")
        # 日本のジオメトリのみを抽出
        japan_gdf = world[world['ADMIN'] == 'Japan']

        # 空間結合（sjoin）を使い、日本の領域内（within）にあるポイントだけを抽出
        gdf_japan = gpd.sjoin(gdf, japan_gdf, how="inner", predicate='within')
        
        print(f"\nフィルタリング後、{len(gdf_japan)}件のデータが日本国内にあると判断されました。")
        
        # 分析対象のGeoDataFrameを日本国内のデータに入れ替える
        gdf = gdf_japan.copy()
        # sjoinで不要な列が追加されるため、元の列のみを保持
        gdf = gdf[['latitude', 'longitude', 'emotion_score', 'geometry']]

    except Exception as e:
        print(f"シェープファイルの読み込みまたはフィルタリングでエラーが発生しました: {e}")
        print("Natural Earthのシェープファイルが同じディレクトリに存在するか確認してください。")
        # エラーが発生した場合は、フィルタリングせずに処理を続行
        pass
    # =================================================================
    # 2. 【新規追加】説明変数のためのデータ準備と計算
    # =================================================================
    # =================================================================
    # 2. 【修正】説明変数のためのデータ準備と計算
    # =================================================================
    # =================================================================
    # 2. 【飲食店のみ版】説明変数のためのデータ準備と計算
    # =================================================================
    print("\n--- 2. 説明変数の準備 ---")
    
    try:
        # 2.1 ★飲食店のシェープファイルのみを読み込む
        print("飲食店のシェープファイルを読み込んでいます...")
        
        # 'restaurants.shp' はご自身で保存したファイル名に合わせる
        restaurants = gpd.read_file("shapefiles/osm_japan_pois_restaurant.gpkg")
        
        # CRS（座標参照系）を感情スコアのデータに合わせる
        restaurants = restaurants.to_crs(gdf.crs)

        print(f"飲食店データを{len(restaurants)}件読み込みました。")

        # 2.2 ★飲食店密度のみを計算
        # 座標系をメートル単位（UTM）に変換して距離計算を正確に行う
        gdf_proj = gdf.to_crs(epsg=32654)
        restaurants_proj = restaurants.to_crs(gdf_proj.crs)

        # 各地点から半径500m以内にあるPOIの数をカウント
        radius_m = 500
        print(f"各地点の半径{radius_m}m以内の飲食店密度を計算します...")
        
        restaurant_density = []
        
        # tqdmで進捗を可視化
        for point in tqdm(gdf_proj.geometry, desc="密度計算中"):
            buffer = point.buffer(radius_m)
            possible_restaurants = restaurants_proj.iloc[restaurants_proj.sindex.query(buffer)]
            actual_restaurants = possible_restaurants[possible_restaurants.intersects(buffer)]
            restaurant_density.append(len(actual_restaurants))

        gdf['restaurant_density'] = restaurant_density
        
        print("密度変数の計算が完了しました。")
        print(gdf[['emotion_score', 'restaurant_density']].describe())

        # =================================================================
        # 3. 【飲食店のみ版】地理的加重回帰 (GWR)
        # =================================================================
        print("\n--- 3. 地理的加重回帰 (GWR) ---")
        # 3.1 GWR用のデータを準備
        g_y = gdf['emotion_score'].values.reshape(-1, 1)
        # ★説明変数を飲食店密度のみに変更
        g_X = gdf[['restaurant_density']].values
        
        # 座標をメートル単位に変換（再利用）
        g_coords = list(zip(gdf_proj.geometry.x, gdf_proj.geometry.y))
        # =================================================================
        # 【★★ ここから追加 ★★】
        # 5. 分析範囲を関東地方に限定するフィルタリング
        # =================================================================
        print("\n--- 5. 分析範囲を関東地方に限定 ---")

        # 関東地方のおおよその緯度経度の範囲を定義
        lat_min, lat_max = 34.8, 37.2
        lon_min, lon_max = 138.5, 141.0

        # 範囲内のデータのみを抽出
        gdf_kanto = gdf[
            (gdf['latitude'] >= lat_min) & (gdf['latitude'] <= lat_max) &
            (gdf['longitude'] >= lon_min) & (gdf['longitude'] <= lon_max)
        ].copy() # .copy() を付けて警告を防ぐ

        print(f"関東地方のデータ {len(gdf_kanto)}件を抽出しました。")

        # データが少なすぎないかチェック
        if len(gdf_kanto) < 50: # 閾値は適宜調整
            print("分析するにはデータが少なすぎるため、処理を終了します。")
        else:
            # 【★★ ここまで追加 ★★】

        # =================================================================
        # 6. 【変更】地理的加重回帰 (GWR) - 関東データを使用
        # =================================================================
            print("\n--- 6. 地理的加重回帰 (GWR) ---")
        # 6.1 GWR用のデータを準備 (★gdf_kanto を使用)
        g_y = gdf_kanto['emotion_score'].values.reshape(-1, 1)
        g_X = gdf_kanto[['restaurant_density']].values
        
        # 座標をメートル単位に変換 (★gdf_kanto を使用)
        gdf_proj_kanto = gdf_kanto.to_crs(epsg=32654)
        g_coords = list(zip(gdf_proj_kanto.geometry.x, gdf_proj_kanto.geometry.y))
        
        # 6.2 GWRの実行
        try:
            # (GWRの実行と可視化のコードは、入力が gdf_kanto になっている以外は同じ)
            gwr_selector = Sel_BW(g_coords, g_y, g_X)
            gwr_bw = gwr_selector.search()
            print(f"【関東地方】GWRの最適なバンド幅: {gwr_bw}")
            
            gwr_model = GWR(g_coords, g_y, g_X, gwr_bw, fixed=False)
            gwr_results = gwr_model.fit()
            
            # ★結果を gdf_kanto に追加
            gdf_kanto['gwr_coeff_restaurant'] = gwr_results.params[:, 1]
            gdf_kanto['gwr_local_r2'] = gwr_results.localR2

            # GWRのサマリーを表示
            print("\n--- GWRモデルの要約 (関東地方) ---")
            print(gwr_results.summary())

            # =================================================================
            # 7. 【変更】結果の可視化 - 関東データを使用
            # =================================================================
            print("\n--- 7. GWR結果の可視化 ---")
            fig, axes = plt.subplots(1, 2, figsize=(16, 7))

            # ★gdf_kanto をプロット
            gdf_kanto.plot(column='gwr_coeff_restaurant', cmap='coolwarm', legend=True, ax=axes[0])
            axes[0].set_title("GWR Coefficient for 'Restaurant Density' (Kanto)")
            
            gdf_kanto.plot(column='gwr_local_r2', cmap='viridis', legend=True, ax=axes[1])
            axes[1].set_title("GWR Local R-squared (Kanto)")
            
            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"GWRの実行中にエラーが発生しました: {e}")
        # # 3.2 GWRの実行
        # try:
        #     gwr_selector = Sel_BW(g_coords, g_y, g_X)
        #     gwr_bw = gwr_selector.search()
        #     print(f"GWRの最適なバンド幅: {gwr_bw}")
            
        #     gwr_model = GWR(g_coords, g_y, g_X, gwr_bw, fixed=False)
        #     gwr_results = gwr_model.fit()

        #     # 3.3 結果をGeoDataFrameに追加
        #     # ★飲食店密度の係数のみを追加 (gwr_results.params[:, 1] に格納される)
        #     gdf['gwr_coeff_restaurant'] = gwr_results.params[:, 1] 
        #     gdf['gwr_local_r2'] = gwr_results.localR2 

        #     # =================================================================
        #     # 4. 【飲食店のみ版】結果の可視化
        #     # =================================================================
        #     print("\n--- 4. GWR結果の可視化 ---")
        #     # ★プロットを2つに変更
        #     fig, axes = plt.subplots(1, 2, figsize=(16, 7))

        #     # 可視化1: 飲食店密度の係数
        #     gdf.plot(column='gwr_coeff_restaurant', cmap='coolwarm', legend=True, ax=axes[0])
        #     axes[0].set_title("GWR Coefficient for 'Restaurant Density'")
            
        #     # 可視化2: モデルの当てはまり（局所R2乗値）
        #     gdf.plot(column='gwr_local_r2', cmap='viridis', legend=True, ax=axes[1])
        #     axes[1].set_title("GWR Local R-squared")
            
        #     plt.tight_layout()
        #     plt.show()

        # except Exception as e:
        #     print(f"GWRの実行中にエラーが発生しました: {e}")
            
    except FileNotFoundError as e:
        print(f"\nエラー: 飲食店シェープファイル('restaurants.shp')が見つかりません。")
        print(f"ファイル名とパスを確認してください。 詳細: {e}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
