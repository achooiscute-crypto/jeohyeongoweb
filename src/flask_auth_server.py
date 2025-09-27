# flask_auth_server.py
from flask import Flask, request, jsonify, session, redirect, url_for
import firebase_admin
from firebase_admin import credentials, auth, firestore
import jwt
import datetime
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

# Flask 앱 생성 (가장 먼저 정의)
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key-for-development')

# Firebase Admin SDK 초기화
def initialize_firebase():
    try:
        # 서비스 계정 키 파일로 초기화 시도
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized with service account key")
    except FileNotFoundError:
        try:
            # 환경 변수를 통한 초기화 시도
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized with application default credentials")
        except Exception as e:
            print(f"Firebase initialization failed: {e}")
            # 테스트를 위한 더미 초기화 (실제 배포 시 제거)
            print("Warning: Using dummy Firebase setup for testing")

# Firestore 클라이언트 얻기
def get_db():
    try:
        db = firestore.client()
        return db
    except Exception as e:
        print(f"Firestore client error: {e}")
        return None

# Firebase 초기화 실행
initialize_firebase()
db = get_db()

# JWT 생성 함수
def create_jwt(user_uid, email, role):
    payload = {
        'user_uid': user_uid,
        'email': email,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    try:
        token = jwt.encode(payload, app.secret_key, algorithm='HS256')
        return token
    except Exception as e:
        print(f"JWT creation error: {e}")
        return None

# JWT 검증 데코레이터
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

# 사용자 프로필 초기화/조회 함수
def init_or_get_user_profile(user_uid, email, name):
    if not db:
        return {'email': email, 'display_name': name, 'honyangi': 100, 'role': 'student'}
    
    try:
        user_ref = db.collection('users').document(user_uid)
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return user_data
        else:
            # 새 사용자 생성
            new_user = {
                'email': email,
                'display_name': name or email.split('@')[0],
                'honyangi': 100,
                'role': 'student',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_ref.set(new_user)
            return new_user
    except Exception as e:
        print(f"User profile error: {e}")
        # 오류 발생 시 기본값 반환
        return {'email': email, 'display_name': name, 'honyangi': 100, 'role': 'student'}

# 라우트 정의 (app이 정의된 후에)
@app.route('/')
def home():
    return jsonify({'message': 'Flask Auth Server is running!'})

@app.route('/api/login', methods=['POST'])
def login():
    id_token = request.json.get('id_token')
    if not id_token:
        return jsonify({'message': 'ID token is required'}), 400
    
    try:
        # Firebase ID 토큰 검증
        decoded_token = auth.verify_id_token(id_token)
        user_uid = decoded_token['uid']
        email = decoded_token['email']
        name = decoded_token.get('name', '')

        # 이메일 도메인 검증
        if not email.endswith('@jeohyeon.hs.kr'):
            return jsonify({'message': '학교 구글 계정(@jeohyeon.hs.kr)으로만 로그인 가능합니다.'}), 403

        # 사용자 프로필 처리
        user_profile = init_or_get_user_profile(user_uid, email, name)
        
        # JWT 생성
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
                'honyangi': user_profile['honyangi']
            }
        }), 200
        
    except auth.ExpiredIdTokenError:
        return jsonify({'message': '로그인 세션이 만료되었습니다.'}), 401
    except auth.InvalidIdTokenError:
        return jsonify({'message': '유효하지 않은 로그인 정보입니다.'}), 401
    except Exception as e:
        print(f"Login error: {e}")
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
        
        # DB에 없거나 오류 시 현재 사용자 정보 반환
        return jsonify({
            'user': {
                'email': current_user['email'],
                'display_name': current_user.get('display_name', current_user['email'].split('@')[0]),
                'role': current_user['role'],
                'honyangi': 100
            }
        }), 200
        
    except Exception as e:
        print(f"Profile error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/api/profile', methods=['POST'])
@token_required
def update_profile(current_user):
    try:
        data = request.json
        new_display_name = data.get('display_name')
        if not new_display_name:
            return jsonify({'message': '표시 이름을 입력하세요.'}), 400
        
        user_uid = current_user['user_uid']
        if db:
            user_ref = db.collection('users').document(user_uid)
            user_ref.update({'display_name': new_display_name})
        
        return jsonify({'message': '이름이 성공적으로 변경되었습니다.'}), 200
    except Exception as e:
        print(f"Profile update error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/api/honyangi', methods=['POST'])
@token_required
def update_honyangi(current_user):
    if current_user['role'] not in ['manager', 'admin']:
        return jsonify({'message': '권한이 없습니다.'}), 403
    
    data = request.json
    target_email = data.get('target_email')
    amount = data.get('amount')
    
    if not target_email or amount is None:
        return jsonify({'message': 'target_email과 amount는 필수 입력값입니다.'}), 400
    
    try:
        if not db:
            return jsonify({'message': '데이터베이스 연결에 실패했습니다.'}), 500
            
        # 대상 사용자 조회
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', target_email).limit(1)
        target_docs = query.get()
        
        if not target_docs:
            return jsonify({'message': '대상 사용자를 찾을 수 없습니다.'}), 404
            
        target_doc = target_docs[0]
        target_data = target_doc.to_dict()
        new_amount = target_data.get('honyangi', 0) + amount
        
        # 호냥이 음수 방지
        if new_amount < 0:
            return jsonify({'message': '호냥이는 0보다 작아질 수 없습니다.'}), 400
            
        target_doc.reference.update({'honyangi': new_amount})
        return jsonify({
            'message': f'{target_email}의 호냥이를 {amount} 변경했습니다. 현재: {new_amount}'
        }), 200
        
    except Exception as e:
        print(f"Honyangi update error: {e}")
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
        print(f"Role update error: {e}")
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
            users.append(user_data)
        
        return jsonify({'users': users}), 200
        
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask Auth Server...")
    print(f"Secret key set: {bool(app.secret_key)}")
    app.run(debug=True, port=5000, host='0.0.0.0')