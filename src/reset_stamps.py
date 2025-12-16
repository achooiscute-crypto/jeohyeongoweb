"""
Firestore 스탬프 및 grant 기록 완전 초기화 스크립트
모든 사용자의 스탬프를 0으로 리셋하고 부여 이력을 삭제합니다.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Firebase Admin SDK 초기화
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# 스탬프 ID 목록
STAMP_IDS = [f"stamp{i}" for i in range(1, 35)]

def reset_all_user_stamps():
    """
    모든 사용자의 스탬프를 False로 초기화
    """
    print("\n" + "="*60)
    print("🔄 사용자 스탬프 초기화 시작")
    print("="*60)
    
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        reset_count = 0
        default_stamps = {stamp: False for stamp in STAMP_IDS}
        
        for doc in docs:
            try:
                user_data = doc.to_dict()
                email = user_data.get('email', 'Unknown')
                
                # 스탬프를 모두 False로 설정
                doc.reference.update({'stamps': default_stamps})
                
                reset_count += 1
                print(f"✅ {email} - 스탬프 초기화 완료")
                
            except Exception as e:
                print(f"❌ {doc.id} 초기화 실패: {e}")
        
        print("\n" + "="*60)
        print(f"✅ 사용자 스탬프 초기화 완료: {reset_count}명")
        print("="*60)
        
        return reset_count
        
    except Exception as e:
        print(f"\n❌ 사용자 스탬프 초기화 중 오류: {e}")
        return 0

def delete_all_stamp_grants():
    """
    stamp_grants 컬렉션의 모든 문서 삭제
    """
    print("\n" + "="*60)
    print("🗑️  stamp_grants 기록 삭제 시작")
    print("="*60)
    
    try:
        grants_ref = db.collection('stamp_grants')
        docs = grants_ref.stream()
        
        delete_count = 0
        
        for doc in docs:
            try:
                grant_data = doc.to_dict()
                manager = grant_data.get('manager_email', 'Unknown')
                target = grant_data.get('target_email', 'Unknown')
                stamp_id = grant_data.get('stamp_id', 'Unknown')
                
                # 문서 삭제
                doc.reference.delete()
                
                delete_count += 1
                print(f"🗑️  {manager} → {target} ({stamp_id}) 삭제")
                
            except Exception as e:
                print(f"❌ {doc.id} 삭제 실패: {e}")
        
        print("\n" + "="*60)
        print(f"✅ stamp_grants 기록 삭제 완료: {delete_count}건")
        print("="*60)
        
        return delete_count
        
    except Exception as e:
        print(f"\n❌ stamp_grants 삭제 중 오류: {e}")
        return 0

def verify_reset():
    """
    초기화 결과 검증
    """
    print("\n" + "="*60)
    print("🔍 초기화 결과 검증")
    print("="*60)
    
    try:
        # 사용자 스탬프 확인
        users_ref = db.collection('users')
        users = users_ref.stream()
        
        total_users = 0
        users_with_stamps = 0
        
        for user_doc in users:
            user_data = user_doc.to_dict()
            total_users += 1
            
            stamps = user_data.get('stamps', {})
            stamp_count = sum(1 for has_stamp in stamps.values() if has_stamp)
            
            if stamp_count > 0:
                users_with_stamps += 1
                email = user_data.get('email', 'Unknown')
                print(f"⚠️  {email} - 아직 {stamp_count}개 스탬프 보유")
        
        # stamp_grants 확인
        grants_ref = db.collection('stamp_grants')
        grants = grants_ref.stream()
        remaining_grants = sum(1 for _ in grants)
        
        print("\n" + "-"*60)
        print(f"전체 사용자: {total_users}명")
        print(f"스탬프 보유 사용자: {users_with_stamps}명")
        print(f"남은 grant 기록: {remaining_grants}건")
        print("-"*60)
        
        if users_with_stamps == 0 and remaining_grants == 0:
            print("\n✅ 모든 기록이 성공적으로 초기화되었습니다!")
            return True
        else:
            print("\n⚠️  일부 기록이 남아있습니다. 다시 확인하세요.")
            return False
        
    except Exception as e:
        print(f"\n❌ 검증 중 오류: {e}")
        return False

def backup_before_reset():
    """
    초기화 전 현재 상태 백업
    """
    print("\n" + "="*60)
    print("💾 초기화 전 백업 생성")
    print("="*60)
    
    try:
        import json
        
        # 사용자 데이터 백업
        users_ref = db.collection('users')
        users = users_ref.stream()
        
        backup_data = {
            'users': [],
            'grants': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for user_doc in users:
            user_data = user_doc.to_dict()
            user_data['doc_id'] = user_doc.id
            if 'created_at' in user_data:
                user_data['created_at'] = str(user_data['created_at'])
            backup_data['users'].append(user_data)
        
        # grant 데이터 백업
        grants_ref = db.collection('stamp_grants')
        grants = grants_ref.stream()
        
        for grant_doc in grants:
            grant_data = grant_doc.to_dict()
            grant_data['doc_id'] = grant_doc.id
            if 'granted_at' in grant_data:
                grant_data['granted_at'] = str(grant_data['granted_at'])
            backup_data['grants'].append(grant_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_before_reset_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 백업 완료: {filename}")
        print(f"   사용자: {len(backup_data['users'])}명")
        print(f"   grant 기록: {len(backup_data['grants'])}건")
        
        return filename
        
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return None

def main():
    """
    메인 실행 함수
    """
    print("\n" + "🚨 " + "="*54 + " 🚨")
    print("      스탬프 시스템 완전 초기화 스크립트")
    print("🚨 " + "="*54 + " 🚨\n")
    
    print("⚠️  경고: 이 작업은 되돌릴 수 없습니다!")
    print("   - 모든 사용자의 스탬프가 0으로 초기화됩니다")
    print("   - 모든 stamp_grants 기록이 삭제됩니다\n")
    
    # 1. 백업 생성
    print("STEP 1: 현재 상태 백업")
    backup_file = backup_before_reset()
    
    if not backup_file:
        print("\n⚠️  백업 생성에 실패했습니다.")
        response = input("백업 없이 계속 진행하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("초기화를 취소합니다.")
            return
    
    # 2. 최종 확인
    print("\n" + "="*60)
    print("정말로 모든 스탬프 기록을 초기화하시겠습니까?")
    print("이 작업은 되돌릴 수 없습니다!")
    print("="*60)
    
    confirmation = input("\n계속하려면 'YES'를 정확히 입력하세요: ")
    
    if confirmation != 'YES':
        print("\n❌ 초기화를 취소했습니다.")
        return
    
    # 3. 사용자 스탬프 초기화
    print("\nSTEP 2: 사용자 스탬프 초기화")
    user_count = reset_all_user_stamps()
    
    # 4. grant 기록 삭제
    print("\nSTEP 3: stamp_grants 기록 삭제")
    grant_count = delete_all_stamp_grants()
    
    # 5. 검증
    print("\nSTEP 4: 초기화 결과 검증")
    success = verify_reset()
    
    # 6. 결과 요약
    print("\n" + "="*60)
    print("🎉 초기화 작업 완료!")
    print("="*60)
    print(f"사용자 스탬프 초기화: {user_count}명")
    print(f"grant 기록 삭제: {grant_count}건")
    print(f"최종 상태: {'✅ 성공' if success else '⚠️  확인 필요'}")
    
    if backup_file:
        print(f"\n💾 백업 파일: {backup_file}")
        print("   필요시 이 파일로 복구할 수 있습니다.")
    
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