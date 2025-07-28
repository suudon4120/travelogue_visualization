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
from mgwr.gwr import GWR
from mgwr.sel_bw import Sel_BW

# 可視化ライブラリ
import matplotlib.pyplot as plt

def extract_data_from_html(file_path):
    """
    foliumで生成されたHTMLファイルからマーカーとヒートマップのデータを抽出する関数。

    Args:
        file_path (str): HTMLファイルのパス

    Returns:
        list: 抽出された地点データのリスト [lat, lon, emotion_score]
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script')

    all_places = []
    
    # 正規表現パターン
    marker_pattern = re.compile(r"L\.marker\(\s*(\[.*?\]),\s*\{")
    popup_pattern = re.compile(r"<b>タグ別感情スコア:</b><br>(.*?)<hr style='margin: 3px 0;'>", re.DOTALL)
    score_pattern = re.compile(r"\(([\d\.-]+)\)")

    # 感情スコアの平均を計算する補助関数
    def get_avg_score(popup_html):
        scores_html = popup_pattern.search(popup_html)
        if scores_html:
            scores = [float(s) for s in score_pattern.findall(scores_html.group(1))]
            return np.mean(scores) if scores else 0.5 # スコアがなければ中間値0.5
        return 0.5

    # L.markerから緯度経度とポップアップ情報を抽出
    for script in scripts:
        script_text = script.string
        if script_text:
            markers = marker_pattern.finditer(script_text)
            popups = re.finditer(r'var html_.*? = \$\(`(.*?)`\)\[0\];', script_text, re.DOTALL)
            
            # マーカーとポップアップを対応付ける（単純な順序に基づく）
            marker_list = list(markers)
            popup_list = list(popups)
            
            for i in range(min(len(marker_list), len(popup_list))):
                try:
                    lat_lon_str = marker_list[i].group(1)
                    lat, lon = json.loads(lat_lon_str)
                    
                    popup_html = popup_list[i].group(1).replace('\\n', '').replace('\\"', '"')
                    avg_score = get_avg_score(popup_html)
                    
                    all_places.append([lat, lon, avg_score])
                except (json.JSONDecodeError, IndexError):
                    continue
                    
    # L.heatLayerからもデータを抽出
    heat_layer_pattern = re.compile(r"L.heatLayer\(\s*(\[\[.*?\]\]),\s*\{", re.DOTALL)
    heat_match = heat_layer_pattern.search(html_content)
    if heat_match:
        heat_data_str = heat_match.group(1)
        heat_data = json.loads(heat_data_str)
        all_places.extend(heat_data)
        
    # 重複データの削除
    df = pd.DataFrame(all_places, columns=['lat', 'lon', 'emotion_score'])
    df = df.drop_duplicates(subset=['lat', 'lon'])
    
    return df.values.tolist()


# --- メイン処理 ---
# 1. HTMLからデータを抽出
file_path = 'visited_places_map_emotion_batch_output_20250725.html'
data = extract_data_from_html(file_path)

if not data:
    print("HTMLファイルからデータを抽出できませんでした。処理を終了します。")
else:
    print(f"{len(data)}件のユニークな地点データを抽出しました。")
    
    # 2. GeoDataFrameの作成
    df = pd.DataFrame(data, columns=['latitude', 'longitude', 'emotion_score'])
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # 3. 空間的重み行列の作成 (K-Nearest Neighbors, k=8)
    # 点データなので近傍ベースの重み行列を作成します
    weights = KNN.from_dataframe(gdf, k=8)
    weights.transform = 'R' # 標準化

    # 4. 空間的自己相関分析 (Global Moran's I)
    print("\n--- 1. 空間的自己相関分析 (Global Moran's I) ---")
    moran = Moran(gdf['emotion_score'], weights)
    print(f"Moran's I 統計量: {moran.I:.4f}")
    print(f"p値: {moran.p_sim:.4f}")
    if moran.p_sim < 0.05:
        interpretation = "正の相関" if moran.I > 0 else "負の相関"
        print(f"解釈: p値が0.05未満であり、統計的に有意な{interpretation}が見られます。")
        print("感情スコアが高い（低い）地点は、その周辺も高い（低い）傾向があります。")
    else:
        print("解釈: p値が0.05以上であり、感情スコアの空間的な偏りは偶然の範囲内です。")

    # 5. ホットスポット分析 (Getis-Ord Gi*)
    print("\n--- 2. ホットスポット分析 (Getis-Ord Gi*) ---")
    gi = G_Local(gdf['emotion_score'], weights)
    
    # Gi*の結果をDataFrameに追加
    gdf['gi_z_score'] = gi.Zs
    gdf['gi_p_value'] = gi.p_sim

    # ホットスポットとコールドスポットを分類
    hotspots = gdf[(gdf['gi_p_value'] < 0.05) & (gdf['gi_z_score'] > 1.96)]
    coldspots = gdf[(gdf['gi_p_value'] < 0.05) & (gdf['gi_z_score'] < -1.96)]
    
    print(f"ホットスポット（感情がポジティブな場所の集積）の数: {len(hotspots)}")
    print(f"コールドスポット（感情がネガティブな場所の集積）の数: {len(coldspots)}")
    if len(hotspots) > 0:
        print("ホットスポットの代表的な地点（上位5件）:\n", hotspots.sort_values('gi_z_score', ascending=False).head())
    if len(coldspots) > 0:
        print("コールドスポットの代表的な地点（上位5件）:\n", coldspots.sort_values('gi_z_score', ascending=True).head())

    # 6. 地理的加重回帰 (GWR)
    # GWRは目的変数（感情スコア）と説明変数の関係を分析します。
    # 今回のデータには説明変数がないため、デモンストレーションとして、
    # 各地点の「中心からの距離」を仮想的な説明変数として生成します。
    print("\n--- 3. 地理的加重回帰 (GWR) ---")
    print("注意: 説明変数がないため、中心からの距離を仮想的な説明変数として生成し分析します。")

    # 座標をメートル単位に変換 (UTMゾーン54N: EPSG:32654)
    gdf_proj = gdf.to_crs(epsg=32654)
    
    # 目的変数(y)と説明変数(X)の準備
    g_y = gdf_proj['emotion_score'].values.reshape(-1, 1)
    
    # 仮想的な説明変数の生成（データセットの中心点からの距離）
    center_point = gdf_proj.union_all().centroid
    gdf_proj['distance_from_center'] = gdf_proj.geometry.apply(lambda p: p.distance(center_point) / 1000) # km単位
    g_X = gdf_proj[['distance_from_center']].values
    
    # 座標データ
    u = gdf_proj['geometry'].x
    v = gdf_proj['geometry'].y
    g_coords = list(zip(u, v))

    # GWRの最適なバンド幅（近傍数）を探索
    try:
        gwr_selector = Sel_BW(g_coords, g_y, g_X)
        gwr_bw = gwr_selector.search()
        print(f"GWRの最適なバンド幅（近傍点の数）: {gwr_bw}")
        
        # GWRモデルの実行
        gwr_model = GWR(g_coords, g_y, g_X, gwr_bw)
        gwr_results = gwr_model.fit()
        
        print("\nGWRモデルの要約:")
        print(gwr_results.summary())

        # GWRの結果をGeoDataFrameに追加
        gdf['gwr_coeff_dist'] = gwr_results.params[:, 1] # 距離に対する係数
        gdf['gwr_local_r2'] = gwr_results.localR2
        
    except Exception as e:
        print(f"GWRの実行中にエラーが発生しました: {e}")
        print("データポイントが少ないか、共線性などの問題がある可能性があります。")


    # 7. 結果の可視化
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))

    # --- ホットスポット分析の可視化 ---
    ax1 = axes[0]
    # ベースとなる地図をプロット
    gdf.plot(ax=ax1, color='lightgrey', markersize=10, label='Not Significant')

    # 【修正点】ホットスポットが空でない場合のみプロット
    if not hotspots.empty:
        hotspots.plot(ax=ax1, color='red', marker='*', markersize=100, label='Hot Spot (Positive)')

    # 【修正点】コールドスポットが空でない場合のみプロット
    if not coldspots.empty:
        coldspots.plot(ax=ax1, color='blue', marker='v', markersize=80, label='Cold Spot (Negative)')

    ax1.set_title("Hotspot Analysis (Getis-Ord Gi*) Results")
    ax1.legend()
    ax1.set_xlabel("Longitude")
    ax1.set_ylabel("Latitude")

    # --- GWRの係数（中心からの距離の影響度）の可視化 ---
    ax2 = axes[1]
    if 'gwr_coeff_dist' in gdf.columns:
        gdf.plot(column='gwr_coeff_dist', ax=ax2, legend=True, cmap='viridis')
        ax2.set_title("GWR Coefficients for 'Distance from Center'")
    else:
        # GWR分析が失敗した場合の表示
        ax2.text(0.5, 0.5, 'GWR analysis failed or was not performed.', 
                ha='center', va='center', transform=ax2.transAxes)
        ax2.set_title("GWR Coefficients")

    ax2.set_xlabel("Longitude")
    ax2.set_ylabel("Latitude")

    plt.tight_layout()
    plt.show()