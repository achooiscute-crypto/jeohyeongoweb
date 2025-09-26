# streamlit_app.py
import streamlit as st
import requests
import os

BACKEND = os.getenv("BACKEND_BASE_URL", "http://localhost:5000")

st.set_page_config(page_title="학교 스탬프 앱")

st.title("학교 스탬프 도장판")

# 로그인 버튼 (로그인 흐름은 백엔드에서 수행)
if st.button("구글로 로그인 (학교 계정)"):
    st.write("로그인 창을 엽니다...")
    st.markdown(f"[로그인하러 가기]({BACKEND}/login)")

# 로그아웃 버튼
if st.button("로그아웃"):
    # 로그아웃은 브라우저에서 백엔드 /logout 호출
    res = requests.get(f"{BACKEND}/logout")
    if res.status_code == 200:
        st.success("로그아웃 되었습니다. 페이지를 새로고침하세요.")

# 현재 유저 정보 요청
whoami = None
try:
    res = requests.get(f"{BACKEND}/whoami", timeout=3)
    if res.status_code == 200:
        whoami = res.json()
    else:
        whoami = None
except Exception:
    whoami = None

if not whoami:
    st.info("로그인이 필요합니다. 위의 로그인 버튼을 누르세요.")
    st.stop()

# 로그인된 경우 UI
st.subheader(f"{whoami.get('displayName')} ({whoami.get('email')})")
claims = whoami.get("claims", {})
role = claims.get("role", whoami.get("profile", {}).get("role", "student"))
st.write("권한:", role)

# username(아이디) 변경 UI (학생 포함 모두 가능)
profile = whoami.get("profile", {})
current_username = profile.get("username", "")
new_username = st.text_input("아이디(공개명) 설정", value=current_username)
if st.button("아이디 저장"):
    # 단순히 Firestore profile 업데이트용 엔드포인트가 없다면,
    # 여기에 /update_profile 같은 엔드포인트를 만들어 호출하는 편이 좋음.
    # 예시로 직접 Firestore 수정 엔드포인트를 만들지 않았으므로 경고만 표시합니다.
    st.info("이 예제는 프론트엔드 예시입니다. 백엔드에 /update_profile 엔드포인트를 추가하여 저장하세요.")

# 스탬프 찍기 (leader/admin 전용)
if role in ("leader", "admin"):
    st.markdown("---")
    st.subheader("스탬프 찍기")
    target_email = st.text_input("학생 이메일 (예: 2411224@jeohyeon.hs.kr)")
    note = st.text_input("메모 (선택)")
    if st.button("스탬프 찍기"):
        payload = {"target_email": target_email, "note": note, "board_id": "default_board"}
        r = requests.post(f"{BACKEND}/stamp", json=payload)
        if r.status_code == 201:
            st.success("스탬프를 찍었습니다.")
        else:
            st.error(f"실패: {r.text}")

# 관리자만 role 부여 가능
if role == "admin":
    st.markdown("---")
    st.subheader("관리자 패널: 권한 설정")
    target_email_admin = st.text_input("권한을 설정할 사용자 이메일")
    new_role = st.selectbox("부여할 권한", ["student", "leader", "admin"])
    if st.button("권한 변경"):
        r = requests.post(f"{BACKEND}/set_role", json={"target_email": target_email_admin, "role": new_role})
        if r.status_code == 200:
            st.success("권한 변경 성공")
        else:
            st.error(f"실패: {r.text}")

# 간단한 스탬프 목록(읽기)
st.markdown("---")
st.subheader("최근 스탬프")
# 이 예제는 백엔드에 스탬프 조회 API가 없으므로 직접 Firestore에 접근하는 UI 코드는 생략.
st.info("스탬프 목록을 보려면 백엔드에 /stamps 또는 직접 Firestore 읽기 엔드포인트를 추가하세요.")
