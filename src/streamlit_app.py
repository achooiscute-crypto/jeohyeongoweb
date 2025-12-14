import streamlit as st
import requests
import jwt
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from streamlit.components.v1 import html
import json

load_dotenv()

FLASK_SERVER_URL = "https://jeohyeon-academic-web.onrender.com"
FIREBASE_AUTH_URL = "https://jeohyeonweb.firebaseapp.com"
STREAMLIT_APP_URL = "https://jeohyeongoweb.streamlit.app"

STAMP_BOOTHS = [f"booth{i}" for i in range(1, 35)]

# 세션 상태 초기화
session_defaults = {
    'auth_token': None,
    'user_info': None,
    'logout_triggered': False,
    'just_logged_out': False,
    'current_page': 0,
    'show_schedule': False,
    'show_clubs': False,
    'admin_users': None
}

for key, default in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

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
    """토큰 검증 함수 (datetime.utcnow() 수정)"""
    if not token:
        return None
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp', 0)
        if datetime.now(timezone.utc).timestamp() > exp:  # 수정
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

def show_schedule_section():
    st.subheader("📅 발표 일정")
    schedule_data = [
        {"시간": "09:00 - 09:30", "제목": "개회식", "장소": "강당"},
        {"시간": "09:30 - 10:30", "제목": "1학년 과학 발표", "장소": "1층 로비"},
        {"시간": "10:30 - 11:30", "제목": "2학년 역사 발표", "장소": "2층 세미나실"},
        {"시간": "11:30 - 12:30", "제목": "점심 시간", "장소": "식당"},
        {"시간": "12:30 - 14:00", "제목": "동아리 발표회", "장소": "각 동아리실"},
        {"시간": "14:00 - 15:00", "제목": "특별 강연", "장소": "강당"},
        {"시간": "15:00 - 16:00", "제목": "폐회식", "장소": "강당"},
    ]
    
    for event in schedule_data:
        with st.container():
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                st.write(f"**{event['시간']}**")
            with col2:
                st.write(event['제목'])
            with col3:
                st.write(event['장소'])
            st.markdown("---")

def show_clubs_section():
    st.subheader("🏫 동아리 목록")
    clubs_data = [
        {"이름": "과학 동아리", "지도교사": "김영희 선생님", "활동장소": "과학실 1", "소개": "실험과 연구를 통한 과학 탐구"},
        {"이름": "역사 동아리", "지도교사": "이철수 선생님", "활동장소": "인문학실", "소개": "역사 탐방과 자료 연구"},
        {"이름": "미술 동아리", "지도교사": "박지민 선생님", "활동장소": "미술실", "소개": "다양한 미술 활동과 전시"},
        {"이름": "음악 동아리", "지도교사": "정다운 선생님", "활동장소": "음악실", "소개": "합주와 공연 준비"},
        {"이름": "봉사 동아리", "지도교사": "최성민 선생님", "활동장소": "상담실", "소개": "지역사회 봉사 활동"},
        {"이름": "코딩 동아리", "지도교사": "한지훈 선생님", "활동장소": "컴퓨터실", "소개": "프로그래밍과 앱 개발"},
    ]
    
    for club in clubs_data:
        with st.expander(f"**{club['이름']}** - {club['지도교사']}"):
            st.write(f"**활동 장소:** {club['활동장소']}")
            st.write(f"**동아리 소개:** {club['소개']}")

