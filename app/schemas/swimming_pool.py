from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class SwimmingPoolBase(BaseModel):
    name: str
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = None
    operating_hours: Optional[Dict] = None
    lanes: Optional[int] = None
    pool_size: Optional[str] = None
    water_temp: Optional[str] = None
    facilities: Optional[List[str]] = None
    membership_prices: Optional[Dict] = None
    daily_price: Optional[str] = None  # 일일권 가격 (예: "10000")
    monthly_lesson_price: Optional[str] = None  # 한달 수강권 (예: "150000" 또는 "가격 다양, 표 참조")
    free_swim_times: Optional[Dict] = None
    free_swim_price: Optional[str] = None  # 자유수영 (예: "8000" 또는 "시간대별 상이")
    lessons: Optional[List[Dict]] = None
    source: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None

class SwimmingPoolCreate(SwimmingPoolBase):
    pass

class SwimmingPoolResponse(SwimmingPoolBase):
    id: int
    last_updated: datetime
    is_active: bool
    review_count: int

    class Config:
        from_attributes = True

class SwimmingPoolSearch(BaseModel):
    lat: float
    lng: float
    radius_km: float = 5.0  # 기본 5km 반경
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    has_free_swim: Optional[bool] = None
