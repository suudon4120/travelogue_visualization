import docx
import re
import pandas as pd

docx_path = 

def extract_events_from_docx(docx_path):
    doc = docx.Document(docx_path)
    full_text = "\n".join(p.text for p in doc.paragraphs)

    # 日付 + イベント抽出
    date_pattern = r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?"
    event_keywords = ["入院", "退院", "手術", "ドレナージ", "発熱", "合併症", "感染", "抗菌薬", "再手術"]

    events = []
    for line in full_text.splitlines():
        for kw in event_keywords:
            if kw in line:
                date_match = re.search(date_pattern, line)
                if date_match:
                    year, month, day = date_match.groups()
                    date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                    events.append({
                        "Event": kw,
                        "Date": date_str,
                        "Text": line.strip()
                    })

    df = pd.DataFrame(events)
    return df

# サンプルデータ
data = {
    "Event": [
        "入院", 
        "診断", 
        "手術", 
        "合併症発生", 
        "ドレナージ処置", 
        "経過観察", 
        "再手術", 
        "回復", 
        "退院"
    ],
    "Start": [
        "2023-04-01", 
        "2023-04-02", 
        "2023-04-05", 
        "2023-04-07", 
        "2023-04-08", 
        "2023-04-10", 
        "2023-04-12", 
        "2023-04-15", 
        "2023-04-20"
    ],
    "End": [
        "2023-04-02", 
        "2023-04-05", 
        "2023-04-07", 
        "2023-04-08", 
        "2023-04-10", 
        "2023-04-12", 
        "2023-04-15", 
        "2023-04-20", 
        "2023-04-21"
    ],
    "Type": [
        "入院", 
        "診断", 
        "手術", 
        "合併症", 
        "処置", 
        "観察", 
        "手術", 
        "回復", 
        "退院"
    ]
}

# DataFrame作成
df = pd.DataFrame(data)

# Timelineプロット
fig = px.timeline(df, x_start="Start", x_end="End", y="Event", color="Type", text="Event")

# 分岐イベントの強調（例：赤）
fig.update_traces(
    marker=dict(color='red'),
    selector=dict(name="合併症")
)


# レイアウト調整
fig.update_layout(
    title="治療経過とプロセスのタイムライン",
    xaxis_title="日付",
    yaxis_title="イベント",
    showlegend=True,
    height=600
)

fig.update_yaxes(categoryorder="total ascending")
fig.show()
