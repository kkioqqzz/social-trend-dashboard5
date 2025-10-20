# 1️⃣ 라이브러리 import
import pandas as pd
from pytrends.request import TrendReq
import instaloader
from googleapiclient.discovery import build
import streamlit as st
import plotly.express as px
import time

# 2️⃣ 키워드 & API 설정
hashtags = ["OOTD", "빈티지룩"]  # 원하는 키워드 리스트
youtube_api_key = "여기에_API_KEY_입력"

# -------------------
# 3️⃣ 인스타그램 데이터 수집
L = instaloader.Instaloader()
instagram_data = []

for tag in hashtags:
    try:
        hashtag = instaloader.Hashtag.from_name(L.context, tag)
        instagram_data.append({
            "platform": "Instagram",
            "hashtag": "#"+tag,
            "mentions": hashtag.mediacount
        })
        time.sleep(1)
    except Exception as e:
        print(tag, e)

df_instagram = pd.DataFrame(instagram_data)

# -------------------
# 4️⃣ 구글 트렌드 데이터 수집
pytrends = TrendReq(hl='ko', tz=540)
google_data = []

for tag in hashtags:
    try:
        pytrends.build_payload([tag], cat=0, timeframe='now 7-d', geo='KR', gprop='')
        trend_data = pytrends.interest_over_time()
        mentions = int(trend_data[tag].iloc[-1]) if not trend_data.empty else 0
        google_data.append({
            "platform": "GoogleTrends",
            "hashtag": "#"+tag,
            "mentions": mentions
        })
        time.sleep(1)
    except Exception as e:
        print(f"GoogleTrends {tag} error:", e)
        google_data.append({
            "platform": "GoogleTrends",
            "hashtag": "#"+tag,
            "mentions": 0
        })

df_google = pd.DataFrame(google_data)

# -------------------
# 5️⃣ 유튜브 데이터 수집
youtube = build('youtube', 'v3', developerKey=youtube_api_key)
youtube_data = []

for kw in hashtags:
    try:
        req = youtube.search().list(q=kw, part='snippet', type='video', maxResults=5)
        res = req.execute()
        for item in res['items']:
            video_id = item['id']['videoId']
            stats_req = youtube.videos().list(part='statistics', id=video_id)
            stats_res = stats_req.execute()
            stats = stats_res['items'][0]['statistics']
            youtube_data.append({
                "platform": "YouTube",
                "hashtag": kw,
                "mentions": int(stats.get('viewCount', 0))
            })
        time.sleep(1)
    except Exception as e:
        print(f"YouTube {kw} error:", e)

df_youtube = pd.DataFrame(youtube_data)

# -------------------
# 6️⃣ 데이터 통합 (CSV 없이 바로 사용)
df = pd.concat([df_instagram, df_google, df_youtube], ignore_index=True)

# -------------------
# 7️⃣ Streamlit UI
st.title("Social Trend Dashboard (CSV 없이 안전버전)")

# 플랫폼 선택
platform = st.selectbox("Platform 선택", df['platform'].unique())
df_platform = df[df['platform']==platform]

# TOP N 키워드
st.subheader(f"{platform} TOP 키워드")
top_n = st.slider("몇 개 보여줄까요?", 1, len(df_platform), 3)
top_keywords = df_platform.sort_values("mentions", ascending=False).head(top_n)
st.dataframe(top_keywords)

# 막대그래프
st.subheader("키워드 언급량 비교")
fig = px.bar(top_keywords, x="hashtag", y="mentions", text="mentions")
st.plotly_chart(fig)

# 키워드 검색
st.subheader("키워드 검색")
search = st.text_input("검색어 입력 (# 없이도 가능)").lower()
if search:
    search_df = df_platform[df_platform['hashtag'].str.lower().str.contains(search)]
    if not search_df.empty:
        st.dataframe(search_df)
    else:
        st.write("검색 결과 없음")
