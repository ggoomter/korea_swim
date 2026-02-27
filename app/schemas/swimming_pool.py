from pydantic import BaseModel
from typing import Optional, Dict, List, Any
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
    pricing: Optional[Dict[str, Any]] = None
    free_swim_schedule: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    parking: Optional[bool] = None
    source: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None

class SwimmingPoolCreate(SwimmingPoolBase):
    pass

class SwimmingPoolResponse(SwimmingPoolBase):
    id: int
    last_updated: Optional[datetime] = None
    is_active: bool = True
    review_count: int = 0
    enrichment_status: Optional[str] = None
    last_enriched: Optional[datetime] = None

    class Config:
        from_attributes = True

class SwimmingPoolSearch(BaseModel):
    lat: float
    lng: float
    radius_km: float = 5.0
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    has_free_swim: Optional[bool] = None
    day: Optional[str] = None  # 요일 필터: "월"~"일"
    time: Optional[str] = None  # 시간 필터: "HH:MM"
