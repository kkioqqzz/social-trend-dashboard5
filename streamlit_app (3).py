# streamlit_app.py
import streamlit as st
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from instagrapi import Client

# -------------------------
# 페이지 기본 설정
st.set_page_config(page_title="소상공인 트렌드 분석", layout="wide")
st.title("📊 소상공인 트렌드 분석 대시보드")

# -------------------------
# 상태 영역
status_col, info_col = st.columns([2, 5])
with status_col:
    st.subheader("상태")
    n_status = st.empty()
    i_status = st.empty()
with info_col:
    st.subheader("로그")
    if "log_text" not in st.session_state:
        st.session_state.log_text = ""
    log_area = st.text_area(
        "실행 로그 (최근 항목 최상단)",
        value=st.session_state.log_text,
        height=240,
        key="log_text_area",
        disabled=True
    )

# -------------------------
# 로그 함수
def log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    new_entry = f"{timestamp} — {msg}\n"
    st.session_state.log_text = new_entry + st.session_state.log_text
    log_area.text_area(
        "실행 로그 (최근 항목 최상단)",
        value=st.session_state.log_text,
        height=240,
        key="log_text_area",
        disabled=True
    )

# -------------------------
# 플랫폼 선택
platform = st.selectbox("플랫폼 선택", ["네이버 데이터랩", "Instagram"])

# -------------------------
# 키워드 검색
keyword_input = st.text_input("키워드 검색 (예: 아이유, 블랙핑크)")

# -------------------------
# 네이버 데이터랩 트렌드 수집 함수
def get_naver_datalab_trends():
    try:
        url = "https://datalab.naver.com/keyword/realtimeList.naver?entertainment=0&sports=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        keywords = [item.get_text(strip=True) for item in soup.select("div.rank_scroll li span.item_title")]
        ranks = list(range(1, len(keywords)+1))
        df = pd.DataFrame({"순위": ranks, "검색어": keywords})
        log("✅ 네이버 데이터랩 인기검색어 수집 완료")
        return df
    except Exception as e:
        log(f"❌ 네이버 트렌드 수집 오류: {e}")
        return pd.DataFrame()

# -------------------------
# Instagram 데이터 수집 (instagrapi 예제)
def get_instagram_hashtags(username, password, keyword):
    try:
        cl = Client()
        cl.login(username, password)
        results = cl.hashtag_search(keyword)
        df = pd.DataFrame([{"해시태그": r.name, "미디어 수": r.media_count} for r in results])
        log("✅ Instagram 해시태그 수집 완료")
        return df
    except Exception as e:
        log(f"❌ Instagram 수집 오류: {e}")
        return pd.DataFrame()

# -------------------------
# 버튼 클릭 시 데이터 수집
if st.button("데이터 수집 실행"):
    if platform == "네이버 데이터랩":
        df = get_naver_datalab_trends()
        if keyword_input:
            df = df[df['검색어'].str.contains(keyword_input)]
        st.dataframe(df)

    elif platform == "Instagram":
        st.warning("Instagram 로그인 필요")
        insta_id = st.text_input("Instagram ID")
        insta_pw = st.text_input("Instagram PW", type="password")
        if insta_id and insta_pw and keyword_input:
            df = get_instagram_hashtags(insta_id, insta_pw, keyword_input)
            st.dataframe(df)
        else:
            st.info("ID, PW, 키워드를 모두 입력해주세요.")
