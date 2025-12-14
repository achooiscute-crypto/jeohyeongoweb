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
    'show_exhibition': False,
    'show_clubs': False,
    'show_map': False,
    'admin_users': None,
    'persistent_auth': None  # 새로 추가: 지속적인 인증 상태
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
    """토큰 검증 함수"""
    if not token:
        return None
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp', 0)
        if datetime.now(timezone.utc).timestamp() > exp:
            # 토큰이 만료된 경우에만 로그아웃
            st.session_state.auth_token = None
            st.session_state.user_info = None
            st.error("로그인 세션이 만료되었습니다. 다시 로그인해주세요.")
            return None
        return decoded
    except Exception:
        # 토큰 검증 실패 시에도 즉시 로그아웃하지 않음
        return None

def handle_login_callback(id_token):
    response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
    if response and response.status_code == 200:
        data = response.json()
        st.session_state.auth_token = data['access_token']
        st.session_state.user_info = data['user']
        st.session_state.persistent_auth = data['access_token']  # 지속적인 인증 저장
        
        save_auth_js = f"""
        <script>
        var authData = {{
            token: "{data['access_token']}",
            user: {json.dumps(data['user'])}
        }};
        localStorage.setItem('stamp_auth', JSON.stringify(authData));
        console.log('Login successful, token saved to localStorage');
        </script>
        """
        html(save_auth_js, height=0)
        
        st.success("✅ 로그인 성공!")
        st.rerun()
    else:
        error_msg = response.json().get('message', '로그인 실패') if response else '서버 연결 실패'
        st.error(f"❌ 로그인 실패: {error_msg}")

def restore_auth_from_localstorage():
    """LocalStorage에서 인증 정보 복원"""
    restore_js = """
    <script>
    // LocalStorage에서 인증 정보 가져오기
    const authData = localStorage.getItem('stamp_auth');
    if (authData) {
        const data = JSON.parse(authData);
        // Streamlit에 메시지 전송
        window.parent.postMessage({
            type: 'RESTORE_AUTH_FROM_STORAGE',
            token: data.token,
            user: data.user
        }, '*');
        console.log('Auth data found in localStorage');
    } else {
        console.log('No auth data in localStorage');
    }
    </script>
    """
    html(restore_js, height=0)

def show_exhibition_section():
    """전시 및 체험 활동 섹션"""
    st.subheader("🎨 전시 및 체험 활동")
    
    # 이미지 표시를 위한 준비
    st.info("전시 및 체험 활동 정보가 준비 중입니다.")
    
    # 이미지 표시 예시 (이미지 파일이 있으면 주석 해제)
    # st.image("exhibition.jpg", caption="전시 활동 예시", use_container_width=True)
    
    # 임시 내용
    exhibition_data = [
        {"부스": "1-3번", "활동명": "과학 실험 체험", "내용": "재미있는 과학 실험 체험"},
        {"부스": "4-6번", "활동명": "미술 전시", "내용": "학생들의 미술 작품 전시"},
        {"부스": "7-9번", "활동명": "로봇 체험", "내용": "로봇 제작 및 조종 체험"},
        {"부스": "10-12번", "활동명": "VR 체험", "내용": "가상 현실 체험 존"},
    ]
    
    for item in exhibition_data:
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 2])
            with col1:
                st.write(f"**{item['부스']}**")
            with col2:
                st.write(item['활동명'])
            with col3:
                st.write(item['내용'])
            st.markdown("---")

def show_clubs_section():
    """학술발표 참여 동아리 섹션"""
    st.subheader("🏫 학술발표 참여 동아리")
    
    # 이미지 표시를 위한 준비
    st.info("학술발표 동아리 정보가 준비 중입니다.")
    
    # 이미지 표시 예시
    # st.image("clubs.jpg", caption="동아리 활동", use_container_width=True)
    
    clubs_data = [
        {"동아리": "과학 동아리", "발표주제": "환경 오염과 해결 방안", "시간": "10:00-11:00"},
        {"동아리": "역사 동아리", "발표주제": "고려시대의 문화", "시간": "11:00-12:00"},
        {"동아리": "문학 동아리", "발표주제": "현대 시의 이해", "시간": "13:00-14:00"},
        {"동아리": "수학 동아리", "발표주제": "수학 퍼즐 대회", "시간": "14:00-15:00"},
    ]
    
    for club in clubs_data:
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.write(f"**{club['동아리']}**")
            with col2:
                st.write(club['발표주제'])
            with col3:
                st.write(club['시간'])
            st.markdown("---")

