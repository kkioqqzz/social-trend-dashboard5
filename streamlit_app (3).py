
import streamlit as st
import pandas as pd
import plotly.express as px

# 데이터 로드
df = pd.read_csv("social_trends_mvp.csv")

st.title("Social Trend Dashboard (MVP) - 소상공인용")

# 플랫폼 선택
platform = st.selectbox("Platform 선택", df['platform'].unique())
df_platform = df[df['platform']==platform]

# TOP N 키워드
st.subheader(f"{platform} TOP 키워드")
top_n = st.slider("몇 개 보여줄까요?", 1, len(df_platform), 3)
top_keywords = df_platform.sort_values("mentions", ascending=False).head(top_n)
st.dataframe(top_keywords)

# 막대그래프: mentions 비교
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
