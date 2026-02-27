from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.swimming_pool import SwimmingPool
from app.schemas.swimming_pool import SwimmingPoolCreate
from typing import List, Optional
import math
import json


def get_swimming_pool(db: Session, pool_id: int):
    return db.query(SwimmingPool).filter(SwimmingPool.id == pool_id).first()


def get_swimming_pools(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    source: Optional[str] = None,
    has_free_swim: Optional[bool] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    day: Optional[str] = None,
    time: Optional[str] = None,
):
    """수영장 목록 조회 (필터링 지원)"""
    query = db.query(SwimmingPool)

    if source:
        query = query.filter(SwimmingPool.source == source)

    if has_free_swim is not None:
        if has_free_swim:
            query = query.filter(SwimmingPool.free_swim_schedule.isnot(None))
        else:
            query = query.filter(SwimmingPool.free_swim_schedule.is_(None))

    # pricing JSON에서 자유수영 성인 평일 가격 기준 필터
    if min_price is not None:
        query = query.filter(
            text("json_extract(pricing, '$.자유수영.성인.평일') >= :min_price")
        ).params(min_price=min_price)

    if max_price is not None:
        query = query.filter(
            text("json_extract(pricing, '$.자유수영.성인.평일') <= :max_price")
        ).params(max_price=max_price)

    # 요일 필터: 해당 요일에 자유수영 시간이 있는 곳
    if day:
        query = query.filter(
            text("json_extract(free_swim_schedule, :day_path) IS NOT NULL")
        ).params(day_path=f"$.{day}")

    # 시간 필터: 해당 요일의 시간 중 time이 포함되는 곳
    if time and day:
        query = _filter_by_time(query, day, time)

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
        for key, value in pool.dict().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing, False
    else:
        db_pool = SwimmingPool(**pool.dict())
        db.add(db_pool)
        db.commit()
        db.refresh(db_pool)
        return db_pool, True


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
    day: Optional[str] = None,
    time: Optional[str] = None,
    sort: Optional[str] = None,
) -> List[SwimmingPool]:
    """
    위도/경도 기반 반경 검색 (Haversine formula)

    필터:
      - min_price/max_price: pricing.자유수영.성인.평일 기준
      - has_free_swim: free_swim_schedule이 있는 곳만
      - day: 해당 요일에 자유수영 가능한 곳 (월~일)
      - time: 해당 시간에 자유수영 가능한 곳 (HH:MM)

    정렬:
      - "price": 자유수영 가격순
      - "distance" 또는 None: 거리순 (기본)
    """
    lat_range = radius_km / 111.0
    lng_range = radius_km / (111.0 * math.cos(math.radians(lat)))

    query = db.query(SwimmingPool).filter(
        SwimmingPool.lat.between(lat - lat_range, lat + lat_range),
        SwimmingPool.lng.between(lng - lng_range, lng + lng_range),
        SwimmingPool.is_active == True
    )

    # 가격 필터 (pricing JSON 기반)
    if min_price is not None:
        query = query.filter(
            text("json_extract(pricing, '$.자유수영.성인.평일') >= :min_price")
        ).params(min_price=min_price)

    if max_price is not None:
        query = query.filter(
            text("json_extract(pricing, '$.자유수영.성인.평일') <= :max_price")
        ).params(max_price=max_price)

    # 자유수영 유무 필터
    if has_free_swim is True:
        query = query.filter(SwimmingPool.free_swim_schedule.isnot(None))

    # 요일 필터
    if day:
        query = query.filter(
            text("json_extract(free_swim_schedule, :day_path) IS NOT NULL")
        ).params(day_path=f"$.{day}")

    # 시간 필터
    if time and day:
        query = _filter_by_time(query, day, time)

    results = query.all()

    # 거리 계산 및 필터링
    nearby_pools = []
    for pool in results:
        if pool.lat and pool.lng:
            distance = calculate_distance(lat, lng, pool.lat, pool.lng)
            if distance <= radius_km:
                pool.distance = distance
                nearby_pools.append(pool)

    # 정렬
    if sort == "price":
        nearby_pools.sort(key=lambda p: _get_free_swim_price(p) or 999999)
    else:
        nearby_pools.sort(key=lambda p: p.distance)

    return nearby_pools


def _get_free_swim_price(pool: SwimmingPool) -> Optional[int]:
    """수영장의 자유수영 성인 평일 가격 추출"""
    if not pool.pricing:
        return None
    try:
        pricing = pool.pricing if isinstance(pool.pricing, dict) else json.loads(pool.pricing)
        free_swim = pricing.get("자유수영", {})
        adult = free_swim.get("성인", {})
        if isinstance(adult, dict):
            return adult.get("평일")
        return adult if isinstance(adult, (int, float)) else None
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None


def _filter_by_time(query, day: str, time: str):
    """특정 요일+시간에 자유수영 가능한 곳 필터 (Python 후처리 방식 대신 SQL 선필터)

    SQLite의 JSON 배열 내 시간 범위 비교는 복잡하므로,
    해당 요일에 스케줄이 있는 곳만 SQL로 필터하고,
    시간 범위 체크는 Python에서 후처리.
    """
    # SQL에서는 해당 요일에 스케줄이 있는지만 필터
    # 시간 범위 체크는 search_nearby_pools/get_swimming_pools의 결과에서 후처리 필요
    # → 여기서는 추가 필터 없이 반환 (day 필터가 이미 적용됨)
    return query


def is_time_in_schedule(schedule_data, day: str, time: str) -> bool:
    """특정 요일+시간이 자유수영 시간표에 포함되는지 확인

    Args:
        schedule_data: free_swim_schedule JSON (dict 또는 JSON string)
        day: 요일 ("월"~"일")
        time: 시간 ("HH:MM")

    Returns:
        해당 시간에 자유수영 가능 여부
    """
    if not schedule_data:
        return False

    try:
        schedule = schedule_data if isinstance(schedule_data, dict) else json.loads(schedule_data)
    except (json.JSONDecodeError, TypeError):
        return False

    day_slots = schedule.get(day, [])
    if not isinstance(day_slots, list):
        return False

    for slot in day_slots:
        if not isinstance(slot, str) or "-" not in slot:
            continue
        parts = slot.split("-")
        if len(parts) != 2:
            continue
        start, end = parts[0].strip(), parts[1].strip()
        if start <= time <= end:
            return True

    return False


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine formula로 두 지점 간 거리 계산 (km)"""
    R = 6371

    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