def show_map_section():
    """학술제 맵 섹션"""
    st.subheader("🗺️ 학술제 맵")
    
    # 이미지 표시를 위한 준비
    st.info("학술제 지도가 준비 중입니다.")
    
    # 이미지 표시 예시 - 나중에 실제 학술제 맵 이미지로 교체
    # st.image("academic_fair_map.jpg", caption="학술제 전체 지도", use_container_width=True)
    
    # 임시로 마크다운으로 맵 표시
    st.markdown("""
    ### 🏛️ 학술제 부스 배치도
    
    ```
    ┌─────────────────────────────────────────┐
    │ 1층: 전시 및 체험 활동 부스 (1-17번)    │
    ├─────────────────────────────────────────┤
    │ █ 1-3번: 과학 체험존                    │
    │ █ 4-6번: 미술 전시존                    │
    │ █ 7-9번: 기술 체험존                    │
    │ █ 10-12번: 문화 체험존                  │
    │ █ 13-15번: 요리 체험존                  │
    │ █ 16-17번: 특별 전시존                  │
    ├─────────────────────────────────────────┤
    │ 2층: 학술발표 동아리 (18-34번)         │
    ├─────────────────────────────────────────┤
    │ █ 18-21번: 과학 발표실                  │
    │ █ 22-25번: 인문학 발표실                │
    │ █ 26-29번: 예술 발표실                  │
    │ █ 30-34번: 특별 강연장                  │
    └─────────────────────────────────────────┘
    ```
    
    ### 🚶 이동 경로
    - **주 출입구**: 정문 (1층 로비)
    - **계단**: 로비 좌우측
    - **엘리베이터**: 로비 중앙
    - **화장실**: 각 층 끝부분
    
    ### 📍 주요 시설
    - **식당**: 1층 서측
    - **휴게실**: 1층 동측
    - **안내데스크**: 로비 중앙
    """)

