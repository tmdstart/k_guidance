from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pymysql # 🌟 MySQL 연결 모듈 추가
from datetime import datetime
import re # 🌟 정규표현식 모듈 추가 (날짜 전처리용)

# -------------------------------
# 1️⃣ MySQL 연결 및 테이블 생성
# -------------------------------
def connect_mysql():
    """MySQL 데이터베이스에 연결합니다."""
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="1234", # 🚨 실제 MySQL 비밀번호로 변경하세요
            database="performance", # 🚨 데이터베이스 이름 확인
            charset="utf8mb4"
        )
        return conn
    except pymysql.err.OperationalError as e:
        print(f"❌ MySQL 연결 실패: {e}")
        print("💡 MySQL 서버가 실행 중인지, 비밀번호와 DB 이름이 올바른지 확인해주세요.")
        return None

def create_tables():
    """크롤링 데이터를 저장할 테이블을 생성합니다."""
    conn = connect_mysql()
    if not conn:
        return

    cursor = conn.cursor()
    
    # 🌟 performance DB의 'musical_perform' 테이블 생성/확인
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musical_perform (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            start_date DATE,
            end_date DATE,
            place VARCHAR(255),
            image TEXT,
            link TEXT
        ) CHARACTER SET utf8mb4;
    """)
    
    # 🌟 실패 데이터를 저장할 'musical_fail' 테이블 생성/확인
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musical_fail (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            date_raw VARCHAR(255),  -- 원본 날짜 문자열 저장을 위해 추가
            place VARCHAR(255),
            error_msg TEXT
        ) CHARACTER SET utf8mb4;
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 테이블 생성 완료")

# -------------------------------
# 2️⃣ Selenium 초기 설정 (유지)
# -------------------------------
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")   
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# -------------------------------
# 3️⃣ 날짜 전처리 함수 (Triple 사이트 날짜 형식 맞춤)
# -------------------------------
def preprocess_date(date_str):
    """
    Triple 사이트의 영문 날짜 문자열을 YYYY-MM-DD 형식으로 변환합니다.
    예: 'May 01, 2025 - May 31, 2025' 또는 'May 01, 2025'
    """
    # 날짜 형식: 'Month Day, Year'
    DATE_FORMAT = '%b %d, %Y' 
    
    try:
        # 단일 날짜 또는 범위 날짜 분리
        if '-' in date_str:
            parts = date_str.split('-')
            start_raw = parts[0].strip()
            end_raw = parts[-1].strip() 
        else:
            start_raw = date_str.strip()
            end_raw = date_str.strip()
            
        # 범위의 끝 날짜에 연도가 생략된 경우 (예: 'Jan 01 - Jan 31, 2025')
        if len(end_raw.split(',')) == 1 and len(start_raw.split(',')) > 1:
            end_raw += ', ' + start_raw.split(',')[-1].strip()

        start_dt = datetime.strptime(start_raw, DATE_FORMAT)
        end_dt = datetime.strptime(end_raw, DATE_FORMAT)
        
        return start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"⚠️ 날짜 변환 실패 ('{date_str}'): {e}")
        return None, None

# -------------------------------
# 4️⃣ 뮤지컬 정보 크롤링
# -------------------------------
def scrape_triple_concerts():
    url = "https://triple.global/en/ticket/genre/MUSICAL/products" # 🌟 URL을 MUSICAL로 변경
    driver = init_driver()
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    
    results = []
    collected_links = set()
    SCROLL_PAUSE_TIME = 2
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    # 🌟 스크롤 로직 단순화 및 명확화
    while True:
        # 현재 스크롤 위치에서 새로운 요소를 수집
        concerts = driver.find_elements(By.CSS_SELECTOR, "ul > li") 
        new_items_found = False

        for concert in concerts:
            try:
                # 🚨 Link는 항상 A 태그에 있으므로 link를 기준으로 수집 여부를 판단합니다.
                link_elem = concert.find_element(By.TAG_NAME, "a")
                link = link_elem.get_attribute("href")
                
                if link in collected_links:
                    continue 
                
                # 🌟 CSS Selector는 원본 코드와 동일하게 유지
                title = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-0.iJhclZ").text.strip()
                date_raw = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-1.gDgSG").text.strip()
                place = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-2.esLjqQ").text.strip()
                image = concert.find_element(By.CSS_SELECTOR, "a > div.sc-45389dec-1.dGxhoh.sc-e4eb73f-3.dNNiLo > img").get_attribute("src")

                start_date, end_date = preprocess_date(date_raw)

                results.append({
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date,
                    "place": place,
                    "image": image,
                    "link": link,
                    "date_raw": date_raw # 디버깅용으로 원본 날짜도 저장
                })
                collected_links.add(link)
                new_items_found = True
                print(f"✅ {len(results)}. {title} | {start_date} - {end_date}")

            except Exception: # 요소 탐색에 실패한 경우 해당 아이템은 건너뜀
                 continue 

        # 2️⃣ 스크롤 다운
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME) 
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # 3️⃣ 스크롤 위치가 변하지 않았거나 새 항목이 없으면 종료
        if new_height == last_height and not new_items_found:
             break

        last_height = new_height

    driver.quit()
    print(f"\n🎉 총 {len(results)}개 뮤지컬 정보 수집 완료")
    return results

# -------------------------------
# 5️⃣ MySQL 적재
# -------------------------------
def save_to_mysql(data):
    conn = connect_mysql()
    if not conn:
        return
        
    cursor = conn.cursor()
    main_count = 0
    fail_count = 0

    for d in data:
        # 필수 필드 (title, start_date, end_date, place) 중 하나라도 None인 경우 체크
        is_data_clean = all([d['title'], d['start_date'], d['end_date'], d['place']])

        if is_data_clean:
            # 데이터가 깨끗한 경우 메인 테이블에 적재
            cursor.execute("""
                INSERT INTO musical_perform (title, start_date, end_date, place, image, link)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (d['title'], d['start_date'], d['end_date'], d['place'], d['image'], d['link']))
            main_count += 1
        
        if not is_data_clean:
             # 데이터가 깨끗하지 않은 경우 실패 테이블에 기록
             error_msg = "필수 필드 누락: " + ", ".join(k for k, v in d.items() if v is None and k != 'image' and k != 'link')
             cursor.execute("""
                 INSERT INTO musical_fail (title, date_raw, place, error_msg)
                 VALUES (%s, %s, %s, %s)
             """, (d.get('title'), d.get('date_raw'), d.get('place'), error_msg))
             fail_count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"💾 {main_count}개 메인 테이블 적재 완료 (musical_perform)")
    print(f"⚠️ {fail_count}개 실패 테이블 적재 완료 (musical_fail)")

# -------------------------------
# 6️⃣ 실행
# -------------------------------
if __name__ == "__main__":
    create_tables()
    data = scrape_triple_concerts()
    save_to_mysql(data)