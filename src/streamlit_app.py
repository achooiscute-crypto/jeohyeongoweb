import streamlit as st
import requests
import jwt
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from streamlit.components.v1 import html
import json
import base64

load_dotenv()

FLASK_SERVER_URL = "https://jeohyeon-academic-web.onrender.com"
FIREBASE_AUTH_URL = "https://jeohyeonweb.firebaseapp.com"
STREAMLIT_APP_URL = "https://jeohyeongoweb.streamlit.app"

# ✅ 스탬프 ID 목록 (부스 → 스탬프로 변경)
STAMP_IDS = [f"stamp{i}" for i in range(1, 35)]

# 세션 상태 초기화
session_defaults = {
    'auth_token': None,
    'user_info': None,
    'logout_triggered': False,
    'just_logged_out': False,
    'current_page': 0,
    'show_presentation_clubs': False,
    'show_exhibition_activities': False,
    'show_academic_web': False,
    'admin_users': None
}

for key, default in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

def get_base64_image(image_path):
    """이미지를 base64로 인코딩"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없음: {image_path}")
        return None
    except Exception as e:
        print(f"❌ 이미지 로드 오류: {e}")
        return None

def format_email_input(user_input):
    """학번만 입력해도 자동으로 이메일 완성"""
    if not user_input:
        return ""
    
    if user_input.isdigit():
        return f"{user_input}@jeohyeon.hs.kr"
    elif '@' in user_input:
        return user_input
    else:
        return f"{user_input}@jeohyeon.hs.kr"

def make_flask_request(endpoint, method='GET', data=None, token=None):
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
        st.error("🚨 Flask 서버에 연결할 수 없습니다.")
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
        if datetime.now(timezone.utc).timestamp() > exp:
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
    response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
    if response and response.status_code == 200:
        data = response.json()
        st.session_state.auth_token = data['access_token']
        st.session_state.user_info = data['user']
        
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

def show_image_section(title, image_key):
    """이미지 표시 섹션 (나중에 구현)"""
    st.subheader(title)
    st.info("🖼️ 이미지가 곧 업데이트될 예정입니다.")
    # 나중에 이미지 파일 표시 로직 추가

def show_login_page():
    # ✅ 디버깅: 현재 작업 디렉토리 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    background_image_path = os.path.join(current_dir, "background.jpg")
    
    # base64 인코딩 시도
    bg_image_base64 = get_base64_image(background_image_path)
    
    if bg_image_base64:
        st.sidebar.success("✅ 배경 이미지 로드 성공!")
        # 배경 이미지가 있을 때
        page_bg_css = f"""
        <style>
        /* 전체 페이지 스타일 */
        .stApp {{
            background-image: linear-gradient(rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.3)), 
                              url("data:image/jpg;base64,{bg_image_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        /* Streamlit 기본 요소 숨기기 */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        </style>
        """
        st.markdown(page_bg_css, unsafe_allow_html=True)
    else:
        st.sidebar.error("❌ 배경 이미지 로드 실패 - 기본 배경 사용")
        # 배경 이미지가 없을 때 기본 스타일
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)
    
    if 'just_logged_out' in st.session_state and st.session_state.just_logged_out:
        st.session_state.just_logged_out = False
        st.success("✅ 안전하게 로그아웃되었습니다.")
    
    if 'token' in st.query_params and not st.session_state.auth_token:
        if 'logout_triggered' not in st.session_state or not st.session_state.logout_triggered:
            id_token = st.query_params['token']
            st.info("🔐 토큰을 받았습니다. 로그인 처리 중...")
            
            response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
            
            if response and response.status_code == 200:
                data = response.json()
                st.session_state.auth_token = data['access_token']
                st.session_state.user_info = data['user']
                st.query_params.clear()
                st.rerun()
            else:
                error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
                st.error(f"❌ 로그인 실패: {error_msg}")
        else:
            st.query_params.clear()

    if not st.session_state.auth_token:
        # ✅ 상단 여백
        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
        
        # ✅ 중앙 정렬된 컨테이너 삭제한다
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 20px;'>
            
            </div>
            """, unsafe_allow_html=True)
        
        # ✅ 하단 로그인 버튼
        st.markdown("<div style='height: 200px;'></div>", unsafe_allow_html=True)
        
        # 버튼을 중앙 정렬하기 위한 컬럼
        col_left, col_center, col_right = st.columns([1, 1, 1])
        
        with col_center:
            # ✅ 하늘색 로그인 버튼 스타일
            login_button_html = f"""
            <div style='text-align: center;'>
                <button onclick="openAuthPage()" 
                        style="
                            padding: 15px 30px;
                            font-size: 18px;
                            font-weight: bold;
                            background: #7e9af5;
                            color: white;
                            border: none;
                            border-radius: 25px;
                            cursor: pointer;
                            width: 100%;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                            transition: all 0.3s;
                        "
                        onmouseover="this.style.background='#6CB4D9'; this.style.transform='translateY(-2px)'"
                        onmouseout="this.style.background='#87CEEB'; this.style.transform='translateY(0)'">
                     Google 로그인
                </button>
            </div>
            <script>
            function openAuthPage() {{
                window.open("{FIREBASE_AUTH_URL}", "_blank");
            }}
            </script>
            """
            html(login_button_html, height=80)

        auth_js = f"""
        <script>
        window.addEventListener('message', function(event) {{
            if (event.origin === "https://jeohyeonweb.firebaseapp.com" && 
                event.data.type === 'FIREBASE_ID_TOKEN') {{
                window.location.href = '{STREAMLIT_APP_URL}?token=' + encodeURIComponent(event.data.token);
            }}
        }});
        </script>
        """
        html(auth_js, height=0)

def show_student_features(token, user_info):
    st.header("🎫 나의 스탬프 현황")
    
    stamps_per_page = 10
    total_pages = (len(STAMP_IDS) + stamps_per_page - 1) // stamps_per_page
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 이전", disabled=st.session_state.current_page == 0):
            st.session_state.current_page -= 1
            st.rerun()
    with col2:
        st.write(f"페이지 {st.session_state.current_page + 1} / {total_pages}")
    with col3:
        if st.button("다음 ▶", disabled=st.session_state.current_page >= total_pages - 1):
            st.session_state.current_page += 1
            st.rerun()
    
    start_idx = st.session_state.current_page * stamps_per_page
    end_idx = min(start_idx + stamps_per_page, len(STAMP_IDS))
    current_stamps = STAMP_IDS[start_idx:end_idx]
    
    stamps_data = user_info.get('stamps', {})
    
    cols = st.columns(5)
    for i, stamp_id in enumerate(current_stamps):
        col_idx = i % 5
        has_stamp = stamps_data.get(stamp_id, False)
        stamp_number = stamp_id.replace("stamp", "")
        
        with cols[col_idx]:
            if has_stamp:
                st.markdown(
                    f"""
                    <div style='
                        width: 80px; height: 80px; border-radius: 50%; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex; align-items: center; justify-content: center; 
                        color: white; font-weight: bold; margin: 10px auto;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        font-size: 16px;
                    '>
                        {stamp_number}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.success(f"**스탬프 {stamp_number}**")
            else:
                st.markdown(
                    f"""
                    <div style='
                        width: 80px; height: 80px; border-radius: 50%; 
                        background: #f0f0f0; border: 2px dashed #ccc;
                        display: flex; align-items: center; justify-content: center; 
                        color: #999; margin: 10px auto; font-size: 16px;
                    '>
                        {stamp_number}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.info(f"**스탬프 {stamp_number}**")
    
    stamp_count = sum(1 for has_stamp in stamps_data.values() if has_stamp)
    total_stamps = len(STAMP_IDS)
    progress = stamp_count / total_stamps
    
    st.subheader("📊 진행 상황")
    st.progress(progress)
    st.write(f"**{stamp_count} / {total_stamps} 스탬프 획득** ({progress:.1%})")
    
    with st.expander("👤 내 프로필 정보"):
        st.write(f"**표시 이름:** {user_info.get('display_name', '이름 없음')}")
        st.write(f"**이메일:** {user_info['email']}")
        st.write(f"**역할:** {user_info['role']}")
        st.write(f"**획득 스탬프:** {stamp_count}개")

def show_manager_features(token, user_info):
    st.header("🔄 스탬프 관리 (부장)")
    
    # ✅ 강화된 안내 메시지
    st.warning("""
    ⚠️ **부장 권한 안내**
    - 부장은 **각 계정당 1개의 스탬프만** 부여할 수 있습니다
    - 자신에게도 1개만 부여 가능합니다
    - 한 번 부여하면 동일 계정에 추가 부여 불가
    - 순차적으로 다음 빈 스탬프가 자동 부여됩니다
    """)
    
    with st.form("manager_grant_form"):
        st.subheader("🎫 순차적 스탬프 부여")
        
        target_input = st.text_input("대상 학생 학번 또는 이메일", 
                                    placeholder="2411224 (자동으로 @jeohyeon.hs.kr 추가)",
                                    key="manager_grant_input")
        target_email = format_email_input(target_input)
        
        if target_email:
            st.info(f"**부여 대상:** {target_email}")
        
        submitted = st.form_submit_button("✅ 다음 순서 스탬프 부여", use_container_width=True)
        
        if submitted:
            if not target_email:
                st.error("❌ 대상 학번을 입력하세요.")
            else:
                with st.spinner("순차적 스탬프 부여 중..."):
                    response = make_flask_request('/api/stamps', 'POST', {
                        'target_email': target_email, 
                        'action': 'grant',
                        'auto_grant': True
                    }, token)
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data.get('message')}")
                        st.balloons()
                        st.info("💡 이 계정에는 더 이상 스탬프를 부여할 수 없습니다.")
                    else:
                        error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                        st.error(f"❌ {error_msg}")

def show_admin_features(token, user_info):
    st.header("⚙️ 관리자 메뉴")
    
    if 'admin_users' not in st.session_state:
        response = make_flask_request('/api/users', 'GET', token=token)
        if response and response.status_code == 200:
            st.session_state.admin_users = response.json().get('users', [])
    
    st.subheader("👥 사용자 관리")
    
    if 'admin_users' in st.session_state and st.session_state.admin_users:
        users_for_display = []
        for user in st.session_state.admin_users:
            stamps = user.get('stamps', {})
            stamp_count = sum(1 for has_stamp in stamps.values() if has_stamp)
            users_for_display.append({
                '이메일': user.get('email', '이메일 없음'),
                '이름': user.get('display_name', '이름 없음'),
                '역할': user.get('role', 'student'),
                '스탬프': f"{stamp_count}/{len(STAMP_IDS)}"
            })
        
        st.dataframe(users_for_display, use_container_width=True)
        
        st.subheader("🔄 역할 변경")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            role_target_input = st.text_input("대상 학생 학번 또는 이메일", 
                                            placeholder="2411224 (자동으로 @jeohyeon.hs.kr 추가)",
                                            key="role_target_input")
            role_target_email = format_email_input(role_target_input)
        
        with col2:
            new_role = st.selectbox("새로운 역할", ["student", "manager", "admin"], key="role_select")
        
        with col3:
            st.write("") 
            st.write("")
            if st.button("🚀 역할 변경", type="primary", use_container_width=True):
                if role_target_email:
                    with st.spinner("역할 변경 중..."):
                        response = make_flask_request('/api/role', 'POST', {
                            'target_email': role_target_email, 
                            'new_role': new_role
                        }, token)
                        
                        if response and response.status_code == 200:
                            st.success(f"✅ {response.json().get('message')}")
                            response = make_flask_request('/api/users', 'GET', token=token)
                            if response and response.status_code == 200:
                                st.session_state.admin_users = response.json().get('users', [])
                            st.rerun()
                        else:
                            error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                            st.error(f"❌ 역할 변경 실패: {error_msg}")
                else:
                    st.error("❌ 대상 이메일을 입력하세요.")
    
    st.subheader("🎫 스탬프 관리")
    st.info("💡 관리자는 Manager 제약 없이 모든 작업 가능")
    
    with st.expander("📝 순차적 스탬프 부여"):
        with st.form("admin_auto_grant_form"):
            auto_target_input = st.text_input("대상 학생 학번 또는 이메일", 
                                            placeholder="2411224 (자동으로 @jeohyeon.hs.kr 추가)",
                                            key="admin_auto_grant_input")
            auto_target_email = format_email_input(auto_target_input)
            
            if auto_target_email:
                st.info(f"**부여 대상:** {auto_target_email}")
            
            if st.form_submit_button("✅ 순차적 스탬프 부여", use_container_width=True):
                if not auto_target_email:
                    st.error("❌ 대상 학번을 입력하세요.")
                else:
                    with st.spinner("순차적 스탬프 부여 중..."):
                        response = make_flask_request('/api/stamps', 'POST', {
                            'target_email': auto_target_email, 
                            'action': 'grant',
                            'auto_grant': True
                        }, token)
                        
                        if response and response.status_code == 200:
                            data = response.json()
                            st.success(f"✅ {data.get('message')}")
                            st.balloons()
                        else:
                            error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                            st.error(f"❌ 스탬프 부여 실패: {error_msg}")
    
    with st.expander("🔄 특정 스탬프 부여/회수"):
        with st.form("admin_specific_stamp_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                specific_target_input = st.text_input("대상 학생 학번 또는 이메일", 
                                                    placeholder="2411224 (자동으로 @jeohyeon.hs.kr 추가)",
                                                    key="admin_specific_input")
                specific_target_email = format_email_input(specific_target_input)
                
                action_type = st.radio("작업", ["부여", "회수"], key="admin_action", horizontal=True)
            
            with col2:
                stamp_id = st.selectbox("스탬프 선택", STAMP_IDS, key="admin_stamp_select")
                stamp_number = stamp_id.replace("stamp", "")
                st.info(f"선택한 스탬프: **스탬프 {stamp_number}**")
            
            if st.form_submit_button("✅ 적용", use_container_width=True):
                if not specific_target_email:
                    st.error("❌ 대상 이메일을 입력하세요.")
                else:
                    with st.spinner("스탬프 처리 중..."):
                        response = make_flask_request('/api/stamps', 'POST', {
                            'target_email': specific_target_email, 
                            'stamp_id': stamp_id,
                            'action': 'grant' if action_type == "부여" else 'revoke'
                        }, token)
                        
                        if response and response.status_code == 200:
                            st.success(f"✅ {response.json().get('message')}")
                            if action_type == "부여":
                                st.balloons()
                        else:
                            error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                            st.error(f"❌ 스탬프 처리 실패: {error_msg}")

def show_main_page():
    token = st.session_state.auth_token
    user_info = st.session_state.user_info
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f" {user_info['display_name']}님, 환영합니다!")
        stamp_count = sum(1 for stamp, has_stamp in user_info.get('stamps', {}).items() if has_stamp)
        total_stamps = len(STAMP_IDS)
        st.write(f"**역할:** {user_info['role']} | **스탬프:** {stamp_count}/{total_stamps}")
        
    with col2:
        if st.button("🚪 로그아웃"):
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
    
    st.markdown("---")
    
    # ✅ 3개의 버튼으로 변경
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    
    with col_btn1:
        if st.button("🎨 전시 및\n체험 활동", use_container_width=True, key="exhibition_btn"):
            st.session_state.show_exhibition_activities = not st.session_state.show_exhibition_activities
            st.session_state.show_presentation_clubs = False
            st.session_state.show_academic_web = False
            
    with col_btn2:
        if st.button("🌐 학술제 맵", use_container_width=True, key="academic_web_btn"):
            st.session_state.show_academic_web = not st.session_state.show_academic_web
            st.session_state.show_presentation_clubs = False
            st.session_state.show_exhibition_activities = False

    with col_btn3:
        if st.button("📚 학술발표\n참여 동아리", use_container_width=True, key="presentation_btn"):
            st.session_state.show_presentation_clubs = not st.session_state.show_presentation_clubs
            st.session_state.show_exhibition_activities = False
            st.session_state.show_academic_web = False
    
    # ✅ 각 버튼에 대응하는 콘텐츠 표시
    if st.session_state.get('show_presentation_clubs', False):
        show_image_section("📚 학술발표 참여 동아리", "presentation_clubs")
        
    if st.session_state.get('show_exhibition_activities', False):
        show_image_section("🎨 전시 및 체험 활동", "exhibition_activities")
        
    if st.session_state.get('show_academic_web', False):
        show_image_section("🌐 학술제 웹", "academic_web")
    
    st.divider()
    
    show_student_features(token, user_info)
    
    if user_info['role'] in ['manager', 'admin']:
        st.divider()
        if user_info['role'] == 'manager':
            show_manager_features(token, user_info)
        elif user_info['role'] == 'admin':
            show_admin_features(token, user_info)

