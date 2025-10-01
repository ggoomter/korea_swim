from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean
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

    # 운영 정보
    operating_hours = Column(JSON, nullable=True)  # {"mon": "06:00-22:00", ...}

    # 시설 정보
    lanes = Column(Integer, nullable=True)  # 레인 수
    pool_size = Column(String, nullable=True)  # 예: "25m x 15m"
    water_temp = Column(String, nullable=True)  # 수온
    facilities = Column(JSON, nullable=True)  # ["사우나", "주차장", "락커"]

    # 가격 정보
    membership_prices = Column(JSON, nullable=True)  # {"1month": 100000, "3month": 270000, ...}
    daily_price = Column(Integer, nullable=True)  # 1회 이용권

    # 자율수영 정보
    free_swim_times = Column(JSON, nullable=True)  # {"mon": ["06:00-08:00", "20:00-22:00"], ...}
    free_swim_price = Column(Integer, nullable=True)

    # 레슨 정보
    lessons = Column(JSON, nullable=True)  # [{"type": "초급", "price": 200000, "schedule": "월수금"}]

    # 메타 정보
    source = Column(String)  # "공공데이터", "네이버", "카카오"
    url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)  # 수영장 이미지
    description = Column(String, nullable=True)  # 설명
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # 평점 및 리뷰
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
