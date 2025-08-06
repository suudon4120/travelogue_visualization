import geopandas as gpd

# あなたがQGISで変換したシェープファイルのパスを指定
shapefile_path = "./shapefiles/osm_japan_pois_restaurant.shp" # ファイル名は適宜修正してください

try:
    # ファイルを読み込んで、列名とデータの先頭5行を表示
    osm_data = gpd.read_file(shapefile_path, encoding='cp932')
    
    print("-----------------------------------------")
    print("シェープファイルに含まれる列名の一覧:")
    print(osm_data.columns)
    print("-----------------------------------------")
    print("\nデータの先頭5行のサンプル:")
    print(osm_data.head())
    print("-----------------------------------------")

except FileNotFoundError:
    print(f"エラー: ファイルが見つかりません。パスを確認してください: {shapefile_path}")
except Exception as e:
    print(f"エラーが発生しました: {e}")