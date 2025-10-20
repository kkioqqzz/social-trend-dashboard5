import pandas as pd
import streamlit as st
import plotly.express as px
import time
import requests
import instaloader
from pytrends.request import TrendReq

st.title("Social Trend Dashboard (Instagram + Google Trends + Naver)")

# -------------------
# 1️⃣ 키워드 및 API 입력
hashtags = ["OOTD", "빈티지룩", "패션스타일", "데일리룩"]

# Instagram 로그인
insta_username = st.text_input("Instagram Username")
insta_password = st.text_input("Instagram Password", type="password")

# Naver API
naver_client_id = st.text_input("Naver Client ID")
naver_client_secret = st.text_input("Naver Client Secret", type="password")

# -------------------
# 2️⃣ Instagram 로그인 및 데이터 수집
st.sidebar.header("Instagram 상태")
instagram_data = []

if insta_username and insta_password:
    try:
        L = instaloader.Instaloader()
        L.login(insta_username, insta_password)
        st.sidebar.success("Instagram 로그인 성공 ✅ 데이터 수집 시작...")
        for tag in hashtags:
            try:
                hashtag = instaloader.Hashtag.from_name(L.context, tag)
                instagram_data.append({
                    "platform": "Instagram",
                    "hashtag": "#"+tag,
                    "mentions": hashtag.mediacount
                })
                time.sleep(1)
            except:
                instagram_data.append({"platform":"Instagram","hashtag":"#"+tag,"mentions":0})
        st.sidebar.info("Instagram 데이터 수집 완료 ✅")
    except Exception as e:
        st.sidebar.error(f"Instagram 로그인 실패 ❌\n사유: {e}")
        instagram_data = [{"platform":"Instagram","hashtag":"#"+tag,"mentions":0} for tag in hashtags]
else:
    instagram_data = [{"platform":"Instagram","hashtag":"#"+tag,"mentions":0} for tag in hashtags]

df_instagram = pd.DataFrame(instagram_data, columns=["platform","hashtag","mentions"])

# -------------------
# 3️⃣ Google Trends 데이터 수집
st.sidebar.header("Google Trends 상태")
google_data = []
try:
    pytrends = TrendReq(hl='ko', tz=540)
    for tag in hashtags:
        try:
            pytrends.build_payload([tag], timeframe='now 7-d', geo='KR')
            trend_data = pytrends.interest_over_time()
            mentions = int(trend_data[tag].iloc[-1]) if not trend_data.empty else 0
            google_data.append({"platform":"GoogleTrends","hashtag":"#"+tag,"mentions":mentions})
            time.sleep(1)
        except Exception as e:
            google_data.append({"platform":"GoogleTrends","hashtag":"#"+tag,"mentions":0})
    st.sidebar.success("Google Trends 데이터 수집 완료 ✅")
except Exception as e:
    st.sidebar.error(f"Google Trends 오류 ❌\n사유: {e}")
    google_data = [{"platform":"GoogleTrends","hashtag":"#"+tag,"mentions":0} for tag in hashtags]

df_google = pd.DataFrame(google_data, columns=["platform","hashtag","mentions"])

# -------------------
# 4️⃣ Naver 데이터 수집
st.sidebar.header("Naver 상태")
naver_data = []

if naver_client_id and naver_client_secret:
    try:
        for kw in hashtags:
            url = "https://openapi.naver.com/v1/search/blog.json"
            headers = {"X-Naver-Client-Id":naver_client_id,"X-Naver-Client-Secret":naver_client_secret}
            params = {"query":kw,"display":1}
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                total_count = int(res.json().get("total",0))
                naver_data.append({"platform":"Naver","hashtag":kw,"mentions":total_count})
            else:
                naver_data.append({"platform":"Naver","hashtag":kw,"mentions":0})
            time.sleep(1)
        st.sidebar.success("Naver 데이터 수집 완료 ✅")
    except Exception as e:
        st.sidebar.error(f"Naver API 호출 실패 ❌\n사유: {e}")
        naver_data = [{"platform":"Naver","hashtag":f"#{tag}","mentions":0} for tag in hashtags]
else:
    naver_data = [{"platform":"Naver","hashtag":f"#{tag}","mentions":0} for tag in hashtags]

df_naver = pd.DataFrame(naver_data, columns=["platform","hashtag","mentions"])

# -------------------
# 5️⃣ 데이터 통합
df = pd.concat([df_instagram, df_google, df_naver], ignore_index=True)

# -------------------
# 6️⃣ Streamlit UI
platform = st.selectbox("Platform 선택", df['platform'].unique())
df_platform = df[df['platform']==platform]

st.subheader(f"{platform} TOP 키워드")
top_n = st.slider("몇 개 보여줄까요?", 1, len(df_platform), 3)
top_keywords = df_platform.sort_values("mentions", ascending=False).head(top_n)
st.dataframe(top_keywords)

st.subheader("키워드 언급량 비교")
fig = px.bar(top_keywords, x="hashtag", y="mentions", text="mentions", color="hashtag")
st.plotly_chart(fig)

st.subheader("키워드 검색")
search = st.text_input("검색어 입력 (# 없이도 가능)").lower()
if search:
    search_df = df_platform[df_platform['hashtag'].str.lower().str.contains(search)]
    if not search_df.empty:
        st.dataframe(search_df)
    else:
        st.write("검색 결과 없음")
