# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일에서 환경 변수 로드

# 서비스 계정 키 파일이 있는 경우 해당 경로를, 없는 경우 환경 변수를 사용합니다.
if not firebase_admin._apps:
    try:
        # 옵션 1: 서비스 계정 키 JSON 파일 사용 (권장)
        cred = credentials.Certificate("../serviceAccountKey.json")
    except FileNotFoundError:
        # 옵션 2: 환경 변수를 사용한 초기화 사실 여기는 별의미는 없습니다.
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

# Firestore 클라이언트를 반환하는 함수
def get_db():
    db = firestore.client()
    return db