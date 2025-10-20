import pandas as pd
import streamlit as st
import plotly.express as px
import time
import os

# 로컬/Cloud 구분
IS_CLOUD = "IS_STREAMLIT_CLOUD" in os.environ

# 키워드 및 API 설정
hashtags = ["OOTD", "빈티지룩", "패션스타일", "데일리룩"]
youtube_api_key = "여기에_API_KEY_입력"

st.title("Social Trend Dashboard (로컬+Cloud 겸용)")

# -------------------
# 1️⃣ Instagram 데이터 수집
instagram_data = []

if not IS_CLOUD:
    try:
        import instaloader
        L = instaloader.Instaloader()
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
    except Exception as e:
        print("Instaloader error:", e)

# Cloud 또는 실패 시 샘플 데이터
if not instagram_data:
    instagram_data = [{"platform": "Instagram", "hashtag": f"#{tag}", "mentions": (i+1)*100} 
                      for i, tag in enumerate(hashtags)]

df_instagram = pd.DataFrame(instagram_data)

# -------------------
# 2️⃣ Google Trends 데이터 수집
google_data = []

if not IS_CLOUD:
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='ko', tz=540)
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
    except Exception as e:
        print("Pytrends error:", e)

# Cloud 또는 실패 시 샘플 데이터
if not google_data:
    google_data = [{"platform": "GoogleTrends", "hashtag": f"#{tag}", "mentions": (i+1)*80} 
                   for i, tag in enumerate(hashtags)]

df_google = pd.DataFrame(google_data)

# -------------------
# 3️⃣ YouTube 데이터 수집
youtube_data = []

if not IS_CLOUD:
    try:
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        for kw in hashtags:
            try:
                req = youtube.search().list(q=kw, part='snippet', type='video', maxResults=3)
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
    except Exception as e:
        print("YouTube API error:", e)

# Cloud 또는 실패 시 샘플 데이터
if not youtube_data:
    youtube_data = [{"platform": "YouTube", "hashtag": f"#{tag}", "mentions": (i+1)*50} 
                    for i, tag in enumerate(hashtags)]

df_youtube = pd.DataFrame(youtube_data)

# -------------------
# 4️⃣ 데이터 통합
df = pd.concat([df_instagram, df_google, df_youtube], ignore_index=True)

# -------------------
# 5️⃣ Streamlit UI
platform = st.selectbox("Platform 선택", df['platform'].unique())
df_platform = df[df['platform']==platform]

# TOP N
st.subheader(f"{platform} TOP 키워드")
top_n = st.slider("몇 개 보여줄까요?", 1, len(df_platform), 3)
top_keywords = df_platform.sort_values("mentions", ascending=False).head(top_n)
st.dataframe(top_keywords)

# 막대그래프
st.subheader("키워드 언급량 비교")
fig = px.bar(top_keywords, x="hashtag", y="mentions", text="mentions", color="hashtag")
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
