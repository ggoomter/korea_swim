import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from crawler.naver_map import NaverMapCrawler
from crawler.kakao_map import KakaoMapCrawler
from crawler.public_data import PublicDataCrawler
from database.connection import SessionLocal
from app.crud.swimming_pool import create_swimming_pool
from app.schemas.swimming_pool import SwimmingPoolCreate

load_dotenv()

def crawl_and_save():
    """
    모든 크롤러를 실행하고 DB에 저장
    """
    db = SessionLocal()

    try:
        # 1. 네이버 크롤링
        naver_client_id = os.getenv("NAVER_CLIENT_ID")
        naver_client_secret = os.getenv("NAVER_CLIENT_SECRET")

        if naver_client_id and naver_client_secret:
            print("\n=== 네이버 지도 크롤링 시작 ===")
            naver_crawler = NaverMapCrawler(naver_client_id, naver_client_secret)
            naver_pools = naver_crawler.crawl_all_pools()
            save_to_db(db, naver_pools)
        else:
            print("⚠️ 네이버 API 키가 설정되지 않았습니다.")

        # 2. 카카오 크롤링
        kakao_api_key = os.getenv("KAKAO_API_KEY")

        if kakao_api_key:
            print("\n=== 카카오맵 크롤링 시작 ===")
            kakao_crawler = KakaoMapCrawler(kakao_api_key)
            kakao_pools = kakao_crawler.crawl_all_pools()
            save_to_db(db, kakao_pools)
        else:
            print("⚠️ 카카오 API 키가 설정되지 않았습니다.")

        # 3. 공공데이터 크롤링
        public_api_key = os.getenv("PUBLIC_DATA_API_KEY")

        if public_api_key:
            print("\n=== 공공데이터 크롤링 시작 ===")
            public_crawler = PublicDataCrawler(public_api_key)
            public_pools = public_crawler.crawl_all_pools()
            save_to_db(db, public_pools)
        else:
            print("⚠️ 공공데이터 API 키가 설정되지 않았습니다.")

        print("\n✅ 크롤링 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

def save_to_db(db: Session, pools_data: list):
    """
    크롤링한 데이터를 DB에 저장
    """
    saved_count = 0
    error_count = 0

    for pool_data in pools_data:
        try:
            pool_schema = SwimmingPoolCreate(**pool_data)
            create_swimming_pool(db, pool_schema)
            saved_count += 1

            if saved_count % 100 == 0:
                print(f"  저장 중... {saved_count}개")

        except Exception as e:
            error_count += 1
            print(f"  저장 오류: {pool_data.get('name', 'Unknown')} - {e}")

    print(f"  ✅ 저장 완료: {saved_count}개")
    if error_count > 0:
        print(f"  ⚠️ 오류: {error_count}개")

if __name__ == "__main__":
    crawl_and_save()
