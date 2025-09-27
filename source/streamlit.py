# streamlit_app.py (일부 주요 업데이트)
import streamlit as st
import requests
import json
import jwt
from datetime import datetime

# Flask 서버 기본 URL
FLASK_SERVER_URL = "http://localhost:5000"

# Streamlit 세션 상태 초기화
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'login_html_loaded' not in st.session_state:
    st.session_state.login_html_loaded = False

# 환경 변수에서 Firebase 구성을 읽어 HTML 내용 동적 생성
import os
from dotenv import load_dotenv
load_dotenv()

def get_firebase_login_html():
    """Firebase 구성 정보로 HTML 내용을 동적으로 생성합니다."""
    html_path = "firebase_login.html"
    with open(html_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    # .env 파일의 값으로 플레이스홀더 대체
    firebase_config_keys = ['API_KEY', 'AUTH_DOMAIN', 'PROJECT_ID', 'STORAGE_BUCKET', 'MESSAGING_SENDER_ID', 'APP_ID']
    for key in firebase_config_keys:
        env_key = f"FIREBASE_{key}"
        html_content = html_content.replace(f"{{{{{env_key}}}}}", os.getenv(env_key, ""))
    return html_content

# Flask 서버에 요청을 보내는 헬퍼 함수 (기존과 동일)
def make_flask_request(endpoint, method='GET', data=None, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        if method == 'GET':
            response = requests.get(f"{FLASK_SERVER_URL}{endpoint}", headers=headers)
        elif method == 'POST':
            response = requests.post(f"{FLASK_SERVER_URL}{endpoint}", json=data, headers=headers)
        return response
    except requests.exceptions.ConnectionError:
        st.error("Flask 서버에 연결할 수 없습니다. flask_auth_server.py가 실행 중인지 확인하세요.")
        return None

def handle_login_callback(id_token):
    """Flask 서버로 ID 토큰을 전송하여 검증하고 JWT를 받습니다."""
    response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
    if response and response.status_code == 200:
        data = response.json()
        st.session_state.auth_token = data['access_token']
        st.session_state.user_info = data['user']
        st.success("로그인 성공!")
        st.rerun()
    else:
        error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
        st.error(f"로그인 실패: {error_msg}")

# 메인 페이지 렌더링 함수
def main():
    st.set_page_config(page_title="학교 웹사이트", page_icon="🏫", layout="wide")

    # HTML 컴포넌트에서 메시지 수신 처리
    if not st.session_state.login_html_loaded:
        # HTML이 로드된 후 한 번만 실행되도록 플래그 설정
        st.session_state.login_html_loaded = True
        # HTML 컴포넌트에 메시지를 전달하기 위한 커스텀 스크립트
        components.html(f"""
            <script>
                window.addEventListener('message', function(event) {{
                    if (event.data.type === 'FIREBASE_ID_TOKEN') {{
                        // Streamlit의 experimental_set_query_params를 통해 토큰 전달
                        window.parent.postMessage({{type: 'streamlit:setComponentValue', value: event.data.token}}, '*');
                    }}
                }}, false);
            </script>
        """, height=0) # 높이 0으로 보이지 않게 함

    # 쿼리 파라미터 또는 세션 상태를 통한 로그인 처리
    query_params = st.experimental_get_query_params()
    if 'token' in query_params and not st.session_state.auth_token:
        id_token = query_params['token'][0]
        handle_login_callback(id_token)
        # 토큰이 URL에 남지 않도록 쿼리 파라미터 제거
        st.experimental_set_query_params()

    # 로그인 상태에 따른 UI 표시
    if st.session_state.auth_token:
        show_main_page()
    else:
        show_login_page()

def show_login_page():
    """로그인 페이지를 표시합니다."""
    st.title("학교 웹사이트 로그인")
    st.write("학교 구글 계정(@jeohyeon.hs.kr)으로 로그인하세요.")

    # HTML 컴포넌트를 iframe으로 표시
    login_html = get_firebase_login_html()
    from streamlit.components.v1 import html
    html(login_html, height=200)

    # HTML에서 postMessage로 보낸 토큰을 처리하기 위한 JavaScript 리스너
    # Streamlit의 컴포넌트 값 변경 감지 (대안 구현)
    st.components.v1.html("""
        <script>
        window.addEventListener('message', function(event) {
            // 상위 창(Streamlit)으로 메시지를 전달하는 로직
            if (event.data.type === 'FIREBASE_ID_TOKEN') {
                // Streamlit과의 통합을 위해 쿼리 파라미터를 설정하도록 시뮬레이션
                window.location.href = window.location.origin + window.location.pathname + '?token=' + encodeURIComponent(event.data.token);
            }
        });
        </script>
    """, height=0)

# show_main_page() 및 역할별 기능은 이전과 동일하게 유지
# ... (이전 코드의 show_main_page, show_student_features 등 유지)

if __name__ == '__main__':
    main()