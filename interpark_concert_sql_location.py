import pymysql
import requests
import os
from dotenv import load_dotenv
import time

# .env 파일에서 환경 변수를 로드
load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")


# -------------------------------
# 1️⃣ DB 연결 설정
# -------------------------------
def connect_mysql():
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="1234",
            database="performance",
            charset="utf8mb4"
        )
        return conn
    except pymysql.err.OperationalError as e:
        print(f"❌ MySQL 연결 실패: {e}")
        print("💡 MySQL 서버 / 계정 / 비밀번호 / DB 이름 확인 필요")
        return None


# -------------------------------
# 2️⃣ Google Geocoding API 호출
# -------------------------------
def get_coordinates_from_place(place_name):
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ API 키 없음")
        return None, None

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
# 3️⃣ concert_perform 테이블에 칼럼 추가
# -------------------------------
def alter_table():
    conn = connect_mysql()
    if not conn:
        return

    cursor = conn.cursor()

    # ✅ latitude 추가
    try:
        cursor.execute("""
            ALTER TABLE concert_perform 
            ADD COLUMN latitude DECIMAL(10,8) NULL
        """)
        print("✅ latitude 칼럼 추가 완료.")
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1060:  # Duplicate column
            print("⚠️ latitude 칼럼 이미 존재 -> 건너뜀")
        else:
            raise e

    # ✅ longitude 추가
    try:
        cursor.execute("""
            ALTER TABLE concert_perform 
            ADD COLUMN longitude DECIMAL(11,8) NULL
        """)
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
# 4️⃣ 지오코딩 후 DB 업데이트
# -------------------------------
def update_geocodes():
    conn = connect_mysql()
    if not conn:
        return

    cursor = conn.cursor(pymysql.cursors.DictCursor)
    update_count = 0

    # ✅ place가 있고, 위도/경도가 NULL인 행만 조회
    cursor.execute("""
        SELECT id, place 
        FROM concert_perform
        WHERE place IS NOT NULL AND latitude IS NULL
    """)
    records = cursor.fetchall()

    print(f"\n🔍 총 {len(records)}개의 미변환 레코드 → 지오코딩 시작")

    for record in records:
        place_name = record['place']
        record_id = record['id']

        latitude, longitude = get_coordinates_from_place(place_name)

        if latitude is not None and longitude is not None:
            cursor.execute("""
                UPDATE concert_perform
                SET latitude = %s, longitude = %s
                WHERE id = %s
            """, (latitude, longitude, record_id))
            update_count += 1
            print(f"   [OK] #{record_id}: {place_name} -> {latitude}, {longitude}")

        time.sleep(0.2)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n🎉 총 {update_count}개 레코드 업데이트 완료.")


# -------------------------------
# 5️⃣ 실행
# -------------------------------
if __name__ == "__main__":
    alter_table()
    update_geocodes()
