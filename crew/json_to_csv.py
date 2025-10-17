import json
import csv

# JSON 파일 읽기
with open('korean_foods_details_20251015_120256.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# CSV 파일로 저장
with open('korean_foods_des.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    
    # 헤더 작성
    headers = ['url', 'food_name', 'title', 'description', 'ingredients', 'image_path']
    writer.writerow(headers)
    
    # 데이터 작성
    for item in data['foods']:
        # ingredients 리스트를 콤마로 구분된 문자열로 변환
        ingredients_str = ', '.join(item.get('ingredients', []))
        
        row = [
            item.get('url', ''),
            item.get('food_name', ''),
            item.get('title', ''),
            item.get('description', ''),
            ingredients_str,
            item.get('image_path', '')
        ]
        
        writer.writerow(row)

print(f"✅ CSV 파일이 생성되었습니다: korean_foods_des.csv")
print(f"   총 {len(data['foods'])}개의 음식 데이터가 변환되었습니다.")