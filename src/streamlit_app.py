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
        # 실제로는 서버에서 검증해야 하지만, 클라이언트에서 기본 검증
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp', 0)
        if datetime.utcnow().timestamp() > exp:
            st.session_state.auth_token = None
            st.session_state.user_info = None
            st.error("로그인 세션이 만료되었습니다. 다시 로그인해주세요.")
            return None
        return decoded
    except Exception as e:
        st.session_state.auth_token = None
        st.session_state.user_info = None
        return None

def show_login_page():
    """로그인 페이지 표시"""
    st.title("🏫 학교 웹사이트 로그인")
    st.write("학교 구글 계정(@jeohyeon.hs.kr)으로 로그인하세요.")
    
    # Firebase 로그인 HTML 컴포넌트
    firebase_config = {
        'apiKey': os.getenv('FIREBASE_API_KEY', ''),
        'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', ''),
        'projectId': os.getenv('FIREBASE_PROJECT_ID', ''),
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', ''),
        'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID', ''),
        'appId': os.getenv('FIREBASE_APP_ID', '')
    }
    
    # HTML 컴포넌트
    html_content = f"""
    <html>
    <head>
        <script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js"></script>
        <script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-auth-compat.js"></script>
        <script>
            const firebaseConfig = {firebase_config};
            firebase.initializeApp(firebaseConfig);
            
            function signInWithGoogle() {{
                const provider = new firebase.auth.GoogleAuthProvider();
                provider.setCustomParameters({{ hd: 'jeohyeon.hs.kr' }});
                
                firebase.auth().signInWithPopup(provider)
                    .then((result) => {{
                        return result.user.getIdToken(true);
                    }}).then((idToken) => {{
                        // Streamlit으로 토큰 전송
                        window.parent.postMessage({{
                            type: 'FIREBASE_ID_TOKEN',
                            token: idToken
                        }}, '*');
                    }}).catch((error) => {{
                        console.error("Login error:", error);
                        window.parent.postMessage({{
                            type: 'FIREBASE_LOGIN_ERROR',
                            error: error.message
                        }}, '*');
                    }});
            }}
        </script>
    </head>
    <body>
        <button onclick="signInWithGoogle()" style="
            padding: 12px 24px; 
            font-size: 16px; 
            background-color: #4285f4; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        ">
            Google로 로그인
        </button>
    </body>
    </html>
    """
    
    # HTML 컴포넌트 렌더링
    st.components.v1.html(html_content, height=100)
    
    # 메시지 리스너
    st.components.v1.html("""
        <script>
            window.addEventListener('message', function(event) {
                if (event.data.type === 'FIREBASE_ID_TOKEN') {
                    // Streamlit의 set_query_params를 통해 토큰 전달
                    const url = new URL(window.location);
                    url.searchParams.set('token', event.data.token);
                    window.history.replaceState({}, '', url);
                    
                    // 페이지 리로드 트리거
                    window.parent.postMessage({type: 'RELOAD'}, '*');
                }
            });
        </script>
    """, height=0)
    
    # URL 파라미터에서 토큰 처리
    query_params = st.experimental_get_query_params()
    if 'token' in query_params and not st.session_state.auth_token:
        id_token = query_params['token'][0]
        response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
        
        if response and response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data['access_token']
            st.session_state.user_info = data['user']
            st.experimental_set_query_params()  # URL 정리
            st.rerun()
        else:
            error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
            st.error(f"로그인 실패: {error_msg}")

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