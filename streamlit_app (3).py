# streamlit_app.py
import os
import time
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# --- optional imports that might fail in restricted envs; we'll import lazily where needed
# from pytrends.request import TrendReq
# import instaloader

# -------------------------
# 환경 감지
IS_CLOUD = os.getenv("IS_STREAMLIT_CLOUD", "False") == "True"

# -------------------------
st.set_page_config(page_title="Social Trend Dashboard", layout="wide")
st.title("Social Trend Dashboard — GoogleTrends + Naver + Instagram (안정 버전)")

# -------------------------
# 입력: 키워드 리스트 (사용자가 편집 가능)
with st.expander("🔧 분석 키워드 (편집 가능)", expanded=True):
    default_keywords = ["OOTD", "빈티지룩", "패션스타일", "데일리룩"]
    keywords_text = st.text_area("키워드를 쉼표로 구분해 입력하세요 (한국어/영어 혼합 가능)", 
                                 value=",".join(default_keywords), height=80)
    # normalize into cleaned list (no leading/trailing spaces)
    keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
    st.write(f"키워드 개수: {len(keywords)}")

# -------------------------
# 입력: 인증 정보 (로컬에서만 실제로 사용 권장)
st.sidebar.header("인증 & 실행")
st.sidebar.markdown("**로컬 테스트 권장**: Instagram 로그인/네이버 API는 로컬 환경에서 실제 동작 확인하세요.")
insta_username = st.sidebar.text_input("Instagram username (옵션, 로컬에서만 로그인)", value="", key="insta_user")
insta_password = st.sidebar.text_input("Instagram password (옵션, 로컬에서만 로그인)", value="", type="password", key="insta_pwd")

naver_client_id = st.sidebar.text_input("Naver Client ID (옵션)", value="", key="naver_id")
naver_client_secret = st.sidebar.text_input("Naver Client Secret (옵션)", value="", type="password", key="naver_secret")

# 자동 수집 옵션
auto_collect_after_auth = st.sidebar.checkbox("로그인/인증 성공 시 자동으로 데이터 수집", value=True)

# 실행 버튼
collect_button = st.sidebar.button("🔁 데이터 수집 실행")

# 상태 영역
status_col, info_col = st.columns([2, 5])
with status_col:
    st.subheader("상태")
    g_status = st.empty()
    n_status = st.empty()
    i_status = st.empty()
with info_col:
    st.subheader("로그")
    log_area = st.empty()

# small helper for logging
def log(msg):
    existing = log_area.text_area("실행 로그 (최근 항목 최상단)", value="", height=240)
    # append on top
    log_area.text_area("실행 로그 (최근 항목 최상단)", value=f"{time.strftime('%Y-%m-%d %H:%M:%S')} — {msg}\n{existing}", height=240)

# -------------------------
# 데이터 수집 함수들 (안정성 보장)
def collect_google_trends(keywords):
    """
    한 번에 키워드 묶어서 요청. 실패 시 예외 메시지 반환.
    반환: list of dict {'platform','hashtag','mentions'}
    """
    try:
        from pytrends.request import TrendReq
    except Exception as e:
        raise RuntimeError(f"pytrends import 실패: {e}")

    if not keywords:
        return []
    results = []
    try:
        pytrends = TrendReq(hl='ko', tz=540)
        # 구글은 최대 5개 묶어서 비교 가능 => 여기서는 길이 조절
        # If more than 5 keywords, chunk them.
        CHUNK = 5
        for i in range(0, len(keywords), CHUNK):
            chunk = keywords[i:i+CHUNK]
            # build payload and fetch interest_over_time
            pytrends.build_payload(chunk, timeframe='now 7-d', geo='KR')
            df = pytrends.interest_over_time()
            # df may be empty -> set 0
            for kw in chunk:
                if kw in df.columns and not df.empty:
                    val = int(df[kw].iloc[-1])
                else:
                    val = 0
                results.append({"platform":"GoogleTrends", "hashtag":f"#{kw}", "mentions": val})
            time.sleep(1.1)  # rate limit breathing room
    except Exception as e:
        # bubble up with readable message
        raise RuntimeError(f"Google Trends 수집 실패: {e}")
    return results

