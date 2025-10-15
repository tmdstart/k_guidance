import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ----------------------------------------------------
# 1. 설정 및 상수
# ----------------------------------------------------
BASE_URL = "https://korean.visitkorea.or.kr/kfes/list/wntyFstvlList.do"

REGION_DROPDOWN_ID = "searchArea"
DATE_DROPDOWN_ID = "searchDate"
SEOUL_VALUE = "1"
DATE_FILTER_VALUE = ['A','B']  # A: 개최 중, B: 개최 예정

# ----------------------------------------------------
# 2. 날짜 전처리 함수
# ----------------------------------------------------
def preprocess_date(date_string):
    dates = re.findall(r'(\d{4}\.\d{2}\.\d{2})', date_string)
    start_date = dates[0] if len(dates) >= 1 else None
    end_date = dates[-1] if len(dates) >= 1 else None
    return start_date, end_date

# ----------------------------------------------------
# 3. 상세 페이지 크롤링 (별도 드라이버)
# ----------------------------------------------------
def crawl_festival_detail(detail_url):
    service = ChromeService(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)
    detail_data = {'description': "N/A", 'address': "N/A", 'instagram_url': "N/A"}

    try:
        driver.get(detail_url)
        SELECTORS = {
            'description': "#mainTab > div > div > section.poster_detail > div > div.poster_info_content > div.m_img_fst",
            'address': "#mainTab > div > div > section.poster_detail > div > div.poster_detail_wrap > div > div.img_info_box > ul > li:nth-child(2) > p",
            'instagram_url': "#mainTab > div > div > section.poster_detail > div > div.poster_detail_wrap > div > div.img_info_box > ul > li:nth-child(6) > a"
        }

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS['description'])))

        try:
            desc = driver.find_element(By.CSS_SELECTOR, SELECTORS['description']).text.strip()
            detail_data['description'] = re.sub(r'\s+', ' ', desc)
        except:
            pass

        try:
            addr = driver.find_element(By.CSS_SELECTOR, SELECTORS['address']).text.strip()
            detail_data['address'] = addr
        except:
            pass

        try:
            insta = driver.find_element(By.CSS_SELECTOR, SELECTORS['instagram_url']).get_attribute('href')
            detail_data['instagram_url'] = insta
        except:
            pass

    except Exception as e:
        print(f"❌ 상세 페이지 크롤링 실패: {e}")
    finally:
        driver.quit()

    return detail_data

# ----------------------------------------------------
# 4. 메인 크롤링
# ----------------------------------------------------
def get_all_festival_data():
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    wait = WebDriverWait(driver, 15)
    all_results = []

    try:
        driver.get(BASE_URL)
        print("✅ 기본 페이지 접속 완료")

        # 지역 선택 (서울)
        wait.until(EC.presence_of_element_located((By.ID, REGION_DROPDOWN_ID)))
        Select(driver.find_element(By.ID, REGION_DROPDOWN_ID)).select_by_value(SEOUL_VALUE)
        time.sleep(1)

        # A(개최 중), B(개최 예정) 각각 반복
        for date_filter in DATE_FILTER_VALUE:
            print(f"\n🎯 '{date_filter}' 필터 적용 중...")

            # 날짜 필터 선택
            Select(driver.find_element(By.ID, DATE_DROPDOWN_ID)).select_by_value(date_filter)
            time.sleep(1)

            # 검색 버튼 클릭
            search_button = driver.find_element(By.CSS_SELECTOR, "button.btn_search")
            driver.execute_script("arguments[0].click();", search_button)

            # Ajax 로딩 대기
            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#fstvlList > li")))
            except:
                print(f"⚠️ '{date_filter}' 결과 없음 (리스트 비어 있음)")
                continue

            time.sleep(2)
            print(f"✅ '{date_filter}' 필터 결과 로딩 완료")

            page = 1
            while True:
                print(f"\n===== 📄 {date_filter} - {page}페이지 크롤링 시작 =====")
                items = driver.find_elements(By.CSS_SELECTOR, "#fstvlList > li")

                if not items:
                    print("더 이상 축제 없음. 종료.")
                    break

                for idx, item in enumerate(items, start=1):
                    try:
                        title = item.find_element(By.CSS_SELECTOR, "a > div.other_festival_content > strong").text.strip()
                        date_raw = item.find_element(By.CSS_SELECTOR, "a > div.other_festival_content > div.date").text
                        start_date, end_date = preprocess_date(date_raw)
                        img_url = item.find_element(By.CSS_SELECTOR, "a > div.other_festival_img > img").get_attribute('src')
                        detail_url = item.find_element(By.CSS_SELECTOR, "a").get_attribute('href')

                        print(f"▶ {idx}. {title} 상세페이지 이동 중...")
                        detail_data = crawl_festival_detail(detail_url)

                        result = {
                            'filter': date_filter,
                            'title': title,
                            'image_url': img_url,
                            'start_date': start_date,
                            'end_date': end_date,
                            'detail_url': detail_url,
                            **detail_data
                        }
                        all_results.append(result)
                        print(f"✅ {title} 완료")

                    except Exception as e:
                        print(f"❌ {idx}번째 축제 오류: {e}")

                # 다음 페이지 이동
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "div.paging_wrap a.next")
                    if "disabled" in next_btn.get_attribute("class"):
                        print("다음 페이지 없음. 종료.")
                        break
                    driver.execute_script("arguments[0].click();", next_btn)
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#fstvlList > li")))
                    time.sleep(1)
                    page += 1
                except:
                    print("다음 페이지 버튼 없음. 종료.")
                    break

    except Exception as e:
        print(f"❌ 메인 실행 오류: {e}")
    finally:
        driver.quit()

    print(f"\n🎉 총 {len(all_results)}개 축제 크롤링 완료")
    return all_results

# ----------------------------------------------------
# 5. 실행
# ----------------------------------------------------
if __name__ == "__main__":
    data = get_all_festival_data()
    print("\n=== 결과 미리보기 ===")
    for i, d in enumerate(data[:3], start=1):
        print(f"{i}. {d['title']} | {d['start_date']}~{d['end_date']}")
        print(f"주소: {d['address']}")
        print(f"설명: {d['description']}")
