import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pytrends.request import TrendReq
from instagrapi import Client

# --------------------------
# 로그 관리
# --------------------------
if "log_text" not in st.session_state:
    st.session_state.log_text = ""

def log(message):
    st.session_state.log_text = f"{message}\n" + st.session_state.log_text
    st.text_area("실행 로그 (최근 항목 최상단)", value=st.session_state.log_text,
                 height=240, key="log_area", disabled=True)

# --------------------------
# Google Trends 수집
# --------------------------
def get_google_trends(keywords):
    try:
        pytrends = TrendReq(hl='ko', tz=540)
        pytrends.build_payload(keywords, timeframe='today 12-m', geo='KR')
        df = pytrends.interest_over_time()
        if df.empty:
            log("Google Trends: 데이터가 없습니다.")
        return df
    except Exception as e:
        log(f"❌ Google Trends 수집 오류: {e}")
        return pd.DataFrame()

# --------------------------
# Naver 데이터랩 수집
# --------------------------
def get_naver_datalab_trends():
    try:
        url = "https://datalab.naver.com/keyword/realtimeList.naver?where=main"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select("div.keyword_rank ul li a span.title")
        data = [item.get_text(strip=True) for item in items]
        df = pd.DataFrame({"검색어": data})
        log("✅ 네이버 데이터랩 인기검색어 수집 완료")
        return df
    except Exception as e:
        log(f"❌ 네이버 트렌드 수집 오류: {e}")
        return pd.DataFrame()

# --------------------------
# Instagram 로그인 / 2FA
# --------------------------
def insta_login(username, password, two_factor_code=None):
    cl = Client()
    try:
        if two_factor_code:
            cl.login(username, password, verification_code=two_factor_code)
        else:
            cl.login(username, password)
        log("✅ Instagram 로그인 성공")
        return cl
    except Exception as e:
        if "TwoFactorRequired" in str(e) or "ChallengeRequired" in str(e):
            st.session_state.need_2fa = True
            log("🔐 Instagram 2단계 인증 필요")
        else:
            log(f"❌ Instagram 로그인 실패: {e}")
        return None

# --------------------------
# Streamlit UI
# --------------------------
st.title("소상공인 키워드 트렌드 대시보드")

# 플랫폼 선택
platform = st.selectbox("플랫폼 선택", ["Google Trends", "Naver 데이터랩"], key="platform")

# 키워드 입력
keyword_input = st.text_input("검색 키워드 입력", key="keyword_input")

# Instagram 로그인 입력
st.subheader("Instagram 로그인 (선택)")
insta_user = st.text_input("계정", key="insta_user")
insta_pass = st.text_input("비밀번호", type="password", key="insta_pass")

if st.session_state.get("need_2fa", False):
    two_factor_code = st.text_input("2단계 인증 코드", key="insta_2fa")
    if st.button("2FA 제출"):
        insta_login(insta_user, insta_pass, two_factor_code)
else:
    if st.button("Instagram 로그인"):
        insta_login(insta_user, insta_pass)

# 데이터 수집
if st.button("데이터 수집"):
    if platform == "Google Trends":
        df = get_google_trends([keyword_input] if keyword_input else ["키워드"])
    elif platform == "Naver 데이터랩":
        df = get_naver_datalab_trends()
    
    # 키워드 필터링
    if keyword_input and not df.empty:
        df = df[df['검색어'].astype(str).str.contains(keyword_input)]
    
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("데이터가 없습니다.")
