# streamlit_app.py
import streamlit as st
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from instagrapi import Client
from pytrends.request import TrendReq

# -------------------------
# 페이지 설정
st.set_page_config(page_title="소상공인 트렌드 분석", layout="wide")
st.title("📊 소상공인 트렌드 분석 대시보드")

# -------------------------
# 세션 상태 초기화
if "log_text" not in st.session_state:
    st.session_state.log_text = ""

# -------------------------
# 로그 함수
def log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    st.session_state.log_text = f"{timestamp} — {msg}\n" + st.session_state.log_text
    st.text_area(
        "실행 로그 (최근 항목 최상단)",
        value=st.session_state.log_text,
        height=240,
        key="log_text_area",
        disabled=True
    )

# -------------------------
# 플랫폼 선택
platform = st.selectbox("플랫폼 선택", ["네이버 데이터랩", "Instagram", "Google Trends"])

# -------------------------
# 키워드 검색 입력
keyword_input = st.text_input("키워드 검색 (예: 아이유, 블랙핑크)")

# -------------------------
# Instagram ID/PW 입력 (항상 렌더링)
insta_id = st.text_input("Instagram ID")
insta_pw = st.text_input("Instagram PW", type="password")

# -------------------------
# 네이버 데이터랩 수집
def get_naver_datalab_trends():
    try:
        url = "https://datalab.naver.com/keyword/realtimeList.naver?entertainment=0&sports=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        keywords = [item.get_text(strip=True) for item in soup.select("div.rank_scroll li span.item_title")]
        if not keywords:
            log("⚠️ 네이버 데이터랩: 인기검색어 수집 결과 없음")
            return pd.DataFrame()
        ranks = list(range(1, len(keywords)+1))
        df = pd.DataFrame({"순위": ranks, "검색어": keywords})
        log("✅ 네이버 데이터랩 인기검색어 수집 완료")
        return df
    except Exception as e:
        log(f"❌ 네이버 트렌드 수집 오류: {e}")
        return pd.DataFrame()

# -------------------------
# Instagram 해시태그 수집
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
# Google Trends 수집 (재시도 로직)
def get_google_trends(keyword_list, retries=3):
    try:
        pytrends = TrendReq(hl='ko', tz=540)
        for attempt in range(retries):
            try:
                pytrends.build_payload(keyword_list, timeframe='now 7-d', geo='KR')
                df = pytrends.interest_over_time().reset_index()
                if df.empty:
                    log("⚠️ Google Trends: 빈 데이터 발생")
                else:
                    log("✅ Google Trends 수집 완료")
                return df
            except Exception as e_inner:
                log(f"⚠️ Google Trends 요청 실패, 재시도 {attempt+1}/{retries}: {e_inner}")
                time.sleep(2)  # 잠시 대기 후 재시도
        return pd.DataFrame()
    except Exception as e:
        log(f"❌ Google Trends 최종 오류: {e}")
        return pd.DataFrame()

# -------------------------
# 데이터 수집 버튼
if st.button("데이터 수집 실행"):
    if platform == "네이버 데이터랩":
        df = get_naver_datalab_trends()
        if not df.empty and keyword_input:
            df = df[df['검색어'].astype(str).str.contains(keyword_input)]
        st.dataframe(df)

    elif platform == "Instagram":
        if insta_id and insta_pw and keyword_input:
            df = get_instagram_hashtags(insta_id, insta_pw, keyword_input)
            st.dataframe(df)
        else:
            st.info("ID, PW, 키워드를 모두 입력해주세요.")

    elif platform == "Google Trends":
        if keyword_input:
            df = get_google_trends([keyword_input])
            st.dataframe(df)
        else:
            st.info("키워드를 입력해주세요.")
