import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
# 以前のコードから必要な関数をすべてコピーしてくる
from travelogue import (
    geocode_place, geocode_gsi, map_emotion_and_routes, 
    LayerToggleButtons, get_image_as_base64,
    get_visit_hint,
    TAG_TO_IMAGE, TAG_PRIORITY, DEFAULT_ICON_IMAGE, TAG_TO_GIF,
    COLORS, base_name, MAX_DISTANCE_KM
)

# --- 設定 ---
load_dotenv()
client = OpenAI()

def main():
    """メイン処理：バッチ結果のダウンロード、ジオコーディング、地図生成"""
    batch_job_id = input("ステージ1で取得したBatch Job IDを入力してください: ").strip()
    if not batch_job_id:
        print("IDが入力されていません。")
        return

    print(f"\nバッチジョブの状態を確認します: {batch_job_id}")
    try:
        while True:
            batch_job = client.batches.retrieve(batch_job_id)
            print(f"現在の状態: {batch_job.status}...")
            if batch_job.status in ['completed', 'failed', 'cancelled']:
                break
            time.sleep(30)

        if batch_job.status != 'completed':
            print(f"[ERROR] バッチ処理が成功しませんでした。状態: {batch_job.status}")
            if batch_job.error_file_id:
                print(f"エラーファイルID: {batch_job.error_file_id}")
            return

        print("✅ バッチ処理が完了しました。結果をダウンロードします。")
        output_file_id = batch_job.output_file_id
        result_content = client.files.content(output_file_id).text

        results_by_id = {}
        for line in result_content.strip().split('\n'):
            ### ★★★ ここからが修正箇所です ★★★
            try:
                data = json.loads(line)
                custom_id = data['custom_id']
                
                # レスポンスが成功しているか確認
                if data.get('response') and data['response']['status_code'] == 200:
                    response_body = data['response']['body']
                    # GPTが生成したJSONコンテンツをさらにパース
                    # この内側のパースでエラーが発生する可能性がある
                    content = json.loads(response_body['choices'][0]['message']['content'])
                    results_by_id[custom_id] = content
                else:
                    print(f"[WARNING] ID {custom_id} のリクエストでAPIエラーが発生しました。スキップします。")
            except json.JSONDecodeError as e:
                # 壊れたJSONが原因でパースに失敗した場合
                print(f"[WARNING] 1件のバッチ結果の解析に失敗しました。この結果をスキップします。エラー: {e}")
                # ループは中断せず、次の行の処理に進む
                continue
            ### ★★★ 修正ここまで ★★★


        print(f"✅ {len(results_by_id)}件の結果を正常にパースしました。")
        print("\nジオコーディングと最終データ構築を開始します...")
        all_travels_data = []
        for i, (file_num, result_data) in enumerate(results_by_id.items()):
            print(f"\n--- [{file_num}] の後処理を開始 ---")
            events = result_data.get("events", [])
            if not events: continue

            # get_visit_hintをここで呼び出し、region_hintを取得
            full_text_for_hint = " ".join([e.get('experience','') for e in events])
            region_hint = get_visit_hint(full_text_for_hint)

            stop_events = [e for e in events if e.get('type') == 'stop']
            for stop_event in stop_events:
                place_name = stop_event.get('place')
                if not place_name: continue
                
                ### ★★★ ここからが修正箇所です ★★★
                coords = None
                context_hint = stop_event.get('location_context', region_hint)
                
                # 1. Geopy
                coords = geocode_place(place_name, context_hint)
                
                # 2. GPTの推定座標 (有効な数値か厳密にチェック)
                if not coords:
                    gpt_lat = stop_event.get('latitude')
                    gpt_lon = stop_event.get('longitude')
                    # 両方がNoneでなく、かつ数値であることを確認
                    if gpt_lat is not None and gpt_lon is not None and isinstance(gpt_lat, (int, float)) and isinstance(gpt_lon, (int, float)):
                        # (0,0)は無効とみなす
                        if gpt_lat != 0.0 or gpt_lon != 0.0:
                            coords = (gpt_lat, gpt_lon)
                
                # 3. 国土地理院API
                if not coords:
                    coords = geocode_gsi(place_name)
                
                if coords:
                    stop_event['latitude'] = coords[0]
                    stop_event['longitude'] = coords[1]
                else:
                    print(f"[!] 全てのジオコーディングに失敗しました: {place_name}")
                    # 失敗した場合、座標キーを確実に削除する
                    if 'latitude' in stop_event: del stop_event['latitude']
                    if 'longitude' in stop_event: del stop_event['longitude']
                ### ★★★ 修正ここまで ★★★

            all_travels_data.append({
                "file_num": file_num,
                "events": events,
                "color": COLORS[i % len(COLORS)],
                "region_hint": region_hint
            })

        # 地図生成
        if all_travels_data:
            ### ★★★ ここが修正箇所です ★★★
            # 現在時刻からタイムスタンプ文字列を生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # タイムスタンプをファイル名に含める
            output_filename = f"{base_name}batch_{timestamp}.html"
            
            print(f"\n🗺️ {len(all_travels_data)}件の旅行記データで地図を生成します...")
            map_emotion_and_routes(all_travels_data, output_filename)
            ### ★★★ 修正ここまで ★★★
        else:
            print("\n地図を生成するための有効なデータがありませんでした。")

    except Exception as e:
        print(f"[FATAL ERROR] 処理中にエラーが発生しました: {e}")

if __name__ == '__main__':
    main()