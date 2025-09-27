# flask_auth_server.py (일부 코드 재확인)
@app.route('/api/login', methods=['POST'])
def login():
    id_token = request.json.get('id_token')
    if not id_token:
        return jsonify({'message': 'ID token is required'}), 400
    try:
        # Firebase Admin SDK를 사용하여 ID 토큰 검증:cite[1]
        decoded_token = auth.verify_id_token(id_token)
        user_uid = decoded_token['uid']
        email = decoded_token['email']
        name = decoded_token.get('name', '')

        # 이메일 도메인 검증 (@jeohyeon.hs.kr)
        if not email.endswith('@jeohyeon.hs.kr'):
            return jsonify({'message': '학교 구글 계정(@jeohyeon.hs.kr)으로만 로그인 가능합니다.'}), 403

        # 사용자 프로필 초기화/조회 (Firestore)
        user_profile = init_or_get_user_profile(user_uid, email, name)
        # JWT 생성 (Flask 세션용)
        jwt_token = create_jwt(user_uid, email, user_profile['role'])

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
        return jsonify({'message': f'로그인 처리 중 오류가 발생했습니다: {str(e)}'}), 500