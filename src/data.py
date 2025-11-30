# migrate_firestore.py
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Firebase Admin SDK 초기화
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# 스탬프 부스 목록
STAMP_BOOTHS = [f"booth{i}" for i in range(1, 35)]


def migrate_to_34_stamps():
    """기존 사용자 데이터를 34개 스탬프 시스템으로 마이그레이션"""
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        migrated_count = 0
        
        for doc in docs:
            try:
                user_data = doc.to_dict()
                current_stamps = user_data.get('stamps', {})
                
                # 새로운 34개 스탬프 구조 생성 (기존 데이터 유지)
                new_stamps = {}
                for i in range(1, 35):
                    booth_id = f"booth{i}"
                    # 기존 데이터 유지, 없는 스탬프는 False로 설정
                    new_stamps[booth_id] = current_stamps.get(booth_id, False)
                
                # 문서 업데이트
                doc.reference.update({'stamps': new_stamps})
                migrated_count += 1
                print(f"✅ {user_data.get('email', 'Unknown')} 마이그레이션 완료")
                
            except Exception as e:
                print(f"❌ {doc.id} 마이그레이션 실패: {e}")
        
        print(f"\n=== 마이그레이션 완료 ===")
        print(f"성공: {migrated_count}건")
        
    except Exception as e:
        print(f"마이그레이션 중 오류 발생: {e}")

if __name__ == '__main__':
    print("34개 스탬프 시스템으로 마이그레이션을 시작합니다...")
    migrate_to_34_stamps()

def check_migration():
    """마이그레이션 결과 확인"""
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        has_stamps = 0
        has_honyangi = 0
        total = 0
        
        for doc in docs:
            user_data = doc.to_dict()
            total += 1
            
            if 'stamps' in user_data:
                has_stamps += 1
            if 'honyangi' in user_data:
                has_honyangi += 1
        
        print(f"\n=== 마이그레이션 현황 ===")
        print(f"전체 사용자: {total}명")
        print(f"스탬프 필드 보유: {has_stamps}명 ({has_stamps/total*100:.1f}%)")
        print(f"호냥이 필드 보유: {has_honyangi}명 ({has_honyangi/total*100:.1f}%)")
        
    except Exception as e:
        print(f"확인 중 오류 발생: {e}")

if __name__ == '__main__':
    print("Firestore 데이터 마이그레이션을 시작합니다...")
    
    # 먼저 현재 상태 확인
    check_migration()
    
    # 사용자 입력 받기
    response = input("\n마이그레이션을 진행하시겠습니까? (y/N): ")
    
    if response.lower() == 'y':
        migrate_users()
        print("\n마이그레이션 후 현황:")
        check_migration()
    else:
        print("마이그레이션이 취소되었습니다.")