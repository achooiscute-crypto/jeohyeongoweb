# streamlit_app.py
import streamlit as st
import requests
import jwt
from datetime import datetime
import os
from dotenv import load_dotenv
import webbrowser
from streamlit.components.v1 import html
import json

load_dotenv()

# Flask 서버 기본 URL
FLASK_SERVER_URL = "http://localhost:5000"  # 로컬 테스트용

# Firebase 호스팅된 인증 페이지 URL
FIREBASE_AUTH_URL = "https://jeohyeonweb.firebaseapp.com"

# 스탬프 부스 목록 (백엔드와 동일하게 유지)
STAMP_BOOTHS = [
    "booth1", "booth2", "booth3", "booth4", "booth5",
    "booth6", "booth7", "booth8", "booth9", "booth10"
]

# Streamlit 세션 상태 초기화
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'logout_triggered' not in st.session_state:
    st.session_state.logout_triggered = False
if 'just_logged_out' not in st.session_state:
    st.session_state.just_logged_out = False

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

def handle_login_callback(id_token):
    """Flask 서버로 ID 토큰을 전송하여 실제 로그인 처리"""
    response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
    if response and response.status_code == 200:
        data = response.json()
        st.session_state.auth_token = data['access_token']
        st.session_state.user_info = data['user']
        
        # ✅ LocalStorage에 로그인 정보 저장
        save_auth_js = f"""
        <script>
        var authData = {{
            token: "{data['access_token']}",
            user: {json.dumps(data['user'])}
        }};
        localStorage.setItem('stamp_auth', JSON.stringify(authData));
        </script>
        """
        html(save_auth_js, height=0)
        
        st.success("✅ 로그인 성공!")
        st.rerun()
    else:
        error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
        st.error(f"❌ 로그인 실패: {error_msg}")

def show_login_page():
    st.title("🏫 학교 웹사이트")
    
    # ✅ 명시적 로그아웃 후에는 토큰 무시
    if 'just_logged_out' in st.session_state and st.session_state.just_logged_out:
        st.session_state.just_logged_out = False
        st.success("✅ 안전하게 로그아웃되었습니다.")
    
    # ✅ 쿼리 파라미터에서 토큰 자동 처리 (로그아웃 상태에서만)
    if 'token' in st.query_params and not st.session_state.auth_token:
        # 로그아웃 직후인지 확인
        if 'logout_triggered' not in st.session_state or not st.session_state.logout_triggered:
            id_token = st.query_params['token']
            st.info("🔐 토큰을 받았습니다. 로그인 처리 중...")
            
            # Flask 서버로 토큰 검증 요청
            response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
            
            if response and response.status_code == 200:
                data = response.json()
                st.session_state.auth_token = data['access_token']
                st.session_state.user_info = data['user']
                st.query_params.clear()  # 토큰 제거
                st.rerun()
            else:
                error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
                st.error(f"❌ 로그인 실패: {error_msg}")
        else:
            # 로그아웃 직후면 토큰 무시하고 제거
            st.query_params.clear()

    if not st.session_state.auth_token:
        st.success("학교 구글 계정(@jeohyeon.hs.kr)으로 로그인해 주세요.")
        
        # ✅ 간결한 로그인 UI
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("로그인")
            if st.button("🚪 **Google 로그인**", 
                        type="primary", 
                        use_container_width=True,
                        key="main_login"):
                webbrowser.open_new(FIREBASE_AUTH_URL)
                st.info("로그인 페이지가 열립니다. 로그인을 완료해주세요.")
        
        with col2:
            st.subheader("도움말")
            st.markdown("""
            - 학교 구글 계정만 로그인 가능합니다
            - 로그인 후 자동으로 이동합니다
            - 문제 발생 시 수동 로그인을 이용하세요
            """)

        # ✅ 간소화된 수동 로그인
        with st.expander("🛠️ 수동 로그인 (문제 발생 시)"):
            manual_token = st.text_area("토큰을 여기에 붙여넣으세요", height=80)
            if st.button("🔐 수동 로그인", use_container_width=True):
                if manual_token.strip():
                    handle_login_callback(manual_token.strip())
                else:
                    st.warning("토큰을 입력해주세요.")

        # JavaScript 메시지 처리
        auth_js = """
        <script>
        window.addEventListener('message', function(event) {
            if (event.origin === "https://jeohyeonweb.firebaseapp.com" && 
                event.data.type === 'FIREBASE_ID_TOKEN') {
                window.location.href = 'http://localhost:8501?token=' + encodeURIComponent(event.data.token);
            }
        });
        </script>
        """
        html(auth_js, height=0)

