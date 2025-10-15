import pymysql
import requests
import os
from dotenv import load_dotenv
import time # 🌟 누락된 time 모듈 추가

# .env 파일에서 환경 변수를 로드합니다. (pip install python-dotenv 필요)
load_dotenv() 

# 🚨 Google Maps API 키를 환경 변수에서 가져옵니다.
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY") 

# -------------------------------
# 1️⃣ DB 연결 설정
# -------------------------------
def connect_mysql():
    """MySQL 데이터베이스에 연결합니다."""
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="1234", # 🚨 실제 MySQL 비밀번호로 변경하세요
            database="performance", 
            charset="utf8mb4"
        )
        return conn
    except pymysql.err.OperationalError as e:
        print(f"❌ MySQL 연결 실패: {e}")
        print("💡 MySQL 서버가 실행 중인지, 비밀번호와 DB 이름이 올바른지 확인해주세요.")
        return None

# -------------------------------
# 2️⃣ Geocoding API 함수
# -------------------------------
def get_coordinates_from_place(place_name):
    """장소 이름을 Google Geocoding API를 이용해 위도와 경도로 변환합니다."""
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ API 키가 설정되지 않아 Geocoding을 수행할 수 없습니다.")
        return None, None
    
    # 🌟 검색 정확도 향상을 위해 한국 주소 정보를 추가하고 언어를 한국어로 설정
    full_address = f"{place_name}, Seoul, South Korea, 공연장" 

    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": full_address,
        "key": GOOGLE_MAPS_API_KEY,
        "region": "kr", 
        "language": "ko"
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()

        data = response.json()
        
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        
        elif data['status'] == 'ZERO_RESULTS':
             print(f"   [Geo] 🔴 결과 없음: {place_name}")
             return None, None
        
        else:
            print(f"   [Geo] ❌ API 오류 ({data['status']}): {place_name}")
            return None, None

    except requests.exceptions.RequestException as e:
        print(f"   [Geo] ❌ 요청 오류: {e}")
        return None, None

# -------------------------------
# 3️⃣ DB 테이블 수정 (Duplicate column name 오류 처리 포함)
# -------------------------------
def alter_table():
    conn = connect_mysql()
    if not conn:
        return

    cursor = conn.cursor()

    # ✅ latitude 컬럼 추가 (중복 시 무시)
    try:
        cursor.execute("ALTER TABLE musical_perform ADD COLUMN latitude DECIMAL(10,8) NULL")
        print("✅ latitude 칼럼 추가 완료.")
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1060:
            print("⚠️ latitude 칼럼 이미 존재 -> 건너뜀")
        else:
            raise e

    # ✅ longitude 컬럼 추가 (중복 시 무시)
    try:
        cursor.execute("ALTER TABLE musical_perform ADD COLUMN longitude DECIMAL(11,8) NULL")
        print("✅ longitude 칼럼 추가 완료.")
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1060:
            print("⚠️ longitude 칼럼 이미 존재 -> 건너뜀")
        else:
            raise e

    conn.commit()
    cursor.close()
    conn.close()

# -------------------------------
# 4️⃣ 지오코딩 실행 및 DB 업데이트
# -------------------------------
def update_geocodes():
    conn = connect_mysql()
    if not conn:
        return
        
    # DictCursor를 사용하여 칼럼 이름으로 데이터를 가져옵니다.
    cursor = conn.cursor(pymysql.cursors.DictCursor) 
    update_count = 0
    
    # 🌟 1. place 데이터가 있고, 위도(latitude)가 NULL인 레코드만 조회
    cursor.execute("""
        SELECT id, place FROM musical_perform 
        WHERE place IS NOT NULL AND latitude IS NULL
    """)
    records = cursor.fetchall()
    
    print(f"\n🔍 총 {len(records)}개의 미변환 레코드를 찾았습니다. 지오코딩을 시작합니다.")

    for record in records:
        place_name = record['place']
        record_id = record['id']
        
        # 🌟 2. 지오코딩 수행
        latitude, longitude = get_coordinates_from_place(place_name)
        
        if latitude is not None and longitude is not None:
            # 🌟 3. DB 업데이트
            cursor.execute("""
                UPDATE musical_perform 
                SET latitude = %s, longitude = %s 
                WHERE id = %s
            """, (latitude, longitude, record_id))
            
            update_count += 1
            print(f"   [OK] #{record_id}: {place_name} -> {latitude}, {longitude}")
        
        # API 사용량 제한을 위해 잠시 대기
        time.sleep(0.2) 

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n🎉 총 {update_count}개 레코드 업데이트 완료.")

# -------------------------------
# 5️⃣ 실행
# -------------------------------
if __name__ == "__main__":
    # 1. 테이블 칼럼 추가/확인
    alter_table() 
    
    # 2. 지오코딩 실행 및 업데이트
    update_geocodes()