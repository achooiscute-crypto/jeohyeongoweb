"""
Firestore 데이터베이스 마이그레이션 스크립트
booth1-34 → stamp1-34 변환 및 데이터 구조 정리
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

# Firebase Admin SDK 초기화
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# 스탬프 ID 목록
STAMP_IDS = [f"stamp{i}" for i in range(1, 35)]

def migrate_booth_to_stamp():
    """
    booth1-34를 stamp1-34로 변환
    """
    print("\n" + "="*60)
    print("🔄 스탬프 ID 마이그레이션 시작 (booth → stamp)")
    print("="*60)
    
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for doc in docs:
            try:
                user_data = doc.to_dict()
                email = user_data.get('email', 'Unknown')
                current_stamps = user_data.get('stamps', {})
                
                # booth로 시작하는 키가 있는지 확인
                has_booth_keys = any(key.startswith('booth') for key in current_stamps.keys())
                
                if not has_booth_keys:
                    print(f"⏭️  {email} - 이미 마이그레이션 완료 (스킵)")
                    skipped_count += 1
                    continue
                
                # 새로운 스탬프 구조 생성
                new_stamps = {}
                for i in range(1, 35):
                    old_key = f"booth{i}"
                    new_key = f"stamp{i}"
                    
                    # 기존 데이터가 있으면 유지, 없으면 False
                    new_stamps[new_key] = current_stamps.get(old_key, False)
                
                # 문서 업데이트
                doc.reference.update({'stamps': new_stamps})
                
                # 진행 상황 표시
                stamp_count = sum(1 for v in new_stamps.values() if v)
                print(f"✅ {email} - {stamp_count}개 스탬프 마이그레이션 완료")
                migrated_count += 1
                
            except Exception as e:
                print(f"❌ {doc.id} 마이그레이션 실패: {e}")
                error_count += 1
        
        print("\n" + "="*60)
        print("📊 마이그레이션 결과")
        print("="*60)
        print(f"✅ 성공: {migrated_count}건")
        print(f"⏭️  스킵: {skipped_count}건 (이미 완료)")
        print(f"❌ 실패: {error_count}건")
        print("="*60)
        
        return migrated_count, skipped_count, error_count
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 중 치명적 오류 발생: {e}")
        return 0, 0, 0

def clean_database_structure():
    """
    데이터베이스 구조 정리 및 검증
    - created_at 필드 추가 (없는 경우)
    - stamps 필드 검증 및 정리
    """
    print("\n" + "="*60)
    print("🧹 데이터베이스 구조 정리 시작")
    print("="*60)
    
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        cleaned_count = 0
        
        for doc in docs:
            try:
                user_data = doc.to_dict()
                email = user_data.get('email', 'Unknown')
                updates = {}
                
                # 1. created_at 필드 추가
                if 'created_at' not in user_data:
                    updates['created_at'] = firestore.SERVER_TIMESTAMP
                
                # 2. stamps 필드 검증
                stamps = user_data.get('stamps', {})
                
                # 모든 stamp1-34가 있는지 확인
                missing_stamps = []
                for i in range(1, 35):
                    stamp_id = f"stamp{i}"
                    if stamp_id not in stamps:
                        missing_stamps.append(stamp_id)
                        stamps[stamp_id] = False
                
                if missing_stamps:
                    updates['stamps'] = stamps
                    print(f"🔧 {email} - 누락된 스탬프 추가: {len(missing_stamps)}개")
                
                # 업데이트 실행
                if updates:
                    doc.reference.update(updates)
                    cleaned_count += 1
                    print(f"✅ {email} - 구조 정리 완료")
                
            except Exception as e:
                print(f"❌ {doc.id} 정리 실패: {e}")
        
        print("\n" + "="*60)
        print(f"✅ 구조 정리 완료: {cleaned_count}건")
        print("="*60)
        
        return cleaned_count
        
    except Exception as e:
        print(f"\n❌ 구조 정리 중 오류 발생: {e}")
        return 0

def verify_migration():
    """
    마이그레이션 결과 검증
    """
    print("\n" + "="*60)
    print("🔍 마이그레이션 결과 검증")
    print("="*60)
    
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        total_users = 0
        has_stamps = 0
        has_booth = 0
        complete_stamps = 0
        
        user_details = []
        
        for doc in docs:
            user_data = doc.to_dict()
            total_users += 1
            
            email = user_data.get('email', 'Unknown')
            stamps = user_data.get('stamps', {})
            
            # stamps 필드 체크
            if stamps:
                has_stamps += 1
                
                # booth 키 체크
                has_booth_keys = any(key.startswith('booth') for key in stamps.keys())
                if has_booth_keys:
                    has_booth += 1
                
                # 완전한 stamp1-34 체크
                has_all_stamps = all(f"stamp{i}" in stamps for i in range(1, 35))
                if has_all_stamps:
                    complete_stamps += 1
                
                # 스탬프 개수 계산
                stamp_count = sum(1 for v in stamps.values() if v)
                user_details.append({
                    'email': email,
                    'role': user_data.get('role', 'student'),
                    'stamp_count': stamp_count,
                    'has_booth': has_booth_keys,
                    'complete': has_all_stamps
                })
        
        print(f"\n전체 사용자: {total_users}명")
        print(f"stamps 필드 보유: {has_stamps}명")
        print(f"booth 키 잔존: {has_booth}명 {'⚠️  (마이그레이션 필요)' if has_booth > 0 else '✅'}")
        print(f"완전한 stamp1-34 구조: {complete_stamps}명")
        
        print("\n" + "-"*60)
        print("사용자별 상세 현황:")
        print("-"*60)
        
        for user in sorted(user_details, key=lambda x: x['email']):
            status = ""
            if user['has_booth']:
                status = "⚠️  booth 잔존"
            elif not user['complete']:
                status = "⚠️  불완전"
            else:
                status = "✅ 정상"
            
            print(f"{user['email']:40} | {user['role']:10} | {user['stamp_count']:2}개 | {status}")
        
        print("="*60)
        
        return has_booth == 0 and complete_stamps == total_users
        
    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {e}")
        return False

def backup_current_state():
    """
    현재 상태를 JSON 파일로 백업
    """
    print("\n" + "="*60)
    print("💾 현재 상태 백업 중...")
    print("="*60)
    
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        backup_data = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data['doc_id'] = doc.id
            # Timestamp를 문자열로 변환
            if 'created_at' in user_data:
                user_data['created_at'] = str(user_data['created_at'])
            backup_data.append(user_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"firestore_backup_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 백업 완료: {filename}")
        print(f"   총 {len(backup_data)}명의 사용자 데이터 백업됨")
        
        return filename
        
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return None

def main():
    """
    마이그레이션 메인 프로세스
    """
    print("\n" + "🏫 " + "="*54 + " 🏫")
    print("      학교 스탬프 시스템 데이터베이스 마이그레이션")
    print("🏫 " + "="*54 + " 🏫\n")
    
    # 1. 현재 상태 검증
    print("STEP 1: 현재 상태 확인")
    verify_migration()
    
    # 2. 백업
    print("\nSTEP 2: 백업 생성")
    backup_file = backup_current_state()
    
    if not backup_file:
        print("\n⚠️  백업 생성에 실패했습니다.")
        response = input("백업 없이 계속 진행하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("마이그레이션을 취소합니다.")
            return
    
    # 3. 사용자 확인
    print("\n" + "="*60)
    response = input("\n마이그레이션을 시작하시겠습니까? (y/N): ")
    
    if response.lower() != 'y':
        print("마이그레이션을 취소했습니다.")
        return
    
    # 4. booth → stamp 마이그레이션
    print("\nSTEP 3: booth → stamp 변환")
    migrated, skipped, errors = migrate_booth_to_stamp()
    
    # 5. 데이터베이스 구조 정리
    print("\nSTEP 4: 데이터베이스 구조 정리")
    cleaned = clean_database_structure()
    
    # 6. 최종 검증
    print("\nSTEP 5: 최종 검증")
    success = verify_migration()
    
    # 7. 결과 요약
    print("\n" + "="*60)
    print("🎉 마이그레이션 완료!")
    print("="*60)
    print(f"변환: {migrated}건")
    print(f"스킵: {skipped}건")
    print(f"오류: {errors}건")
    print(f"정리: {cleaned}건")
    print(f"최종 상태: {'✅ 성공' if success else '⚠️  확인 필요'}")
    
    if backup_file:
        print(f"\n💾 백업 파일: {backup_file}")
        print("   문제 발생 시 이 파일로 복구 가능합니다.")
    
    print("="*60)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()