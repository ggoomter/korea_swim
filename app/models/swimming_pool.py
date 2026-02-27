from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class SwimmingPool(Base):
    __tablename__ = "swimming_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    lat = Column(Float)  # 위도
    lng = Column(Float)  # 경도
    phone = Column(String, nullable=True)

    # 운영 정보 (요일별: {"월": "06:00-22:00", "화": "06:00-22:00", ...})
    operating_hours = Column(JSON, nullable=True)

    # 시설 정보
    lanes = Column(Integer, nullable=True)
    pool_size = Column(String, nullable=True)  # "25m x 6레인"
    water_temp = Column(String, nullable=True)
    facilities = Column(JSON, nullable=True)  # ["사우나", "주차장", "락커"]

    # 가격 정보 (대상별/요일별 구조화)
    # {"자유수영": {"성인": {"평일": 3400, "주말": 4400}}, "강습_월": {"성인": 120000}}
    pricing = Column(JSON, nullable=True)

    # 자유수영 시간표 (요일별)
    # {"월": ["12:00-12:50"], "토": ["06:00-07:50", "09:00-10:50"], "휴관": "매월 첫째 일요일"}
    free_swim_schedule = Column(JSON, nullable=True)

    # 비고 (휴관일, 예약방법 등)
    notes = Column(Text, nullable=True)

    # 주차 가능 여부
    parking = Column(Boolean, nullable=True)

    # 메타 정보
    source = Column(String)
    url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # LLM 데이터 추출 상태
    last_enriched = Column(DateTime, nullable=True)
    enrichment_status = Column(String, default="pending")  # pending/success/failed

    # 평점 및 리뷰
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
