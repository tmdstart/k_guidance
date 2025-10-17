import asyncio
from playwright.async_api import async_playwright
import json

async def extract_attraction_links():
    base_url = "https://english.visitseoul.net/attractions"
    params = "?curPage={}&srchType=&srchOptnCode=&srchCtgry=120&sortOrder=&srchWord=&radioOptionLike=TURSM_AREA_8"
    
    all_links = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 타임아웃 설정 증가
        page.set_default_timeout(60000)  # 60초
        
        # 1페이지부터 6페이지까지 순회
        for page_num in range(1, 7):
            url = base_url + params.format(page_num)
            print(f"\n{'='*60}")
            print(f"페이지 {page_num} 크롤링 중: {url}")
            print(f"{'='*60}")
            
            try:
                # networkidle 대신 domcontentloaded 사용 (더 빠름)
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 페이지 로딩 대기
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"⚠️ 페이지 {page_num} 로딩 중 에러: {e}")
                print("재시도 중...")
                await page.wait_for_timeout(2000)
                await page.goto(url, wait_until="load", timeout=60000)
                await page.wait_for_timeout(3000)
            
            # 명소 링크 추출 (여러 선택자 시도)
            links = await page.eval_on_selector_all(
                'a[href*="/attractions/"]',
                '''elements => elements
                    .map(el => el.href)
                    .filter(href => href.includes('/attractions/') && !href.includes('?curPage'))
                '''
            )
            
            # 중복 제거
            unique_links = list(set(links))
            
            print(f"페이지 {page_num}에서 {len(unique_links)}개의 명소 링크 발견")
            
            for i, link in enumerate(unique_links, 1):
                print(f"  {i}. {link}")
            
            all_links.extend(unique_links)
        
        await browser.close()
    
    # 전체 중복 제거
    all_links = list(set(all_links))
    
    print(f"\n{'='*60}")
    print(f"총 {len(all_links)}개의 고유한 명소 링크 수집 완료")
    print(f"{'='*60}")
    
    # JSON 파일로 저장
    with open('seoul_attractions_links.json', 'w', encoding='utf-8') as f:
        json.dump(all_links, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 링크가 'seoul_attractions_links.json' 파일에 저장되었습니다.")
    
    return all_links

if __name__ == "__main__":
    links = asyncio.run(extract_attraction_links())