def main():
    st.set_page_config(
        page_title="저현고 학술제", 
        page_icon="🏫", 
        layout="wide", # 디버깅을 위해 사이드바 열기
    )
    
    if 'auth_token' not in st.session_state:
        auth_data_json = """
        <script>
        var authData = localStorage.getItem('stamp_auth');
        if (authData) {
            window.parent.postMessage({type: 'RESTORE_AUTH', data: authData}, '*');
        }
        </script>
        """
        html(auth_data_json, height=0)

    auth_restore_js = """
    <script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'RESTORE_AUTH') {
            const authData = JSON.parse(event.data.data);
            const url = new URL(window.location);
            url.searchParams.set('restore_token', authData.token);
            window.history.replaceState({}, '', url);
            window.location.reload();
        }
    });
    </script>
    """
    html(auth_restore_js, height=0)

    if 'restore_token' in st.query_params and not st.session_state.auth_token:
        restore_token = st.query_params['restore_token']
        st.session_state.auth_token = restore_token
        response = make_flask_request('/api/profile', 'GET', token=restore_token)
        if response and response.status_code == 200:
            st.session_state.user_info = response.json().get('user')
        st.query_params.clear()
        st.rerun()
    
    if 'logout_triggered' in st.session_state and st.session_state.logout_triggered:
        st.session_state.logout_triggered = False
        st.session_state.auth_token = None
        st.session_state.user_info = None
        if 'token' in st.query_params:
            st.query_params.clear()
        show_login_page()
        return
    
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