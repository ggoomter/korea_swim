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
    monthly_lesson_price: Optional[int] = None  # 한달 수강권 (1개월 강습)
    free_swim_times: Optional[Dict] = None
    free_swim_price: Optional[int] = None
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
