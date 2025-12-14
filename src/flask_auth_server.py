from flask_cors import CORS
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
import jwt
import datetime
from functools import wraps
import os
import json

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

# ✅ 스탬프 ID 목록 (부스 → 스탬프로 변경)
STAMP_IDS = [f"stamp{i}" for i in range(1, 35)]

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
        stamp_id = f"stamp{i}"
        if not stamps.get(stamp_id, False):
            return stamp_id, i
    return None, None  # 모든 스탬프가 이미 부여됨

def check_manager_grant_limit(db, manager_email, target_email):
    """
    Manager가 특정 target에게 이미 스탬프를 부여했는지 확인
    
    Returns:
        tuple: (이미_부여됨: bool, 부여된_스탬프_id: str or None)
    """
    try:
        grants_ref = db.collection('stamp_grants')
        query = grants_ref.where('manager_email', '==', manager_email)\
                          .where('target_email', '==', target_email)\
                          .limit(1)
        
        existing_grants = query.get()
        
        if existing_grants:
            # 이미 부여한 적이 있음
            grant_data = existing_grants[0].to_dict()
            return True, grant_data.get('stamp_id')
        else:
            # 부여한 적 없음
            return False, None
            
    except Exception as e:
        print(f"Grant limit check error: {e}")
        return False, None

def record_stamp_grant(db, manager_email, target_email, stamp_id):
    """
    스탬프 부여 내역을 stamp_grants 컬렉션에 기록
    """
    try:
        grants_ref = db.collection('stamp_grants')
        grant_data = {
            'manager_email': manager_email,
            'target_email': target_email,
            'stamp_id': stamp_id,
            'granted_at': firestore.SERVER_TIMESTAMP
        }
        grants_ref.add(grant_data)
        return True
    except Exception as e:
        print(f"Grant record error: {e}")
        return False

db = None
if initialize_firebase():
    db = get_db()

def create_jwt(user_uid, email, role):
    payload = {
        'user_uid': user_uid,
        'email': email,
        'role': role,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
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
        default_stamps = {stamp: False for stamp in STAMP_IDS}
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
                default_stamps = {stamp: False for stamp in STAMP_IDS}
                user_data['stamps'] = default_stamps
                user_ref.update({'stamps': default_stamps})
            return user_data
        else:
            if email == '2411224@jeohyeon.hs.kr':
                role = 'admin'
            else:
                role = 'student'
            
            default_stamps = {stamp: False for stamp in STAMP_IDS}
            
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
        default_stamps = {stamp: False for stamp in STAMP_IDS}
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
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
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
        
        default_stamps = {stamp: False for stamp in STAMP_IDS}
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

# ✅ 수정된 스탬프 관리 API (Manager 제약 추가)
@app.route('/api/stamps', methods=['POST'])
@token_required
def update_stamps(current_user):
    user_role = current_user['role']
    user_email = current_user['email']  # ✅ 부여하는 사람의 이메일
    data = request.json
    target_email = data.get('target_email')
    stamp_id = data.get('stamp_id')
    action = data.get('action')
    auto_grant = data.get('auto_grant', False)
    
    if not target_email or not action:
        return jsonify({'message': 'target_email, action은 필수 입력값입니다.'}), 400
    
    try:
        if not db:
            return jsonify({'message': '데이터베이스 연결에 실패했습니다.'}), 500
            
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', target_email).limit(1)
        target_docs = query.get()
        
        if not target_docs:
            return jsonify({'message': '대상 사용자를 찾을 수 없습니다.'}), 404
            
        target_doc = target_docs[0]
        target_data = target_doc.to_dict()
        
        new_stamps = target_data.get('stamps', {})
        
        if action == 'grant':
            # ✅ 부장은 순차적 부여만 가능 + 1인당 1회 제한
            if user_role == 'manager':
                if not auto_grant:
                    return jsonify({'message': '부장은 순차적 스탬프 부여만 가능합니다.'}), 400
                
                # ✅ 핵심: Manager가 이미 이 사람에게 스탬프를 부여했는지 확인
                already_granted, previous_stamp = check_manager_grant_limit(db, user_email, target_email)
                
                if already_granted:
                    return jsonify({
                        'message': f'이미 {target_email}에게 {previous_stamp}를 부여했습니다. 각 계정에는 1개의 스탬프만 부여할 수 있습니다.'
                    }), 400
                
                next_stamp, stamp_number = get_next_stamp_number(new_stamps)
                if not next_stamp:
                    return jsonify({'message': '모든 스탬프가 이미 부여되었습니다.'}), 400
                
                stamp_id = next_stamp
                action_text = "순차적 부여"
            
            # ✅ 관리자는 특정 스탬프 또는 순차적 부여 가능 (제한 없음)
            elif user_role == 'admin':
                if auto_grant:
                    next_stamp, stamp_number = get_next_stamp_number(new_stamps)
                    if not next_stamp:
                        return jsonify({'message': '모든 스탬프가 이미 부여되었습니다.'}), 400
                    stamp_id = next_stamp
                    action_text = "순차적 부여"
                else:
                    if not stamp_id:
                        return jsonify({'message': '스탬프 ID를 선택하세요.'}), 400
                    if stamp_id not in STAMP_IDS:
                        return jsonify({'message': '유효하지 않은 스탬프 ID입니다.'}), 400
                    action_text = "특정 부여"
            else:
                return jsonify({'message': '권한이 없습니다.'}), 403
            
            # ✅ 스탬프 부여 처리
            new_stamps[stamp_id] = True
            target_doc.reference.update({'stamps': new_stamps})
            
            # ✅ Manager인 경우 부여 내역 기록 (Admin은 기록하지 않음)
            if user_role == 'manager':
                if not record_stamp_grant(db, user_email, target_email, stamp_id):
                    print(f"Warning: Failed to record grant for {user_email} -> {target_email}")
            
        else:  # revoke
            if user_role not in ['admin']:
                return jsonify({'message': '스탬프 회수는 관리자만 가능합니다.'}), 403
            
            if not stamp_id:
                return jsonify({'message': '회수할 스탬프 ID를 선택하세요.'}), 400
            if stamp_id not in STAMP_IDS:
                return jsonify({'message': '유효하지 않은 스탬프 ID입니다.'}), 400
            
            new_stamps[stamp_id] = False
            target_doc.reference.update({'stamps': new_stamps})
            
            # ✅ 회수 시 grant 기록도 삭제
            try:
                grants_ref = db.collection('stamp_grants')
                query = grants_ref.where('target_email', '==', target_email)\
                                 .where('stamp_id', '==', stamp_id)\
                                 .limit(1)
                grants_to_delete = query.get()
                for grant in grants_to_delete:
                    grant.reference.delete()
            except Exception as e:
                print(f"Grant deletion error: {e}")
            
            action_text = "회수"
        
        return jsonify({
            'message': f'{target_email}에게 {stamp_id} 스탬프를 {action_text}했습니다.',
            'stamp_id': stamp_id
        }), 200
        
    except Exception as e:
        print(f"Stamps update error: {e}")
        return jsonify({'message': str(e)}), 500

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
                user_data['stamps'] = {stamp: False for stamp in STAMP_IDS}
            users.append(user_data)
        
        return jsonify({'users': users}), 200
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/stamps', methods=['GET'])
@token_required
def get_stamps(current_user):
    return jsonify({'stamps': STAMP_IDS}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask Auth Server on port {port}...")
    app.run(debug=False, host='0.0.0.0', port=port)