def show_login_page():
    st.title("🏫 학교 웹사이트")
    
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
        st.success("학교 구글 계정(@jeohyeon.hs.kr)으로 로그인해 주세요.")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("로그인")
            login_js = f"""
            <script>
            function openAuthPage() {{
                window.open("{FIREBASE_AUTH_URL}", "_blank");
            }}
            </script>
            <button onclick="openAuthPage()" 
                    style="padding: 15px 30px; font-size: 16px; background: #FF4B4B; color: white; border: none; border-radius: 5px; cursor: pointer; width: 100%;">
                🚪 Google 로그인
            </button>
            """
            html(login_js, height=100)
            st.info("로그인 페이지가 새 창에서 열립니다.")
        
        with col2:
            st.subheader("도움말")
            st.markdown("""
            - 학교 구글 계정만 로그인 가능합니다
            - 로그인 후 자동으로 이동합니다
            - 문제 발생 시 수동 로그인을 이용하세요
            """)

        with st.expander("🛠️ 수동 로그인 (문제 발생 시)"):
            manual_token = st.text_area("토큰을 여기에 붙여넣으세요", height=80)
            if st.button("🔐 수동 로그인", use_container_width=True):
                if manual_token.strip():
                    handle_login_callback(manual_token.strip())
                else:
                    st.warning("토큰을 입력해주세요.")

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
    total_pages = (len(STAMP_BOOTHS) + stamps_per_page - 1) // stamps_per_page
    
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
    end_idx = min(start_idx + stamps_per_page, len(STAMP_BOOTHS))
    current_stamps = STAMP_BOOTHS[start_idx:end_idx]
    
    stamps_data = user_info.get('stamps', {})
    
    cols = st.columns(5)
    for i, booth in enumerate(current_stamps):
        col_idx = i % 5
        has_stamp = stamps_data.get(booth, False)
        booth_number = booth.replace("booth", "")
        
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
                        {booth_number}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.success(f"**부스 {booth_number}**")
            else:
                st.markdown(
                    f"""
                    <div style='
                        width: 80px; height: 80px; border-radius: 50%; 
                        background: #f0f0f0; border: 2px dashed #ccc;
                        display: flex; align-items: center; justify-content: center; 
                        color: #999; margin: 10px auto; font-size: 16px;
                    '>
                        {booth_number}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.info(f"**부스 {booth_number}**")
    
    stamp_count = sum(1 for has_stamp in stamps_data.values() if has_stamp)
    total_stamps = len(STAMP_BOOTHS)
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
    
    st.info("⚠️ 부장은 순차적 스탬프 부여만 가능합니다. 각 학생에게는 순서대로 한 개의 스탬프만 부여할 수 있습니다.")
    
    with st.form("manager_grant_form"):
        st.subheader("🎫 순차적 스탬프 부여")
        
        # 학번만 입력해도 자동 완성
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
                    # 순차적 부여 모드로 요청
                    response = make_flask_request('/api/stamps', 'POST', {
                        'target_email': target_email, 
                        'action': 'grant',
                        'auto_grant': True  # 순차적 부여 모드
                    }, token)
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data.get('message')}")
                        st.balloons()
                    else:
                        error_msg = response.json().get('message', '처리 실패') if response else '서버 연결 실패'
                        st.error(f"❌ 스탬프 부여 실패: {error_msg}")

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
                '스탬프': f"{stamp_count}/{len(STAMP_BOOTHS)}"
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
                            # 목록 새로고침
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
                booth_id = st.selectbox("스탬프 선택", STAMP_BOOTHS, key="admin_booth_select")
                booth_number = booth_id.replace("booth", "")
                st.info(f"선택한 스탬프: **부스 {booth_number}**")
            
            if st.form_submit_button("✅ 적용", use_container_width=True):
                if not specific_target_email:
                    st.error("❌ 대상 이메일을 입력하세요.")
                else:
                    with st.spinner("스탬프 처리 중..."):
                        response = make_flask_request('/api/stamps', 'POST', {
                            'target_email': specific_target_email, 
                            'booth_id': booth_id,
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
        st.title(f"👋 {user_info['display_name']}님, 환영합니다!")
        stamp_count = sum(1 for booth, has_stamp in user_info.get('stamps', {}).items() if has_stamp)
        total_booths = len(STAMP_BOOTHS)
        st.write(f"**역할:** {user_info['role']} | **스탬프:** {stamp_count}/{total_booths}")
        
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
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("📅 발표 일정 보기", use_container_width=True, key="schedule_btn"):
            st.session_state.show_schedule = not st.session_state.show_schedule
            st.session_state.show_clubs = False if st.session_state.show_schedule else st.session_state.show_clubs
    
    with col_btn2:
        if st.button("🏫 동아리 목록", use_container_width=True, key="clubs_btn"):
            st.session_state.show_clubs = not st.session_state.show_clubs
            st.session_state.show_schedule = False if st.session_state.show_clubs else st.session_state.show_schedule
    
    if st.session_state.get('show_schedule', False):
        show_schedule_section()
        
    if st.session_state.get('show_clubs', False):
        show_clubs_section()
    
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
        page_title="학교 웹사이트", 
        page_icon="🏫", 
        layout="wide",
        initial_sidebar_state="collapsed"
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