def show_main_page():
    """메인 페이지 표시"""
    token = st.session_state.auth_token
    user_info = st.session_state.user_info
    
    # 상단 바
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"👋 {user_info['display_name']}님, 환영합니다!")
        
        # 스탬프 개수 계산
        stamp_count = sum(1 for booth, has_stamp in user_info.get('stamps', {}).items() if has_stamp)
        total_booths = len(STAMP_BOOTHS)
        
        st.write(f"**역할:** {user_info['role']} | **스탬프:** {stamp_count}/{total_booths}")
        
        # 진행률 표시줄
        progress = stamp_count / total_booths if total_booths > 0 else 0
        st.progress(progress)
        st.caption(f"스탬프 진행률: {stamp_count}/{total_booths} ({progress:.1%})")
        
    with col2:
        if st.button("🚪 로그아웃"):
            # ✅ LocalStorage에서 인증 정보 제거
            logout_js = """
            <script>
            localStorage.removeItem('stamp_auth');
            </script>
            """
            html(logout_js, height=0)
            
            st.session_state.auth_token = None
            st.session_state.user_info = None
            st.session_state.logout_triggered = True
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
    st.header("🎫 나의 스탬프 현황")
    
    # 스탬프 그리드 표시
    stamps = user_info.get('stamps', {})
    
    # 5열 그리드로 스탬프 표시
    cols = st.columns(5)
    for i, booth in enumerate(STAMP_BOOTHS):
        col_idx = i % 5
        has_stamp = stamps.get(booth, False)
        
        with cols[col_idx]:
            # 스탬프 모양 (동그란 버튼 형태)
            if has_stamp:
                st.markdown(
                    f"""
                    <div style='
                        width: 80px; 
                        height: 80px; 
                        border-radius: 50%; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        color: white; 
                        font-weight: bold;
                        margin: 10px auto;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    '>
                        ✓
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.success(f"**{booth}**")
            else:
                st.markdown(
                    f"""
                    <div style='
                        width: 80px; 
                        height: 80px; 
                        border-radius: 50%; 
                        background: #f0f0f0;
                        border: 2px dashed #ccc;
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        color: #999; 
                        margin: 10px auto;
                    '>
                        ?
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.info(f"**{booth}**")
    
    # 프로필 정보
    with st.expander("👤 내 프로필 정보"):
        st.write(f"**표시 이름:** {user_info.get('display_name', '이름 없음')}")
        st.write(f"**이메일:** {user_info['email']}")
        st.write(f"**역할:** {user_info['role']}")
        st.write(f"**가입일:** {user_info.get('created_at', '알 수 없음')}")

def show_manager_features(token, user_info):
    """부장 기능 표시"""
    st.header("🔄 부스 스탬프 관리")
    
    with st.form("stamp_management_form"):
        st.subheader("스탬프 부여/회수")
        
        # 대상 사용자 입력
        target_email = st.text_input("대상 학생 이메일", placeholder="2411224@jeohyeon.hs.kr")
        
        # 부스 선택
        booth_id = st.selectbox("부스 선택", STAMP_BOOTHS)
        
        # 작업 선택
        action = st.radio("작업 선택", ["부여하기 🎫", "회수하기 ❌"], horizontal=True)
        
        action_type = "grant" if action == "부여하기 🎫" else "revoke"
        action_text = "부여" if action_type == "grant" else "회수"
        
        submitted = st.form_submit_button(f"✅ 스탬프 {action_text}")
        
        if submitted:
            if not target_email:
                st.error("❌ 대상 이메일을 입력하세요.")
            else:
                with st.spinner("스탬프 변경 중..."):
                    response = make_flask_request('/api/stamps', 'POST', {
                        'target_email': target_email, 
                        'booth_id': booth_id,
                        'action': action_type
                    }, token)
                    
                    if response and response.status_code == 200:
                        st.success(f"✅ {response.json().get('message')}")
                    else:
                        error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                        st.error(f"❌ 스탬프 변경 실패: {error_msg}")

def show_admin_features(token, user_info):
    """관리자 기능 표시"""
    st.header("⚙️ 관리자 메뉴")
    
    # ✅ 즉시 사용자 목록 로드
    if 'admin_users' not in st.session_state:
        response = make_flask_request('/api/users', 'GET', token=token)
        if response and response.status_code == 200:
            st.session_state.admin_users = response.json().get('users', [])
    
    # 사용자 관리 섹션
    st.subheader("👥 사용자 관리")
    
    if 'admin_users' in st.session_state and st.session_state.admin_users:
        # 사용자 목록 테이블
        users_for_display = []
        for user in st.session_state.admin_users:
            stamps = user.get('stamps', {})
            stamp_count = sum(1 for has_stamp in stamps.values() if has_stamp)
            users_for_display.append({
                '이메일': user.get('email', '이메일 없음'),
                '이름': user.get('display_name', '이름 없음'),
                '역할': user.get('role', 'student'),
                '스탬프': f"{stamp_count}/{len(STAMP_BOOTHS)}"
            })
        
        st.dataframe(users_for_display, use_container_width=True)
        
        # ✅ 빠른 역할 변경
        st.subheader("🔄 빠른 역할 변경")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            selected_user = st.selectbox(
                "대상 사용자 선택",
                options=[user['이메일'] for user in users_for_display],
                key="user_select"
            )
        
        with col2:
            new_role = st.selectbox("새로운 역할", ["student", "manager", "admin"], key="role_select")
        
        with col3:
            st.write("")  # 공백
            st.write("")  # 공백
            if st.button("🚀 역할 변경", type="primary", use_container_width=True):
                if selected_user:
                    with st.spinner("역할 변경 중..."):
                        response = make_flask_request('/api/role', 'POST', {
                            'target_email': selected_user, 
                            'new_role': new_role
                        }, token)
                        
                        if response and response.status_code == 200:
                            st.success(f"✅ {response.json().get('message')}")
                            # 목록 새로고침
                            response = make_flask_request('/api/users', 'GET', token=token)
                            if response and response.status_code == 200:
                                st.session_state.admin_users = response.json().get('users', [])
                            st.rerun()
                        else:
                            error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                            st.error(f"❌ 역할 변경 실패: {error_msg}")
    
    # ✅ 스탬프 관리 기능
    st.subheader("🎫 스탬프 관리")
    
    if 'admin_users' in st.session_state and st.session_state.admin_users:
        with st.form("admin_stamp_management"):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                admin_target_user = st.selectbox(
                    "대상 사용자",
                    options=[user['이메일'] for user in users_for_display],
                    key="admin_user_select"
                )
            
            with col2:
                admin_booth_id = st.selectbox("부스 선택", STAMP_BOOTHS, key="admin_booth_select")
            
            with col3:
                admin_action = st.radio("작업", ["부여", "회수"], key="admin_action", horizontal=True)
            
            with col4:
                st.write("")
                st.write("")
                admin_submitted = st.form_submit_button("적용", use_container_width=True)
            
            if admin_submitted and admin_target_user:
                action_type = "grant" if admin_action == "부여" else "revoke"
                with st.spinner("스탬프 변경 중..."):
                    response = make_flask_request('/api/stamps', 'POST', {
                        'target_email': admin_target_user, 
                        'booth_id': admin_booth_id,
                        'action': action_type
                    }, token)
                    
                    if response and response.status_code == 200:
                        st.success(f"✅ {response.json().get('message')}")
                        # 목록 새로고침
                        response = make_flask_request('/api/users', 'GET', token=token)
                        if response and response.status_code == 200:
                            st.session_state.admin_users = response.json().get('users', [])
                        st.rerun()
                    else:
                        error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                        st.error(f"❌ 스탬프 변경 실패: {error_msg}")

def main():
    """메인 앱 함수"""
    st.set_page_config(
        page_title="학교 웹사이트", 
        page_icon="🏫", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # ✅ 페이지 새로고침 시 로그인 상태 복원 (가장 먼저 실행)
    if 'auth_token' not in st.session_state:
        # LocalStorage에서 로그인 정보 가져오기 시도
        auth_data_json = """
        <script>
        var authData = localStorage.getItem('stamp_auth');
        if (authData) {
            window.parent.postMessage({type: 'RESTORE_AUTH', data: authData}, '*');
        }
        </script>
        """
        html(auth_data_json, height=0)

    # ✅ 메시지 리스너 - LocalStorage에서 복원된 데이터 처리
    auth_restore_js = """
    <script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'RESTORE_AUTH') {
            const authData = JSON.parse(event.data.data);
            // Streamlit의 세션 상태 복원을 위해 쿼리 파라미터 설정
            const url = new URL(window.location);
            url.searchParams.set('restore_token', authData.token);
            window.history.replaceState({}, '', url);
            window.location.reload();
        }
    });
    </script>
    """
    html(auth_restore_js, height=0)

    # ✅ 복원 토큰 처리
    if 'restore_token' in st.query_params and not st.session_state.auth_token:
        restore_token = st.query_params['restore_token']
        st.session_state.auth_token = restore_token
        # 사용자 정보 복원 (Flask 서버에서 다시 가져옴)
        response = make_flask_request('/api/profile', 'GET', token=restore_token)
        if response and response.status_code == 200:
            st.session_state.user_info = response.json().get('user')
        st.query_params.clear()
        st.rerun()
    
    # ✅ 로그아웃 플래그 확인
    if 'logout_triggered' in st.session_state and st.session_state.logout_triggered:
        st.session_state.logout_triggered = False
        st.session_state.auth_token = None
        st.session_state.user_info = None
        # 쿼리 파라미터도 명시적으로 제거
        if 'token' in st.query_params:
            st.query_params.clear()
        show_login_page()
        return
    
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