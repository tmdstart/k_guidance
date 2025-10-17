import asyncio
from playwright.async_api import async_playwright
import json
import os
import httpx
from pathlib import Path

async def download_image(url, save_path):
    """이미지 URL에서 실제 파일 다운로드"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True
    except Exception as e:
        print(f"    ⚠️ 다운로드 실패: {e}")
    return False

async def scrape_attraction_detail(page, url, index, category):
    """개별 명소 페이지 크롤링 및 이미지 다운로드"""
    try:
        print(f"\n🔍 크롤링 중: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # 명소 ID 추출 (폴더명으로 사용)
        attraction_id = url.split('/')[-1]
        
        attraction_data = {
            "url": url,
            "id": attraction_id,
            "category": category,
            "title": "",
            "images": [],
            "description": "",
            "details": []
        }
        
        # 이미지 저장 폴더 생성 (카테고리별로 분리)
        image_folder = Path(f"images/{category}/{attraction_id}")
        image_folder.mkdir(parents=True, exist_ok=True)
        
        # 제목 추출
        try:
            title = await page.text_content('h1, h2.tit, .title')
            attraction_data["title"] = title.strip() if title else attraction_id
            print(f"  📌 제목: {attraction_data['title']}")
        except:
            attraction_data["title"] = attraction_id
        
        # 특정 슬라이드 이미지만 추출 (캐러셀 순회)
        try:
            # 페이지가 완전히 로드될 때까지 대기
            print("  ⏳ 이미지 로딩 대기 중...")
            await page.wait_for_timeout(3000)
            
            # 캐러셀 컨테이너 확인
            container_selector = '#container > div.wide-inner > div.wide-slide-element'
            
            container = await page.query_selector(container_selector)
            
            if not container:
                print(f"  ❌ 캐러셀 컨테이너를 찾을 수 없습니다")
                images = []
            else:
                print("  ✅ 캐러셀 발견!")
                
                # 전체 슬라이드 개수 확인
                total_slides = await page.eval_on_selector(
                    container_selector,
                    '''el => {
                        const items = el.querySelectorAll('.owl-item');
                        return items.length;
                    }'''
                )
                print(f"  📊 전체 슬라이드 개수: {total_slides}개")
                
                # 화살표 버튼 찾기
                next_button_selectors = [
                    '.owl-next',
                    '.owl-carousel .owl-next',
                    'button.owl-next',
                    '[class*="next"]',
                    '.slider-next',
                    '.arrow-next'
                ]
                
                next_button = None
                for selector in next_button_selectors:
                    try:
                        btn = await page.query_selector(selector)
                        if btn and await btn.is_visible():
                            next_button = btn
                            print(f"  🔘 다음 버튼 발견: {selector}")
                            break
                    except:
                        continue
                
                images = []
                collected_urls = set()
                
                # 최대 10번 순회 (일반적으로 3-5개이므로 충분)
                max_clicks = 10
                
                for i in range(max_clicks):
                    # 현재 활성화된 이미지 추출
                    try:
                        current_image = await page.eval_on_selector(
                            '.owl-item.active img, .owl-item.active div[style*="background-image"]',
                            '''el => {
                                if (el.tagName === 'IMG') {
                                    return el.src;
                                } else {
                                    // background-image인 경우
                                    const style = el.style.backgroundImage;
                                    const match = style.match(/url\\(["']?([^"']*)["']?\\)/);
                                    return match ? match[1] : null;
                                }
                            }'''
                        )
                        
                        # 상대 경로를 절대 경로로 변환
                        if current_image:
                            if current_image.startswith('/'):
                                current_image = f"https://english.visitseoul.net{current_image}"
                            elif not current_image.startswith('http'):
                                current_image = f"https://english.visitseoul.net/{current_image}"
                        
                        if current_image and current_image not in collected_urls:
                            collected_urls.add(current_image)
                            images.append(current_image)
                            print(f"  📸 이미지 {len(images)} 수집: {current_image[:60]}...")
                        
                    except Exception as e:
                        print(f"  ⚠️ 현재 이미지 추출 실패: {e}")
                    
                    # 다음 버튼 클릭
                    if next_button and i < max_clicks - 1:
                        try:
                            # 버튼이 여전히 활성화되어 있는지 확인
                            is_disabled = await next_button.get_attribute('disabled')
                            has_disabled_class = await next_button.evaluate(
                                'el => el.classList.contains("disabled")'
                            )
                            
                            if is_disabled or has_disabled_class:
                                print(f"  🛑 마지막 슬라이드 도달 (총 {len(images)}개)")
                                break
                            
                            await next_button.click()
                            await page.wait_for_timeout(1000)  # 슬라이드 애니메이션 대기
                            
                        except Exception as e:
                            print(f"  ⚠️ 버튼 클릭 실패 또는 순회 완료")
                            break
                    else:
                        break
                
                # 중복 제거 및 최종 확인
                images = list(dict.fromkeys(images))  # 순서 유지하며 중복 제거
                print(f"  ✅ 총 {len(images)}개의 고유한 이미지 수집 완료")
                
                if not images:
                    print("  ⚠️ 이미지를 찾지 못했습니다. 대체 방법 시도...")
                    # 모든 owl-item에서 한번에 추출
                    images = await page.eval_on_selector_all(
                        '.owl-item img',
                        '''elements => elements
                            .map(el => el.src)
                            .filter(src => src && src.startsWith('http'))
                        '''
                    )
                    images = list(set(images))
                    print(f"  📸 대체 방법으로 {len(images)}개 발견")
            
            # 이미지 다운로드
            for i, img_url in enumerate(images, 1):
                # 파일 확장자 추출
                ext = img_url.split('.')[-1].split('?')[0][:4]  # jpg, png 등
                if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    ext = 'jpg'
                
                filename = f"image_{i:02d}.{ext}"
                save_path = image_folder / filename
                
                print(f"    ⬇️  이미지 {i}/{len(images)} 다운로드 중...")
                success = await download_image(img_url, save_path)
                
                if success:
                    print(f"    ✅ 저장 완료: {filename}")
                    attraction_data["images"].append({
                        "url": img_url,
                        "local_path": str(save_path),
                        "filename": filename
                    })
                else:
                    print(f"    ❌ 저장 실패")
        
        except Exception as e:
            print(f"  ⚠️ 이미지 추출 실패: {e}")
        
        # 기본 설명 추출 (text-area 안의 큰 두 문장)
        try:
            desc_selector = '#container > div.wide-inner > div.text-area'
            desc_element = await page.query_selector(desc_selector)
            
            if desc_element:
                desc_text = await desc_element.text_content()
                if desc_text:
                    attraction_data["description"] = desc_text.strip()
                    print(f"  📝 설명 수집 완료 ({len(desc_text.strip())}자)")
                else:
                    print("  ⚠️ text-area가 비어있습니다")
            else:
                print("  ⚠️ text-area를 찾을 수 없습니다")
                
        except Exception as e:
            print(f"  ⚠️ 설명 추출 실패: {e}")
        
        # 상세 정보 추출 (detial-cont-element 안의 모든 dl 태그)
        try:
            # 전체 상세 정보 컨테이너
            detail_container_selector = '#container > div.detial-cont-element.active > div'
            
            detail_container = await page.query_selector(detail_container_selector)
            
            if detail_container:
                print("  📋 상세 정보 수집 중...")
                
                # 컨테이너 안의 모든 dl 태그 찾기
                all_pairs = await detail_container.evaluate('''container => {
                    const dlElements = container.querySelectorAll('dl');
                    const allResults = [];
                    
                    dlElements.forEach(dl => {
                        const dts = dl.querySelectorAll('dt');
                        const dds = dl.querySelectorAll('dd');
                        
                        for (let i = 0; i < Math.min(dts.length, dds.length); i++) {
                            const label = dts[i].textContent.trim();
                            const value = dds[i].textContent.trim();
                            if (label && value) {
                                allResults.push({ label: label, value: value });
                            }
                        }
                    });
                    
                    return allResults;
                }''')
                
                attraction_data["details"] = all_pairs
                
                for pair in all_pairs:
                    print(f"    • {pair['label']}: {pair['value'][:50]}...")
                
                print(f"  ✅ 상세 정보 {len(all_pairs)}개 수집 완료")
            else:
                print("  ⚠️ 상세 정보 컨테이너를 찾을 수 없습니다")
            
        except Exception as e:
            print(f"  ⚠️ 상세 정보 추출 실패: {e}")
        
        print(f"  ✅ 크롤링 완료: {attraction_data['title']}")
        return attraction_data
        
    except Exception as e:
        print(f"  ❌ 에러 발생: {e}")
        return None

async def scrape_all_attractions(test_mode=False, test_url=None, links_file="seoul_attractions_links.json"):
    """저장된 링크를 읽어서 모든 명소 크롤링
    
    Args:
        test_mode: 테스트 모드 (단일 URL만 크롤링)
        test_url: 테스트할 URL
        links_file: 링크 파일 경로 (예: seoul_attractions_links.json, seoul_history_links.json)
    """
    
    # 파일명에서 카테고리 자동 추출
    # seoul_attractions_links.json -> attractions
    # seoul_history_links.json -> history
    try:
        category = links_file.replace('seoul_', '').replace('_links.json', '')
        print(f"📂 자동 감지된 카테고리: {category}")
    except:
        category = "data"
        print(f"⚠️ 카테고리를 감지할 수 없어 기본값 사용: {category}")
    
    # 테스트 모드: 단일 URL만 크롤링
    if test_mode and test_url:
        links = [test_url]
        print(f"🧪 테스트 모드: {test_url}\n")
    else:
        # 링크 파일 읽기
        try:
            with open(links_file, 'r', encoding='utf-8') as f:
                links = json.load(f)
            print(f"📋 링크 파일: {links_file}")
            print(f"📊 총 {len(links)}개의 링크를 불러왔습니다.\n")
        except FileNotFoundError:
            print(f"❌ {links_file} 파일을 찾을 수 없습니다.")
            return
    
    all_attractions = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # 백그라운드 실행
        page = await browser.new_page()
        page.set_default_timeout(60000)
        
        for i, link in enumerate(links, 1):
            print(f"\n{'='*70}")
            print(f"📍 진행: {i}/{len(links)}")
            print(f"{'='*70}")
            
            data = await scrape_attraction_detail(page, link, i, category)
            if data:
                all_attractions.append(data)
            
            # 서버 부하 방지
            await page.wait_for_timeout(2000)
        
        await browser.close()
    
    # 카테고리별 폴더 생성
    output_folder = Path(category)
    output_folder.mkdir(exist_ok=True)
    
    # 결과 저장
    json_path = output_folder / f'seoul_{category}_details.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_attractions, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✅ 총 {len(all_attractions)}개 {category} 크롤링 완료!")
    print(f"📁 JSON: {json_path}")
    print(f"📁 이미지: images/{category}/ 폴더")
    print(f"{'='*70}")

if __name__ == "__main__":
    # ===== 설정 =====
    # 링크 파일명만 입력하세요! (카테고리는 자동으로 추출됩니다)
    LINKS_FILE = "seoul_places_links.json"  # 예: seoul_history_links.json, seoul_restaurant_links.json
    
    # 테스트 모드: True면 단일 URL만, False면 전체 크롤링
    TEST_MODE = False
    TEST_URL = "https://english.visitseoul.net/attractions/Namsan-Seoul-Tower/ENP000036"
    
    # 실행
    asyncio.run(scrape_all_attractions(
        test_mode=TEST_MODE,
        test_url=TEST_URL if TEST_MODE else None,
        links_file=LINKS_FILE
    ))
    
    
    