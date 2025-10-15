import pymysql
import pandas as pd

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
    except Exception as e:
        print("DB 연결 실패:", e)
        return None

def export_to_csv():
    conn = connect_mysql()
    if not conn:
        return
    
    query = "SELECT * FROM concert_perform"
    df = pd.read_sql(query, conn)
    df.to_csv("concert_perform.csv", index=False, encoding="utf-8-sig")
    
    conn.close()
    print("✅ CSV 파일 생성 완료: concert_perform.csv")

if __name__ == "__main__":
    export_to_csv()
