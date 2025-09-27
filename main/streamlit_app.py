# streamlit_app.py
import streamlit as st
import requests
import jwt
from datetime import datetime
import os
from dotenv import load_dotenv
import webbrowser
from streamlit.components.v1 import html

load_dotenv()

# Flask 서버 기본 URL
FLASK_SERVER_URL = "http://localhost:5000"

# Firebase 호스팅된 인증 페이지 URL (✅ 실제 URL로 수정)
FIREBASE_AUTH_URL = "https://jeohyeonweb.web.app"

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

# ✅ 중요: handle_login_callback 함수를 실제 Flask 통신으로 변경
def handle_login_callback(id_token):
    """Flask 서버로 ID 토큰을 전송하여 실제 로그인 처리"""
    response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
    if response and response.status_code == 200:
        data = response.json()
        st.session_state.auth_token = data['access_token']
        st.session_state.user_info = data['user']
        st.success("✅ 로그인 성공!")
        st.rerun()
    else:
        error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
        st.error(f"❌ 로그인 실패: {error_msg}")

def show_login_page():
    st.title("🏫 학교 웹사이트 로그인")
    st.write("학교 구글 계정(@jeohyeon.hs.kr)으로 로그인해 주세요.")

    # 로그인 버튼
    if st.button("Google로 로그인", key="hosted_login"):
        # 새 팝업 창으로 Firebase 호스팅 인증 페이지 열기
        webbrowser.open_new(FIREBASE_AUTH_URL)
        st.info("로그인 팝업창이 열립니다. 로그인 완료 후 이 창으로 돌아오세요.")

    # ✅ 개선된 JavaScript 메시지 처리
    auth_js = """
    <script>
        // Firebase 호스팅 페이지에서 전송된 메시지 수신
        window.addEventListener('message', function(event) {
            // 메시지 출처 검증 (보안 강화)
            if (event.origin !== "https://jeohyeonweb.web.app") {
                console.log('Untrusted origin:', event.origin);
                return;
            }
            
            if (event.data.type === 'FIREBASE_ID_TOKEN') {
                console.log('Received token from auth page');
                // Streamlit의 set_query_params를 통해 토큰 전달
                const url = new URL(window.location);
                url.searchParams.set('token', event.data.token);
                window.history.replaceState({}, '', url);
                
                // Streamlit에 리로드 신호 전송
                window.dispatchEvent(new Event('tokenReceived'));
            }
        });
        
        // 리로드 이벤트 리스너
        window.addEventListener('tokenReceived', function() {
            // Streamlit의 rerun을 트리거하기 위해 URL 변경 감지
            window.location.reload();
        });
    </script>
    """
    html(auth_js, height=0)

    # 쿼리 파라미터에서 토큰 처리
    if 'token' in st.query_params and not st.session_state.auth_token:
        id_token = st.query_params['token']
        st.write("🔐 토큰을 받았습니다. 로그인 처리 중...")
        handle_login_callback(id_token)
        # ✅ 중요: 토큰 사용 후 쿼리 파라미터 제거 (보안)
        st.query_params.clear()

def show_main_page():
    """메인 페이지 표시"""
    token = st.session_state.auth_token
    user_info = st.session_state.user_info
    
    # 상단 바
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
    
    # 역할별 기능 표시
    show_student_features(token, user_info)
    
    if user_info['role'] in ['manager', 'admin']:
        st.divider()
        show_manager_features(token, user_info)
    
    if user_info['role'] == 'admin':
        st.divider()
        show_admin_features(token, user_info)

def show_student_features(token, user_info):
    """학생 기능 표시"""
    st.header("📝 학생 메뉴")
    
    with st.form("profile_form"):
        st.subheader("프로필 이름 수정")
        new_name = st.text_input("표시 이름", value=user_info.get('display_name', ''))
        submitted = st.form_submit_button("이름 변경")
        
        if submitted:
            if new_name.strip():
                response = make_flask_request('/api/profile', 'POST', {'display_name': new_name.strip()}, token)
                if response and response.status_code == 200:
                    st.session_state.user_info['display_name'] = new_name.strip()
                    st.success("✅ 이름이 성공적으로 변경되었습니다!")
                    st.rerun()
                else:
                    st.error("❌ 이름 변경에 실패했습니다.")
            else:
                st.warning("⚠️ 이름을 입력해주세요.")

def show_manager_features(token, user_info):
    """부장 기능 표시"""
    st.header("💰 부장 메뉴 - 호냥이 관리")
    
    with st.form("honyangi_form"):
        st.subheader("호냥이 지급/차감")
        target_email = st.text_input("대상 학생 이메일", placeholder="2411224@jeohyeon.hs.kr")
        amount = st.number_input("변경 금액 (음수 입력 시 차감)", min_value=-1000, max_value=1000, value=0, step=10)
        submitted = st.form_submit_button("호냥이 적용")
        
        if submitted:
            if not target_email:
                st.error("❌ 대상 이메일을 입력하세요.")
            elif amount == 0:
                st.warning("⚠️ 0 이외의 금액을 입력하세요.")
            else:
                response = make_flask_request('/api/honyangi', 'POST', {
                    'target_email': target_email, 
                    'amount': amount
                }, token)
                
                if response and response.status_code == 200:
                    st.success(f"✅ {response.json().get('message')}")
                else:
                    error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                    st.error(f"❌ 호냥이 변경 실패: {error_msg}")

def show_admin_features(token, user_info):
    """관리자 기능 표시"""
    st.header("⚙️ 관리자 메뉴 - 사용자 권한 관리")
    
    # 사용자 목록 조회
    if st.button("사용자 목록 새로고침"):
        response = make_flask_request('/api/users', 'GET', token=token)
        if response and response.status_code == 200:
            users_data = response.json().get('users', [])
            st.session_state.admin_users = users_data
    
    if 'admin_users' in st.session_state:
        st.subheader("전체 사용자 목록")
        for user in st.session_state.admin_users:
            with st.expander(f"{user.get('display_name', '이름 없음')} ({user.get('email', '이메일 없음')})"):
                st.write(f"역할: {user.get('role', 'student')}")
                st.write(f"호냥이: {user.get('honyangi', 0)}")
    
    # 역할 변경
    with st.form("role_form"):
        st.subheader("사용자 역할 변경")
        target_email = st.text_input("대상 사용자 이메일", placeholder="2411224@jeohyeon.hs.kr")
        new_role = st.selectbox("새로운 역할", ["student", "manager", "admin"])
        submitted = st.form_submit_button("역할 변경")
        
        if submitted:
            if not target_email:
                st.error("❌ 대상 이메일을 입력하세요.")
            else:
                response = make_flask_request('/api/role', 'POST', {
                    'target_email': target_email, 
                    'new_role': new_role
                }, token)
                
                if response and response.status_code == 200:
                    st.success(f"✅ {response.json().get('message')}")
                else:
                    error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                    st.error(f"❌ 역할 변경 실패: {error_msg}")

def main():
    """메인 앱 함수"""
    st.set_page_config(
        page_title="학교 웹사이트", 
        page_icon="🏫", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 토큰 검증
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