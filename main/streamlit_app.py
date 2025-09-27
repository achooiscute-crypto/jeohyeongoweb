# streamlit_app.py
import streamlit as st
import requests
import jwt
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Flask 서버 기본 URL
FLASK_SERVER_URL = "http://localhost:5000"

# Streamlit 세션 상태 초기화
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

def make_flask_request(endpoint, method='GET', data=None, token=None):
    """Flask 서버에 요청을 보내는 헬퍼 함수"""
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        url = f"{FLASK_SERVER_URL}{endpoint}"
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        return response
    except requests.exceptions.ConnectionError:
        st.error("🚨 Flask 서버에 연결할 수 없습니다. flask_auth_server.py가 실행 중인지 확인하세요.")
        return None
    except Exception as e:
        st.error(f"요청 중 오류 발생: {e}")
        return None

def verify_token(token):
    """토큰 검증 함수"""
    if not token:
        return None
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp', 0)
        if datetime.utcnow().timestamp() > exp:
            st.session_state.auth_token = None
            st.session_state.user_info = None
            st.error("로그인 세션이 만료되었습니다. 다시 로그인해주세요.")
            return None
        return decoded
    except Exception:
        st.session_state.auth_token = None
        st.session_state.user_info = None
        return None

# ✅ 수정: handle_login_callback 함수 정의
def handle_login_callback(id_token):
    """테스트용: 입력받은 토큰을 세션에 저장"""
    st.session_state.auth_token = id_token
    # 테스트용 사용자 정보 설정
    st.session_state.user_info = {
        'email': 'test_student@jeohyeon.hs.kr',
        'display_name': '테스트학생',
        'role': 'student',
        'honyangi': 100
    }
    st.rerun()

def show_login_page():
    st.title("🏫 학교 웹사이트 로그인 (개발자 테스트 모드)")
    st.warning("""
    Firebase 로그인 팝업이 현재 환경에서 지원되지 않습니다.
    대체 수단을 이용해 주세요.
    """)

    # 방법 1: 수동 토큰 입력 (테스트용)
    st.subheader("방법 1: 수동 토큰 입력 (테스트용)")
    st.info("아무 문자열이나 입력하면 테스트용 계정으로 로그인됩니다.")

    # st.chat_input을 사용하여 토큰 입력받기
    id_token = st.chat_input("여기에 임의의 토큰을 입력하고 Enter를 누르세요...")
    if id_token:
        handle_login_callback(id_token)

    # 방법 2: 테스트용 사용자 생성 버튼 (선택사항)
    st.subheader("방법 2: 테스트용 계정 생성")
    st.info("로그인 흐름만 테스트하려면 아래 버튼으로 가상 사용자를 생성하세요. (Firebase 연동 없음)")
    
    if st.button("테스트 학생 계정으로 로그인"):
        st.session_state.auth_token = "test-token-student"
        st.session_state.user_info = {
            'email': 'test_student@jeohyeon.hs.kr',
            'display_name': '테스트학생',
            'role': 'student',
            'honyangi': 100
        }
        st.rerun()
    
    if st.button("테스트 관리자 계정으로 로그인"):
        st.session_state.auth_token = "test-token-admin"
        st.session_state.user_info = {
            'email': 'test_admin@jeohyeon.hs.kr',
            'display_name': '테스트관리자',
            'role': 'admin',
            'honyangi': 500
        }
        st.rerun()
    
    # ✅ 최신 API 적용
    token_param = st.query_params.get('token', None)
    if token_param and not st.session_state.auth_token:
        id_token = token_param if isinstance(token_param, str) else token_param[0]
        response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
        
        if response and response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data['access_token']
            st.session_state.user_info = data['user']
            st.query_params.clear()  # URL 정리
            st.rerun()
        else:
            error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
            st.error(f"로그인 실패: {error_msg}")

def show_main_page():
    token = st.session_state.auth_token
    user_info = st.session_state.user_info
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"👋 {user_info['display_name']}님, 환영합니다!")
        st.write(f"**역할:** {user_info['role']} | **보유 호냥이:** {user_info.get('honyangi', 0)}")
    with col2:
        if st.button("🚪 로그아웃"):
            st.session_state.auth_token = None
            st.session_state.user_info = None
            st.rerun()
    
    st.divider()
    show_student_features(token, user_info)
    
    if user_info['role'] in ['manager', 'admin']:
        st.divider()
        show_manager_features(token, user_info)
    
    if user_info['role'] == 'admin':
        st.divider()
        show_admin_features(token, user_info)

# (학생/부장/관리자 기능 함수들은 기존과 동일)

def main():
    st.set_page_config(
        page_title="학교 웹사이트", 
        page_icon="🏫", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    if st.session_state.auth_token:
        user_data = verify_token(st.session_state.auth_token)
        if user_data:
            show_main_page()
        else:
            show_login_page()
    else:
        show_login_page()

if __name__ == '__main__':
    main()
