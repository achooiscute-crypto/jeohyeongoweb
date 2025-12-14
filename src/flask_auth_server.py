from flask_cors import CORS
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
import jwt
import datetime
from functools import wraps
import os
import json
from datetime import datetime, timezone

# Flask 앱 생성
app = Flask(__name__)

# ✅ CORS 설정
allowed_origins = [
    "http://localhost:8501",
    "https://jeohyeonweb.firebaseapp.com",
    "https://jeohyeonweb.web.app",
    "https://jeohyeongoweb.streamlit.app",
]

CORS(app, origins=allowed_origins)

# ✅ 환경 변수 사용
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key-for-development')

# ✅ 스탬프 부스 목록 34개로 확장 (기존 방식 유지)
STAMP_BOOTHS = [f"booth{i}" for i in range(1, 35)]

def initialize_firebase():
    try:
        service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
        
        if service_account_json:
            service_account_info = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized from environment variables")
            return True
        else:
            print("❌ FIREBASE_SERVICE_ACCOUNT_JSON environment variable not found")
            return False
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return False

def get_db():
    try:
        db = firestore.client()
        return db
    except Exception as e:
        print(f"Firestore client error: {e}")
        return None

def get_next_stamp_number(stamps):
    """순차적으로 다음 스탬프 번호 찾기"""
    for i in range(1, 35):
        stamp_id = f"booth{i}"
        if not stamps.get(stamp_id, False):
            return stamp_id, i
    return None, None  # 모든 스탬프가 이미 부여됨

def count_stamps(stamps):
    """부여된 스탬프 개수 세기"""
    if not stamps:
        return 0
    return sum(1 for stamp in stamps.values() if stamp)

def check_manager_stamp_limit(stamps, user_email, target_email, manager_email):
    """매니저의 스탬프 제한 확인"""
    if user_email == 'admin@jeohyeon.hs.kr':  # admin은 제한 없음
        return True
    
    stamp_count = count_stamps(stamps)
    
    # 자신에게 스탬프 부여하는 경우
    if target_email == manager_email:
        if stamp_count >= 1:
            return False, "부장은 자신에게 하나의 스탬프만 부여할 수 있습니다."
        return True, ""
    # 다른 학생에게 스탬프 부여하는 경우
    else:
        if stamp_count >= 1:
            return False, "부장은 한 학생에게 하나의 스탬프만 부여할 수 있습니다."
        return True, ""

db = None
if initialize_firebase():
    db = get_db()

