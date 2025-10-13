from sqlalchemy.orm import Session
from app.models.swimming_pool import SwimmingPool
from app.schemas.swimming_pool import SwimmingPoolCreate
from typing import List, Optional
import math

def get_swimming_pool(db: Session, pool_id: int):
    return db.query(SwimmingPool).filter(SwimmingPool.id == pool_id).first()

def get_swimming_pools(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    source: Optional[str] = None,
    has_free_swim: Optional[bool] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None
):
    """Fetch swimming pools with optional filtering."""
    query = db.query(SwimmingPool)

    if source:
        query = query.filter(SwimmingPool.source == source)

    if has_free_swim is not None:
        if has_free_swim:
            query = query.filter(SwimmingPool.free_swim_times.isnot(None))
        else:
            query = query.filter(SwimmingPool.free_swim_times.is_(None))

    if min_price is not None:
        query = query.filter(SwimmingPool.daily_price >= min_price)

    if max_price is not None:
        query = query.filter(SwimmingPool.daily_price <= max_price)

    return query.offset(skip).limit(limit).all()

def create_swimming_pool(db: Session, pool: SwimmingPoolCreate):
    db_pool = SwimmingPool(**pool.dict())
    db.add(db_pool)
    db.commit()
    db.refresh(db_pool)
    return db_pool

def get_pool_by_name_address(db: Session, name: str, address: str):
    """이름과 주소로 수영장 찾기"""
    return db.query(SwimmingPool).filter(
        SwimmingPool.name == name,
        SwimmingPool.address == address
    ).first()

def upsert_swimming_pool(db: Session, pool: SwimmingPoolCreate):
    """수영장 생성 또는 업데이트 (이름+주소 기준)"""
    existing = get_pool_by_name_address(db, pool.name, pool.address)

    if existing:
        # 기존 수영장 업데이트
        for key, value in pool.dict().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing, False  # (pool, is_new)
    else:
        # 새 수영장 생성
        db_pool = SwimmingPool(**pool.dict())
        db.add(db_pool)
        db.commit()
        db.refresh(db_pool)
        return db_pool, True  # (pool, is_new)

def update_swimming_pool(db: Session, pool_id: int, pool_data: dict):
    db_pool = db.query(SwimmingPool).filter(SwimmingPool.id == pool_id).first()
    if db_pool:
        for key, value in pool_data.items():
            setattr(db_pool, key, value)
        db.commit()
        db.refresh(db_pool)
    return db_pool

def search_nearby_pools(
    db: Session,
    lat: float,
    lng: float,
    radius_km: float = 5.0,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    has_free_swim: Optional[bool] = None,
    only_with_price: bool = False  # 기본적으로 모든 수영장 표시 (가격 추정 포함)
) -> List[SwimmingPool]:
    """
    위도/경도 기반 반경 검색 (Haversine formula)
    """
    # 대략적인 위도/경도 범위 계산 (1도 ≈ 111km)
    lat_range = radius_km / 111.0
    lng_range = radius_km / (111.0 * math.cos(math.radians(lat)))

    query = db.query(SwimmingPool).filter(
        SwimmingPool.lat.between(lat - lat_range, lat + lat_range),
        SwimmingPool.lng.between(lng - lng_range, lng + lng_range),
        SwimmingPool.is_active == True
    )

    # only_with_price=True인 경우에만 가격이 없는 수영장 제외
    if only_with_price:
        query = query.filter(
            SwimmingPool.daily_price.isnot(None)
        )

    if min_price is not None:
        query = query.filter(SwimmingPool.daily_price >= min_price)

    if max_price is not None:
        query = query.filter(SwimmingPool.daily_price <= max_price)

    if has_free_swim is True:
        query = query.filter(SwimmingPool.free_swim_times.isnot(None))

    results = query.all()

    # 정확한 거리 계산 및 필터링
    nearby_pools = []
    for pool in results:
        if pool.lat and pool.lng:
            distance = calculate_distance(lat, lng, pool.lat, pool.lng)
            if distance <= radius_km:
                pool.distance = distance  # 동적 속성 추가
                nearby_pools.append(pool)

    # 거리순 정렬
    nearby_pools.sort(key=lambda x: x.distance)
    return nearby_pools

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Haversine formula로 두 지점 간 거리 계산 (km)
    """
    R = 6371  # 지구 반경 (km)

    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
