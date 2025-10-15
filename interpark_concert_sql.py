from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pymysql
from datetime import datetime

# -------------------------------
# 1️⃣ MySQL 연결 및 테이블 생성
# -------------------------------
def connect_mysql():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="1234",
        database="performance",
        charset="utf8mb4"
    )
    return conn

def create_tables():
    conn = connect_mysql()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concert_perform (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            start_date DATE,
            end_date DATE,
            place VARCHAR(255),
            image TEXT,
            link TEXT
        ) CHARACTER SET utf8mb4;
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concert_fail (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            start_date DATE,
            end_date DATE,
            place VARCHAR(255),
            image TEXT,
            link TEXT
        ) CHARACTER SET utf8mb4;
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 테이블 생성 완료")

# -------------------------------
# 2️⃣ Selenium 초기 설정
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
# 3️⃣ 날짜 전처리 함수
# -------------------------------
def preprocess_date(date_str):
    try:
        if '-' in date_str:
            start_raw, end_raw = date_str.split('-')
            start_dt = datetime.strptime(start_raw.strip(), '%b %d, %Y')
            end_dt = datetime.strptime(end_raw.strip(), '%b %d, %Y')
        else:
            start_dt = end_dt = datetime.strptime(date_str.strip(), '%b %d, %Y')
        return start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d')
    except:
        return None, None

# -------------------------------
# 4️⃣ 콘서트 정보 크롤링
# -------------------------------
def scrape_triple_concerts():
    url = "https://triple.global/en/ticket/genre/CONCERT/products"
    driver = init_driver()
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    results = []
    SCROLL_PAUSE_TIME = 2
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "body > div.sc-55fb52ed-0.gUeTO > ul > li")))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    concert_list = driver.find_elements(By.CSS_SELECTOR, "body > div.sc-55fb52ed-0.gUeTO > ul > li")
    print(f"총 {len(concert_list)}개 콘서트 요소 발견")

    for idx, concert in enumerate(concert_list, start=1):
        try:
            title_elem = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-0.iJhclZ")
            date_elem = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-1.gDgSG")
            place_elem = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-2.esLjqQ")
            image_elem = concert.find_element(By.CSS_SELECTOR, "a > div.sc-45389dec-1.dGxhoh.sc-e4eb73f-3.dNNiLo > img")
            link_elem = concert.find_element(By.CSS_SELECTOR, "a")

            title = title_elem.text.strip() if title_elem else None
            date_raw = date_elem.text.strip() if date_elem else None
            start_date, end_date = preprocess_date(date_raw)
            place = place_elem.text.strip() if place_elem else None
            image = image_elem.get_attribute("src") if image_elem else None
            link = link_elem.get_attribute("href") if link_elem else None

            results.append({
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "place": place,
                "image": image,
                "link": link
            })
            print(f"✅ {idx}. {title} | {start_date} - {end_date} | {place}")

        except Exception as e:
            print(f"⚠️ {idx}번째 콘서트 수집 실패: {e}")
            continue

    driver.quit()
    return results

# -------------------------------
# 5️⃣ MySQL 적재
# -------------------------------
def save_to_mysql(data):
    conn = connect_mysql()
    cursor = conn.cursor()
    main_count = 0
    fail_count = 0

    for d in data:
        cursor.execute("""
            INSERT INTO concert_perform (title, start_date, end_date, place, image, link)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (d['title'], d['start_date'], d['end_date'], d['place'], d['image'], d['link']))
        main_count += 1

        # null 값이 하나라도 있는 경우 fail 테이블에도 적재
        if not all([d['title'], d['start_date'], d['end_date'], d['place']]):
            cursor.execute("""
                INSERT INTO concert_fail (title, start_date, end_date, place, image, link)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (d['title'], d['start_date'], d['end_date'], d['place'], d['image'], d['link']))
            fail_count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"💾 {main_count}개 메인 테이블 적재 완료")
    print(f"⚠️ {fail_count}개 실패 테이블 적재 완료")

# -------------------------------
# 6️⃣ 실행
# -------------------------------
if __name__ == "__main__":
    create_tables()
    data = scrape_triple_concerts()
    save_to_mysql(data)
