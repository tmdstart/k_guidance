from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# ----------------------------------------------------
# 1️⃣ Selenium 초기 설정
# ----------------------------------------------------
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 창 안 띄우기
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ----------------------------------------------------
# 2️⃣ 콘서트 정보 크롤링 함수 (스크롤 + 대기)
# ----------------------------------------------------
def scrape_triple_concerts():
    url = "https://triple.global/en/ticket/genre/MUSICAL/products"
    driver = init_driver()
    driver.get(url)

    wait = WebDriverWait(driver, 20)

    results = []
    collected_links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # 1️⃣ 현재 페이지 요소 수집
        concerts = driver.find_elements(By.CSS_SELECTOR, "ul > li")
        new_count = 0
        for concert in concerts:
            try:
                link = concert.find_element(By.TAG_NAME, "a").get_attribute("href")
                if link in collected_links:
                    continue  # 이미 수집한 데이터는 건너뜀

                title = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-0.iJhclZ").text.strip()
                date = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-1.gDgSG").text.strip()
                place = concert.find_element(By.CSS_SELECTOR, "div:nth-child(2) > div.sc-e4eb73f-2.esLjqQ").text.strip()
                image = concert.find_element(By.CSS_SELECTOR, "a > div.sc-45389dec-1.dGxhoh.sc-e4eb73f-3.dNNiLo > img").get_attribute("src")

                results.append({
                    "title": title,
                    "date": date,
                    "place": place,
                    "image": image,
                    "link": link
                })
                collected_links.add(link)
                new_count += 1
                print(f"✅ {len(results)}. {title}")
            except Exception as e:
                print(f"⚠️ 데이터 수집 실패: {e}")
                continue

        # 2️⃣ 스크롤 내려서 다음 요소 기다리기
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # JS 렌더링 잠시 대기

        # 최대 60초 동안 새 요소가 나타날 때까지 기다림
        scroll_wait_time = 0
        while new_count == 0 and scroll_wait_time < 60:
            time.sleep(2)
            scroll_wait_time += 2
            concerts = driver.find_elements(By.CSS_SELECTOR, "ul > li")
            for concert in concerts:
                link = concert.find_element(By.TAG_NAME, "a").get_attribute("href")
                if link not in collected_links:
                    new_count += 1
                    break

        # 3️⃣ 더 이상 새 요소가 없으면 종료
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_count == 0 or new_height == last_height:
            break
        last_height = new_height

    driver.quit()
    print(f"\n🎉 총 {len(results)}개 콘서트 정보 수집 완료")
    return results

# ----------------------------------------------------
# 3️⃣ 실행
# ----------------------------------------------------
if __name__ == "__main__":
    data = scrape_triple_concerts()
    for d in data:
        print(d)