def collect_naver_blog_counts(keywords, client_id, client_secret):
    """
    네이버 블로그 검색 API로 total(검색결과 개수)을 가져옴.
    반환: list of dict
    """
    results = []
    if not client_id or not client_secret:
        # no credentials -> return zeros but don't raise
        for kw in keywords:
            results.append({"platform":"Naver", "hashtag":f"#{kw}", "mentions":0})
        return results

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    url = "https://openapi.naver.com/v1/search/blog.json"
    for kw in keywords:
        try:
            params = {"query": kw, "display": 1}
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                j = r.json()
                total = int(j.get("total", 0))
                results.append({"platform":"Naver", "hashtag":f"#{kw}", "mentions": total})
            else:
                results.append({"platform":"Naver", "hashtag":f"#{kw}", "mentions": 0})
                log(f"Naver API 호출 실패: 키워드={kw}, status={r.status_code}, body={r.text}")
            time.sleep(1)  # polite
        except Exception as e:
            results.append({"platform":"Naver", "hashtag":f"#{kw}", "mentions": 0})
            log(f"Naver 예외: {e} (키워드={kw})")
    return results

def collect_instagram_counts(keywords, username=None, password=None):
    """
    Instaloader를 사용하여 해시태그의 mediacount를 가져온다.
    - 로그인 정보가 있으면 (로컬에서만) 로그인 시도
    - 실패하면 0으로 처리
    """
    results = []
    try:
        import instaloader
    except Exception as e:
        # instaloader가 없으면 0 대체
        log(f"Instaloader import 실패: {e}")
        for kw in keywords:
            results.append({"platform":"Instagram", "hashtag":f"#{kw}", "mentions":0})
        return results

    L = instaloader.Instaloader()
    logged_in = False
    # only attempt login if credentials provided and NOT running in Cloud
    if username and password and not IS_CLOUD:
        try:
            L.login(username, password)
            logged_in = True
            i_status.success("Instagram 로그인 성공 — 데이터 수집 시작")
        except Exception as e:
            i_status.error(f"Instagram 로그인 실패: {e}")
            log(f"Instagram 로그인 오류: {e}")
            logged_in = False

    for kw in keywords:
        try:
            # pass tag name without '#'
            tagname = kw
            hashtag = instaloader.Hashtag.from_name(L.context, tagname)
            count = int(hashtag.mediacount) if hasattr(hashtag, "mediacount") else 0
            results.append({"platform":"Instagram", "hashtag":f"#{kw}", "mentions": count})
            time.sleep(0.8)
        except Exception as e:
            # often fails in Cloud or under checkpoint -> fallback 0 and log reason
            results.append({"platform":"Instagram", "hashtag":f"#{kw}", "mentions": 0})
            log(f"Instagram 해시태그 수집 오류 (#{kw}): {e}")
    return results

# -------------------------
# 수집 실행 로직 (한 곳에서 제어)
def run_collection():
    g_status.info("Google Trends: 수집 중...")
    n_status.info("Naver: 수집 중...")
    i_status.info("Instagram: 수집 중 (공개 데이터 우선)...")
    log("데이터 수집 시작")

    # Google Trends
    google_results = []
    try:
        google_results = collect_google_trends(keywords)
        g_status.success("Google Trends: 수집 완료")
        log("Google Trends 수집 성공")
    except Exception as e:
        g_status.error(f"Google Trends 오류: {e}")
        log(f"Google Trends 오류: {e}")
        # fallback zeros
        google_results = [{"platform":"GoogleTrends","hashtag":f"#{kw}","mentions":0} for kw in keywords]

    # Naver
    try:
        naver_results = collect_naver_blog_counts(keywords, naver_client_id, naver_client_secret)
        n_status.success("Naver: 수집 완료")
        log("Naver 수집 완료")
    except Exception as e:
        n_status.error(f"Naver 오류: {e}")
        log(f"Naver 오류: {e}")
        naver_results = [{"platform":"Naver","hashtag":f"#{kw}","mentions":0} for kw in keywords]

    # Instagram
    try:
        insta_results = collect_instagram_counts(keywords, insta_username if insta_username else None, insta_password if insta_password else None)
        i_status.success("Instagram: 수집 완료 (오류 발생 시 0 처리)")
        log("Instagram 수집 완료")
    except Exception as e:
        i_status.error(f"Instagram 오류: {e}")
        log(f"Instagram 전체 수집 오류: {e}")
        insta_results = [{"platform":"Instagram","hashtag":f"#{kw}","mentions":0} for kw in keywords]

    # 합치기
    df = pd.concat([pd.DataFrame(insta_results), pd.DataFrame(google_results), pd.DataFrame(naver_results)], ignore_index=True)
    # 보장: 컬럼 확실히 존재
    if "platform" not in df.columns or "hashtag" not in df.columns or "mentions" not in df.columns:
        st.error("데이터프레임 컬럼 이상 — 수집 실패")
        log(f"데이터프레임 컬럼 이상: {df.columns}")
        return pd.DataFrame(columns=["platform","hashtag","mentions"])
    # 정렬, 타입 보정
    df["mentions"] = pd.to_numeric(df["mentions"], errors="coerce").fillna(0).astype(int)
    return df