def show_login_page():
    st.title("🏫 학교 웹사이트")
    
    if 'just_logged_out' in st.session_state and st.session_state.just_logged_out:
        st.session_state.just_logged_out = False
        st.success("✅ 안전하게 로그아웃되었습니다.")
    
    # 페이지 로드 시 LocalStorage에서 인증 복원 시도
    if not st.session_state.auth_token:
        restore_auth_from_localstorage()
    
    if 'token' in st.query_params and not st.session_state.auth_token:
        if 'logout_triggered' not in st.session_state or not st.session_state.logout_triggered:
            id_token = st.query_params['token']
            st.info("🔐 토큰을 받았습니다. 로그인 처리 중...")
            
            response = make_flask_request('/api/login', 'POST', {'id_token': id_token})
            
            if response and response.status_code == 200:
                data = response.json()
                st.session_state.auth_token = data['access_token']
                st.session_state.user_info = data['user']
                st.session_state.persistent_auth = data['access_token']
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
            - 로그인 상태는 브라우저에 저장됩니다
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
        // Firebase 인증 페이지로부터의 메시지 수신
        window.addEventListener('message', function(event) {{
            if (event.origin === "https://jeohyeonweb.firebaseapp.com" && 
                event.data.type === 'FIREBASE_ID_TOKEN') {{
                window.location.href = '{STREAMLIT_APP_URL}?token=' + encodeURIComponent(event.data.token);
            }}
        }});
        
        // LocalStorage 복원 메시지 처리
        window.addEventListener('message', function(event) {{
            if (event.data.type === 'RESTORE_AUTH_FROM_STORAGE') {{
                console.log('Received auth data from localStorage');
                // 페이지 새로고침 없이 세션 상태 업데이트
                window.location.href = '{STREAMLIT_APP_URL}?restore_token=' + encodeURIComponent(event.data.token);
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
    stamp_count = sum(1 for has_stamp in stamps_data.values() if has_stamp)
    
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
    
    total_stamps = len(STAMP_BOOTHS)
    progress = stamp_count / total_stamps if total_stamps > 0 else 0
    
    st.subheader("📊 진행 상황")
    st.progress(progress)
    st.write(f"**{stamp_count} / {total_stamps} 스탬프 획득** ({progress:.1%})")
    
    # 부장인 경우 스탬프 제한 정보 표시
    if user_info['role'] == 'manager':
        st.info(f"⚠️ 부장 권한: 현재 {stamp_count}개의 스탬프를 보유 중입니다. 부장은 자신과 다른 학생에게 각각 1개의 스탬프만 부여할 수 있습니다.")
    
    with st.expander("👤 내 프로필 정보"):
        st.write(f"**표시 이름:** {user_info.get('display_name', '이름 없음')}")
        st.write(f"**이메일:** {user_info['email']}")
        st.write(f"**역할:** {user_info['role']}")
        st.write(f"**획득 스탬프:** {stamp_count}개")
        
        # 스탬프 상세 정보
        if stamp_count > 0:
            st.write("**획득한 스탬프 목록:**")
            for booth, has_stamp in stamps_data.items():
                if has_stamp:
                    st.write(f"- {booth.replace('booth', '부스 ')}")

def show_manager_features(token, user_info):
    st.header("🔄 스탬프 관리 (부장)")
    
    # 부장의 현재 스탬프 상태 확인
    stamps_data = user_info.get('stamps', {})
    stamp_count = sum(1 for has_stamp in stamps_data.values() if has_stamp)
    
    if stamp_count >= 1:
        st.warning(f"⚠️ 이미 {stamp_count}개의 스탬프를 보유하고 있습니다. 부장은 자신에게 하나의 스탬프만 부여할 수 있습니다.")
        st.info("다른 학생에게 스탬프를 부여하려면 아래에서 진행해주세요.")
    
    st.info("""
    **부장 권한 제한 사항:**
    1. 자신에게는 1개의 스탬프만 부여 가능
    2. 각 학생에게는 1개의 스탬프만 부여 가능
    3. 순차적 스탬프 부여만 가능 (다음 순서 스탬프 자동 선택)
    """)
    
    with st.form("manager_grant_form"):
        st.subheader("🎫 순차적 스탬프 부여")
        
        # 자신에게 부여할지 다른 학생에게 부여할지 선택
        grant_type = st.radio("부여 대상 선택:", ["다른 학생에게 부여", "자신에게 부여"], key="manager_grant_type")
        
        if grant_type == "다른 학생에게 부여":
            target_input = st.text_input("대상 학생 학번 또는 이메일", 
                                        placeholder="2411224 (자동으로 @jeohyeon.hs.kr 추가)",
                                        key="manager_grant_input_other")
            target_email = format_email_input(target_input)
        else:
            target_email = user_info['email']
            st.info(f"**부여 대상:** 자신 ({target_email})")
        
        if target_email and grant_type == "다른 학생에게 부여":
            st.info(f"**부여 대상:** {target_email}")
        
        submitted = st.form_submit_button("✅ 순차적 스탬프 부여", use_container_width=True)
        
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
                        
                        # 자신의 정보 업데이트
                        if target_email == user_info['email']:
                            profile_response = make_flask_request('/api/profile', 'GET', token=token)
                            if profile_response and profile_response.status_code == 200:
                                st.session_state.user_info = profile_response.json().get('user')
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
                '스탬프 수': stamp_count,
                '스탬프 비율': f"{stamp_count}/{len(STAMP_BOOTHS)}"
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
        if st.button("🚪 로그아웃", key="logout_button"):
            logout_js = """
            <script>
            localStorage.removeItem('stamp_auth');
            console.log('Logout: Removed auth data from localStorage');
            </script>
            """
            html(logout_js, height=0)
            st.session_state.auth_token = None
            st.session_state.user_info = None
            st.session_state.persistent_auth = None
            st.session_state.logout_triggered = True
            st.session_state.just_logged_out = True
            st.rerun()
    
    st.markdown("---")
    
    # ✅ 3개의 상단 버튼
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🎨 전시 및 체험 활동", 
                    use_container_width=True, 
                    key="exhibition_btn",
                    type="primary" if st.session_state.show_exhibition else "secondary"):
            # 다른 버튼들은 False로, 현재 버튼은 토글
            st.session_state.show_exhibition = not st.session_state.show_exhibition
            st.session_state.show_clubs = False
            st.session_state.show_map = False
    
    with col_btn2:
        if st.button("🏫 학술발표 참여 동아리", 
                    use_container_width=True, 
                    key="clubs_btn",
                    type="primary" if st.session_state.show_clubs else "secondary"):
            st.session_state.show_exhibition = False
            st.session_state.show_clubs = not st.session_state.show_clubs
            st.session_state.show_map = False
    
    with col_btn3:
        if st.button("🗺️ 학술제 맵", 
                    use_container_width=True, 
                    key="map_btn",
                    type="primary" if st.session_state.show_map else "secondary"):
            st.session_state.show_exhibition = False
            st.session_state.show_clubs = False
            st.session_state.show_map = not st.session_state.show_map
    
    # 상단 버튼 섹션 표시
    if st.session_state.get('show_exhibition', False):
        show_exhibition_section()
        
    if st.session_state.get('show_clubs', False):
        show_clubs_section()
        
    if st.session_state.get('show_map', False):
        show_map_section()
    
    st.divider()
    
    # 스탬프 기능 표시
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
    
    # ✅ 페이지 로드 시 인증 상태 복원
    # 1. 먼저 LocalStorage에서 복원 시도
    if 'auth_token' not in st.session_state or not st.session_state.auth_token:
        auth_data_json = """
        <script>
        var authData = localStorage.getItem('stamp_auth');
        if (authData) {
            window.parent.postMessage({type: 'RESTORE_AUTH_FROM_STORAGE', data: authData}, '*');
        }
        </script>
        """
        html(auth_data_json, height=0)
    
    # 2. LocalStorage 복원 메시지 처리
    auth_restore_js = """
    <script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'RESTORE_AUTH_FROM_STORAGE') {
            console.log('Processing auth restore from localStorage');
            const authData = JSON.parse(event.data.data);
            // Streamlit에 메시지 전송하여 페이지 리로드
            const url = new URL(window.location);
            url.searchParams.set('restore_token', authData.token);
            window.history.replaceState({}, '', url);
            window.location.reload();
        }
    });
    </script>
    """
    html(auth_restore_js, height=0)

    # 3. 쿼리 파라미터에서 토큰 복원
    if 'restore_token' in st.query_params and not st.session_state.auth_token:
        restore_token = st.query_params['restore_token']
        st.session_state.auth_token = restore_token
        
        # 토큰 검증 후 사용자 정보 가져오기
        decoded = verify_token(restore_token)
        if decoded:
            # 토큰이 유효하면 사용자 정보 가져오기
            response = make_flask_request('/api/profile', 'GET', token=restore_token)
            if response and response.status_code == 200:
                st.session_state.user_info = response.json().get('user')
                st.session_state.persistent_auth = restore_token
        st.query_params.clear()
        st.rerun()
    
    # 4. 로그아웃 처리
    if 'logout_triggered' in st.session_state and st.session_state.logout_triggered:
        st.session_state.logout_triggered = False
        st.session_state.auth_token = None
        st.session_state.user_info = None
        st.session_state.persistent_auth = None
        if 'token' in st.query_params or 'restore_token' in st.query_params:
            st.query_params.clear()
        show_login_page()
        return
    
    # 5. 인증 상태 확인 및 페이지 표시
    if st.session_state.auth_token:
        # 토큰 검증 (만료된 경우에만 로그아웃)
        user_data = verify_token(st.session_state.auth_token)
        if user_data:
            show_main_page()
        else:
            # 토큰이 만료된 경우에만 로그인 페이지로
            if datetime.now(timezone.utc).timestamp() > user_data.get('exp', 0) if user_data else True:
                st.session_state.auth_token = None
                st.session_state.user_info = None
                show_login_page()
            else:
                # 다른 이유로 검증 실패해도 로그인 상태 유지
                show_main_page()
    else:
        # 지속적인 인증 상태가 있으면 복원 시도
        if st.session_state.persistent_auth:
            response = make_flask_request('/api/profile', 'GET', token=st.session_state.persistent_auth)
            if response and response.status_code == 200:
                st.session_state.auth_token = st.session_state.persistent_auth
                st.session_state.user_info = response.json().get('user')
                st.rerun()
            else:
                show_login_page()
        else:
            show_login_page()

if __name__ == '__main__':
    main()