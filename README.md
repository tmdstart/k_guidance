# k_guidance
## 📂 파일 목록 및 설명

### 1. 음식점 데이터 수집
- **food_crawl.ipynb**: 방문할 만한 서울시 음식점 데이터를 수집 및 분석하는 Jupyter Notebook.
- **seoul_resturant.ipynb**: 서울시 음식점 데이터를 전처리 Jupyter Notebook.

### 2. 인터파크 공연/티켓 데이터

#### 🎫 콘서트
- **interpark_concert_ticket.py**: 인터파크 콘서트 티켓 상세 정보 수집 스크립트.
- **interpark_concert_sql.py**: 수집된 콘서트 데이터를 SQL 데이터베이스에 저장하는 스크립트.
- **interpark_concert_sql_location.py**: 콘서트 공연장 위치 데이터 수집 및 처리(위도, 경도 변환) 스크립트.

#### 🎭 뮤지컬
- **interpark_musical_ticket.py**: 인터파크 뮤지컬 티켓 상세 정보 수집 스크립트.
- **interpark_musical_sql.py**: 수집된 뮤지컬 데이터를 SQL 데이터베이스에 저장하는 스크립트.
- **interpark_musical_sql_location.py**: 뮤지컬 공연장 위치 데이터 수집 및 처리(위도, 경도 변환) 스크립트.

### 3. 축제 데이터
- **대한민국구석구석_festival.py**: 대한민국 구석구석 웹사이트에서 축제 정보를 수집하는 스크립트.

### 4. 한국관광명소 데이터
- **seoul_attraction_location.ipynb**: 비짓서울에서 수집한 서울의 관광명소 수집데이터를 처리(위도, 경도 변환) 스크립트.

### 4. 데이터 변환
- **transform_csv.py**: mysql(데이터베이스)에서 데이터를 추출하여 CSV 파일로 변환하는 스크립트. Mysql -> csv

### 5. 기타
- **.gitignore**: Git 추적에서 제외할 파일 목록 (.env, 캐시, 로그 등).