# -------------------------
# 자동/수동 수집 트리거
if "collected_df" not in st.session_state:
    st.session_state.collected_df = None

# If user pressed collect button -> run
if collect_button:
    st.session_state.collected_df = run_collection()
else:
    # auto collect if user requested auto and provided at least one credential or not cloud
    # We do not auto run on Cloud to avoid quota issues unless user explicitly presses
    if auto_collect_after_auth and not IS_CLOUD and (insta_username and insta_password or (naver_client_id and naver_client_secret)):
        # run once automatically (but avoid continuous loops) — set a flag
        if not st.session_state.get("auto_ran", False):
            st.session_state.collected_df = run_collection()
            st.session_state.auto_ran = True

# If still None, show placeholder sample data so UI doesn't break
if st.session_state.collected_df is None:
    st.info("아직 데이터가 수집되지 않았습니다. 좌측 '데이터 수집 실행' 버튼을 누르거나 인증 정보를 입력하고 자동 수집 옵션을 사용하세요.")
    # show a small sample so UI behaves
    sample_insta = [{"platform":"Instagram","hashtag":"#OOTD","mentions":12000},
                    {"platform":"Instagram","hashtag":"#빈티지룩","mentions":8000}]
    sample_google = [{"platform":"GoogleTrends","hashtag":"#OOTD","mentions":90},
                     {"platform":"GoogleTrends","hashtag":"#빈티지룩","mentions":75}]
    sample_naver = [{"platform":"Naver","hashtag":"#OOTD","mentions":4300},
                    {"platform":"Naver","hashtag":"#빈티지룩","mentions":2100}]
    df = pd.concat([pd.DataFrame(sample_insta), pd.DataFrame(sample_google), pd.DataFrame(sample_naver)], ignore_index=True)
else:
    df = st.session_state.collected_df

# -------------------------
# UI: 플랫폼 선택, TOP N, 검색 (검색은 # 유무, 대소문자 무시)
st.markdown("---")
left, right = st.columns([3,2])

with left:
    st.subheader("트렌드 요약")
    platform = st.selectbox("Platform 선택", options=sorted(df['platform'].unique()))
    df_platform = df[df['platform'] == platform].copy()
    if df_platform.empty:
        st.warning(f"{platform} 데이터가 비어 있습니다.")
    else:
        st.write(f"총 키워드 수: {len(df_platform)}")

    # TOP N
    top_n = st.slider("TOP N 개수 선택", min_value=1, max_value=max(1, len(df_platform)), value=min(3, max(1, len(df_platform))))
    top_keywords = df_platform.sort_values("mentions", ascending=False).head(top_n).reset_index(drop=True)
    st.dataframe(top_keywords)

    # 그래프
    st.subheader("시각화")
    if not top_keywords.empty:
        fig = px.bar(top_keywords, x="hashtag", y="mentions", text="mentions", color="hashtag")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("시각화할 데이터가 없습니다.")

with right:
    st.subheader("키워드 검색")
    search_input = st.text_input("검색어 입력 (# 없이도 가능)").strip().lower()
    if search_input:
        # normalize hashtag column: lower, remove leading '#'
        temp = df_platform.copy()
        temp['_normalized'] = temp['hashtag'].astype(str).str.lower().str.lstrip('#')
        matched = temp[temp['_normalized'].str.contains(search_input, na=False)]
        if not matched.empty:
            st.dataframe(matched.drop(columns=['_normalized']))
        else:
            st.write("검색 결과 없음")

# -------------------------
st.markdown("---")
st.caption("노트: Google Trends와 Naver API는 요청 제한/쿼터가 있을 수 있습니다. 많은 키워드를 자주 요청하면 차단될 수 있으니 주의하세요.")
