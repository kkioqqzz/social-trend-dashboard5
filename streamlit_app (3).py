import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from pytrends.request import TrendReq
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired, LoginRequired

# -----------------------------
# 세션 상태 초기화
# -----------------------------
for key in [
    "log_text", "insta_id", "insta_pw", "two_factor_code", 
    "insta_2fa_required", "insta_login_success", "insta_client"
]:
    if key not in st.session_state:
        st.session_state[key] = "" if "text" in key or "id" in key or "pw" in key else False

# -----------------------------
# 로그 함수
# -----------------------------
def log(message):
    st.session_state.log_text = f"{time.strftime('%Y-%m-%d %H:%M:%S')} — {message}\n" + st.session_state.log_text
    st.text_area("실행 로그 (최근 항목 최상단)", value=st.session_state.log_text, height=240, disabled=True, key="log_area")

# -----------------------------
# 플랫폼 선택
# -----------------------------
platform = st.selectbox("플랫폼 선택", ["Google Trends", "Naver 데이터랩", "Instagram"], key="platform_select")
keyword_input = st.text_input("검색 키워드 (선택)", key="keyword_input")

# -----------------------------
# Google Trends 수집
# -----------------------------
def get_google_trends(keywords):
    pytrends = TrendReq(hl='ko', tz=540)
    try:
        pytrends.build_payload(keywords, timeframe='today 12-m', geo='KR')
        trend_data = pytrends.interest_over_time()
        if trend_data.empty:
            log("⚠️ Google Trends: 수집된 데이터 없음")
            return pd.DataFrame()
        trend_data = trend_data.reset_index().rename(columns={"date": "날짜"})
        log("✅ Google Trends 수집 완료 (최근 12개월)")
        return trend_data
    except Exception as e:
        log(f"❌ Google Trends 수집 오류: {e}")
        return pd.DataFrame()

# -----------------------------
# Naver 데이터랩 수집
# -----------------------------
def get_naver_datalab_trends():
    try:
        url = "https://datalab.naver.com/keyword/realtimeList.naver?entertainment=0&sports=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        keywords = [item.get_text(strip=True) for item in soup.select("div.keyword_rank ul li a span.title")]
        if not keywords:
            log("⚠️ 네이버 데이터랩: 인기검색어 수집 결과 없음")
            return pd.DataFrame()
        df = pd.DataFrame({"순위": range(1, len(keywords)+1), "검색어": keywords})
        log("✅ 네이버 데이터랩 인기검색어 수집 완료")
        return df
    except Exception as e:
        log(f"❌ 네이버 트렌드 수집 오류: {e}")
        return pd.DataFrame()

# -----------------------------
# Instagram 로그인 및 인증
# -----------------------------
def insta_login(insta_id, insta_pw, code=None):
    cl = Client()
    try:
        if code:
            cl.two_factor_login(code)
            st.session_state.insta_login_success = True
            st.session_state.insta_2fa_required = False
            st.session_state.insta_client = cl
            log("✅ Instagram 인증 완료")
            st.experimental_rerun()
        else:
            cl.login(insta_id, insta_pw)
            st.session_state.insta_client = cl
            st.session_state.insta_login_success = True
            st.session_state.insta_2fa_required = False
            log("✅ Instagram 로그인 성공")
    except TwoFactorRequired:
        st.session_state.insta_2fa_required = True
        st.warning("⚠️ 2단계 인증 필요: 앱에서 6자리 코드를 확인하고 입력해주세요.")
        st.session_state.insta_client = cl
    except ChallengeRequired:
        st.session_state.insta_2fa_required = True
        st.warning("⚠️ 이메일 인증 필요: 메일에서 받은 6자리 코드를 입력해주세요.")
        st.session_state.insta_client = cl
    except LoginRequired as e:
        st.session_state.insta_login_success = False
        log(f"❌ Instagram 로그인 실패: {e}")
    except Exception as e:
        st.session_state.insta_login_success = False
        log(f"❌ Instagram 로그인 오류: {e}")

# -----------------------------
# Instagram 입력창 및 2FA 처리
# -----------------------------
if platform == "Instagram":
    st.session_state.insta_id = st.text_input("Instagram ID", value=st.session_state.insta_id, key="insta_id_input")
    st.session_state.insta_pw = st.text_input("Instagram PW", type="password", value=st.session_state.insta_pw, key="insta_pw_input")
    
    if st.button("Instagram 로그인 시도", key="insta_login_btn"):
        insta_login(st.session_state.insta_id, st.session_state.insta_pw)
    
    if st.session_state.insta_2fa_required:
        st.session_state.two_factor_code = st.text_input("인증 코드 입력 (2FA 또는 이메일)", max_chars=6, value=st.session_state.two_factor_code, key="insta_2fa_input")
        if st.button("인증 코드 제출", key="insta_2fa_submit") and st.session_state.two_factor_code:
            insta_login(st.session_state.insta_id, st.session_state.insta_pw, st.session_state.two_factor_code)

# -----------------------------
# 데이터 수집 실행
# -----------------------------
if st.button("데이터 수집 실행", key="collect_btn"):
    df = pd.DataFrame()
    if platform == "Google Trends":
        if keyword_input:
            df = get_google_trends([keyword_input])
        else:
            st.info("⚠️ 키워드를 입력해주세요")
    elif platform == "Naver 데이터랩":
        df = get_naver_datalab_trends()
        if keyword_input and not df.empty:
            df = df[df['검색어'].astype(str).str.contains(keyword_input)]
    
    if platform != "Instagram":
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("데이터가 없습니다.")
