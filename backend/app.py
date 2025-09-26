# backend/app.py
import os
import json
from flask import Flask, redirect, request, session, jsonify, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import firebase_admin
from firebase_admin import credentials, auth, firestore
from dotenv import load_dotenv
from functools import wraps
import datetime

load_dotenv()  # .env에서 설정 불러오기

# ---------- 환경변수 필요 ----------
GOOGLE_CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secret.json")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:5000/oauth2callback")
SERVICE_ACCOUNT_FILE = os.getenv("FIREBASE_SERVICE_ACCOUNT", "serviceAccountKey.json")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", "jeohyeon.hs.kr")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:5000")
STREAMLIT_BASE_URL = os.getenv("STREAMLIT_BASE_URL", "http://localhost:8501")

# ---------- Flask 세팅 ----------
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# ---------- Firebase Admin 초기화 ----------
cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------- 유틸 데코레이터 ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session:
            return jsonify({"error": "not-authenticated"}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get("uid")
        if not uid:
            return jsonify({"error":"not-authenticated"}), 401
        user = auth.get_user(uid)
        claims = user.custom_claims or {}
        if claims.get("role") != "admin":
            return jsonify({"error":"admin-required"}), 403
        return f(*args, **kwargs)
    return decorated

# ---------- OAuth 시작 지점 ----------
@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=["openid", "email", "profile"],
        redirect_uri=OAUTH_REDIRECT_URI
    )
    # hd 파라미터는 'hosted domain'으로 로그인 화면 필터링에 도움된다(서버측 확인 병행 필요)
    auth_url, state = flow.authorization_url(prompt='consent', include_granted_scopes='true', hd=ALLOWED_DOMAIN)
    session['oauth_state'] = state
    return redirect(auth_url)

# ---------- OAuth 콜백 ----------
@app.route("/oauth2callback")
def oauth2callback():
    state = session.get('oauth_state')
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=["openid", "email", "profile"],
        state=state,
        redirect_uri=OAUTH_REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    # id_token 검증 및 정보 추출
    try:
        idinfo = id_token.verify_oauth2_token(creds._id_token, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception as e:
        return f"Invalid token: {e}", 400

    email = idinfo.get("email")
    if not email or not email.endswith(f"@{ALLOWED_DOMAIN}"):
        return "허용되지 않은 도메인의 계정입니다.", 403

    # Firebase Auth 사용자 존재 확인/생성
    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        user = auth.create_user(email=email, display_name=idinfo.get("name"))

    # Firestore users 문서 생성/갱신 (username은 빈값)
    db.collection("users").document(user.uid).set({
        "uid": user.uid,
        "email": email,
        "displayName": idinfo.get("name"),
        "username": "",  # 사용자가 Streamlit에서 설정
        "createdAt": firestore.SERVER_TIMESTAMP
    }, merge=True)

    # 세션에 uid 저장 (간단한 방식)
    session['uid'] = user.uid
    session['email'] = email
    # Redirect to Streamlit app
    return redirect(STREAMLIT_BASE_URL)

# ---------- 간단한 로그아웃 ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(STREAMLIT_BASE_URL)

# ---------- whoami : 현재 로그인 사용자 정보 반환 ----------
@app.route("/whoami")
@login_required
def whoami():
    uid = session['uid']
    user = auth.get_user(uid)
    # custom claims을 UI에 보여주려면 서버측에서 불러옴 (주의: 민감정보 주의)
    claims = user.custom_claims or {}
    # Firestore user doc
    doc = db.collection("users").document(uid).get()
    data = doc.to_dict() if doc.exists else {}
    return jsonify({
        "uid": uid,
        "email": user.email,
        "displayName": user.display_name,
        "claims": claims,
        "profile": data
    })

# ---------- stamp 생성 엔드포인트 (leader/admin만 가능) ----------
@app.route("/stamp", methods=["POST"])
@login_required
def stamp():
    payload = request.json or {}
    target_email = payload.get("target_email")
    note = payload.get("note", "")
    if not target_email:
        return jsonify({"error":"target_email required"}), 400

    # 요청자 권한 확인(서버측 재검증)
    requester_uid = session['uid']
    requester = auth.get_user(requester_uid)
    role = (requester.custom_claims or {}).get("role", "student")
    if role not in ("leader", "admin"):
        return jsonify({"error":"permission denied"}), 403

    # 대상 확인 (email -> uid)
    try:
        target = auth.get_user_by_email(target_email)
    except auth.UserNotFoundError:
        return jsonify({"error":"target not found"}), 404

    # Firestore에 stamp 저장
    board_id = payload.get("board_id", "default_board")
    stamp_doc = {
        "stamper_uid": requester_uid,
        "stamper_display": requester.display_name,
        "target_uid": target.uid,
        "target_email": target.email,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "note": note,
        "board_id": board_id
    }
    db.collection("stampboards").document(board_id).collection("stamps").add(stamp_doc)
    return jsonify({"ok": True}), 201

# ---------- 관리자 전용: role 부여/회수 ----------
@app.route("/set_role", methods=["POST"])
@login_required
@admin_required
def set_role():
    payload = request.json or {}
    target_email = payload.get("target_email")
    role = payload.get("role")  # 'student'|'leader'|'admin'
    if role not in ("student","leader","admin"):
        return jsonify({"error":"invalid role"}), 400
    try:
        target = auth.get_user_by_email(target_email)
    except auth.UserNotFoundError:
        return jsonify({"error":"target not found"}), 404

    # custom claims 설정 (서버에서만)
    auth.set_custom_user_claims(target.uid, {"role": role})
    # Firestore profile에도 role 저장(편의용)
    db.collection("users").document(target.uid).set({"role": role}, merge=True)
    return jsonify({"ok": True}), 200

# ---------- 간단 헬스체크 ----------
@app.route("/health")
def health():
    return "ok"

if __name__ == "__main__":
    # 개발용: debug=True(운영 시 False)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