def create_jwt(user_uid, email, role):
    payload = {
        'user_uid': user_uid,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + datetime.timedelta(hours=24)
    }
    try:
        token = jwt.encode(payload, app.secret_key, algorithm='HS256')
        return token
    except Exception as e:
        print(f"JWT creation error: {e}")
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        except Exception as e:
            return jsonify({'message': f'Token validation error: {str(e)}'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def init_or_get_user_profile(user_uid, email, name):
    if not db:
        default_role = 'admin' if email == '2411224@jeohyeon.hs.kr' else 'student'
        default_stamps = {booth: False for booth in STAMP_BOOTHS}
        return {
            'email': email, 
            'display_name': name, 
            'stamps': default_stamps,
            'role': default_role
        }
    
    try:
        user_ref = db.collection('users').document(user_uid)
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            if 'stamps' not in user_data:
                default_stamps = {booth: False for booth in STAMP_BOOTHS}
                user_data['stamps'] = default_stamps
                user_ref.update({'stamps': default_stamps})
            return user_data
        else:
            if email == '2411224@jeohyeon.hs.kr':
                role = 'admin'
            else:
                role = 'student'
            
            default_stamps = {booth: False for booth in STAMP_BOOTHS}
            
            new_user = {
                'email': email,
                'display_name': name or email.split('@')[0],
                'stamps': default_stamps,
                'role': role,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_ref.set(new_user)
            return new_user
    except Exception as e:
        print(f"User profile error: {e}")
        default_role = 'admin' if email == '2411224@jeohyeon.hs.kr' else 'student'
        default_stamps = {booth: False for booth in STAMP_BOOTHS}
        return {
            'email': email, 
            'display_name': name, 
            'stamps': default_stamps,
            'role': default_role
        }

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'firebase_initialized': firebase_admin._apps != {},
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/')
def home():
    return jsonify({'message': 'Flask Auth Server is running!'})

@app.route('/api/login', methods=['POST'])
def login():
    id_token = request.json.get('id_token')
    if not id_token:
        return jsonify({'message': 'ID token is required'}), 400
    
    try:
        decoded_token = auth.verify_id_token(id_token)
        user_uid = decoded_token['uid']
        email = decoded_token['email']
        name = decoded_token.get('name', '')

        if not email.endswith('@jeohyeon.hs.kr'):
            return jsonify({'message': '학교 구글 계정(@jeohyeon.hs.kr)으로만 로그인 가능합니다.'}), 403

        user_profile = init_or_get_user_profile(user_uid, email, name)
        jwt_token = create_jwt(user_uid, email, user_profile['role'])
        if not jwt_token:
            return jsonify({'message': 'JWT 생성 중 오류가 발생했습니다.'}), 500

        return jsonify({
            'message': 'Login successful',
            'access_token': jwt_token,
            'user': {
                'email': email,
                'display_name': user_profile['display_name'],
                'role': user_profile['role'],
                'stamps': user_profile['stamps']
            }
        }), 200
        
    except auth.ExpiredIdTokenError:
        return jsonify({'message': '로그인 세션이 만료되었습니다.'}), 401
    except auth.InvalidIdTokenError:
        return jsonify({'message': '유효하지 않은 로그인 정보입니다.'}), 401
    except Exception as e:
        return jsonify({'message': f'로그인 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    try:
        user_uid = current_user['user_uid']
        if db:
            user_ref = db.collection('users').document(user_uid)
            user_doc = user_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                return jsonify({'user': user_data}), 200
        
        default_stamps = {booth: False for booth in STAMP_BOOTHS}
        return jsonify({
            'user': {
                'email': current_user['email'],
                'display_name': current_user.get('display_name', current_user['email'].split('@')[0]),
                'role': current_user['role'],
                'stamps': default_stamps
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# ✅ 수정된 스탬프 관리 API
@app.route('/api/stamps', methods=['POST'])
@token_required
def update_stamps(current_user):
    user_role = current_user['role']
    user_email = current_user['email']
    data = request.json
    target_email = data.get('target_email')
    booth_id = data.get('booth_id')
    action = data.get('action')
    auto_grant = data.get('auto_grant', False)
    
    if not target_email or not action:
        return jsonify({'message': 'target_email, action은 필수 입력값입니다.'}), 400
    
    try:
        if not db:
            return jsonify({'message': '데이터베이스 연결에 실패했습니다.'}), 500
            
        # 대상 사용자 조회
        users_ref = db.collection('users')
        target_query = users_ref.where('email', '==', target_email).limit(1)
        target_docs = target_query.get()
        
        if not target_docs:
            return jsonify({'message': '대상 사용자를 찾을 수 없습니다.'}), 404
            
        target_doc = target_docs[0]
        target_data = target_doc.to_dict()
        
        # 현재 스탬프 상태 가져오기
        current_stamps = target_data.get('stamps', {})
        if not current_stamps:
            current_stamps = {booth: False for booth in STAMP_BOOTHS}
        
        existing_stamp_count = count_stamps(current_stamps)
        
        if action == 'grant':
            # ✅ 부장 권한 검사
            if user_role == 'manager':
                # 스탬프 제한 확인
                allowed, message = check_manager_stamp_limit(current_stamps, user_email, target_email, user_email)
                if not allowed:
                    return jsonify({'message': message}), 400
                
                # 자동 부여 모드인지 확인
                if not auto_grant:
                    return jsonify({'message': '부장은 순차적 스탬프 부여만 가능합니다.'}), 400
                
                # 다음 사용 가능한 스탬프 찾기
                next_stamp, stamp_number = get_next_stamp_number(current_stamps)
                if not next_stamp:
                    return jsonify({'message': '모든 스탬프가 이미 부여되었습니다.'}), 400
                
                booth_id = next_stamp
                action_text = "순차적 부여"
            
            # ✅ 관리자는 제한 없음
            elif user_role == 'admin':
                if auto_grant:
                    next_stamp, stamp_number = get_next_stamp_number(current_stamps)
                    if not next_stamp:
                        return jsonify({'message': '모든 스탬프가 이미 부여되었습니다.'}), 400
                    booth_id = next_stamp
                    action_text = "순차적 부여"
                else:
                    if not booth_id:
                        return jsonify({'message': '부스 ID를 선택하세요.'}), 400
                    if booth_id not in STAMP_BOOTHS:
                        return jsonify({'message': '유효하지 않은 부스 ID입니다.'}), 400
                    action_text = "특정 부여"
            else:
                return jsonify({'message': '권한이 없습니다.'}), 403
            
            # 스탬프 업데이트
            current_stamps[booth_id] = True
            
        else:  # revoke
            if user_role not in ['admin']:
                return jsonify({'message': '스탬프 회수는 관리자만 가능합니다.'}), 403
            
            if not booth_id:
                return jsonify({'message': '회수할 부스 ID를 선택하세요.'}), 400
            if booth_id not in STAMP_BOOTHS:
                return jsonify({'message': '유효하지 않은 부스 ID입니다.'}), 400
            
            current_stamps[booth_id] = False
            action_text = "회수"
        
        # 데이터베이스 업데이트
        target_doc.reference.update({'stamps': current_stamps})
        
        # 업데이트된 스탬프 개수 계산
        updated_count = count_stamps(current_stamps)
        
        return jsonify({
            'message': f'{target_email}에게 {booth_id} 스탬프를 {action_text}했습니다.',
            'stamp_id': booth_id,
            'current_stamp_count': updated_count,
            'stamps': current_stamps
        }), 200
        
    except Exception as e:
        print(f"Stamps update error: {e}")
        return jsonify({'message': f'스탬프 처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/role', methods=['POST'])
@token_required
def update_role(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': '관리자만 접근 가능합니다.'}), 403
    
    data = request.json
    target_email = data.get('target_email')
    new_role = data.get('new_role')
    
    if not target_email or new_role not in ['student', 'manager', 'admin']:
        return jsonify({'message': '유효하지 않은 입력값입니다.'}), 400
    
    try:
        if not db:
            return jsonify({'message': '데이터베이스 연결에 실패했습니다.'}), 500
            
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', target_email).limit(1)
        target_docs = query.get()
        
        if not target_docs:
            return jsonify({'message': '대상 사용자를 찾을 수 없습니다.'}), 404
            
        target_doc = target_docs[0]
        target_doc.reference.update({'role': new_role})
        return jsonify({
            'message': f'{target_email}의 역할을 {new_role}로 변경했습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/users', methods=['GET'])
@token_required
def get_all_users(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': '관리자만 접근 가능합니다.'}), 403
    
    try:
        if not db:
            return jsonify({'users': []}), 200
            
        users_ref = db.collection('users')
        docs = users_ref.stream()
        users = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            if 'stamps' not in user_data:
                user_data['stamps'] = {booth: False for booth in STAMP_BOOTHS}
            users.append(user_data)
        
        return jsonify({'users': users}), 200
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/booths', methods=['GET'])
@token_required
def get_booths(current_user):
    return jsonify({'booths': STAMP_BOOTHS}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask Auth Server on port {port}...")
    app.run(debug=False, host='0.0.0.0', port=port)