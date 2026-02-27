from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from app.crud import swimming_pool as crud
from app.schemas.swimming_pool import SwimmingPoolResponse, SwimmingPoolCreate, SwimmingPoolSearch
from database.connection import get_db

router = APIRouter(prefix="/pools", tags=["pools"])

@router.get("/", response_model=List[SwimmingPoolResponse])
def get_pools(
    skip: int = 0,
    limit: int = 1000,
    source: Optional[str] = None,
    has_free_swim: Optional[bool] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    day: Optional[str] = Query(None, description="요일 필터 (월~일)"),
    time: Optional[str] = Query(None, description="시간 필터 (HH:MM)"),
    db: Session = Depends(get_db)
):
    """모든 수영장 조회"""
    pools = crud.get_swimming_pools(
        db,
        skip=skip,
        limit=limit,
        source=source,
        has_free_swim=has_free_swim,
        min_price=min_price,
        max_price=max_price,
        day=day,
        time=time,
    )
    return pools

@router.post("/", response_model=SwimmingPoolResponse)
def create_pool(pool: SwimmingPoolCreate, db: Session = Depends(get_db)):
    """수영장 등록"""
    return crud.create_swimming_pool(db=db, pool=pool)

@router.post("/search", response_model=List[SwimmingPoolResponse])
def search_pools(search: SwimmingPoolSearch, db: Session = Depends(get_db)):
    """위치 기반 수영장 검색 (POST)"""
    pools = crud.search_nearby_pools(
        db=db,
        lat=search.lat,
        lng=search.lng,
        radius_km=search.radius_km,
        min_price=search.min_price,
        max_price=search.max_price,
        has_free_swim=search.has_free_swim,
        day=search.day,
        time=search.time,
    )
    return pools


@router.get("/nearby", response_model=List[SwimmingPoolResponse])
def get_nearby_pools(
    lat: float = Query(..., description="위도"),
    lng: float = Query(..., description="경도"),
    radius: float = Query(5.0, ge=0.1, le=50.0, description="검색 반경 (km)"),
    min_price: Optional[int] = Query(None, description="최소 가격 (자유수영 성인 평일)"),
    max_price: Optional[int] = Query(None, description="최대 가격 (자유수영 성인 평일)"),
    has_free_swim: Optional[bool] = Query(None, description="자유수영 시간표 보유 여부"),
    day: Optional[str] = Query(None, description="요일 필터 (월~일)"),
    time: Optional[str] = Query(None, description="시간 필터 (HH:MM)"),
    sort: Optional[str] = Query(None, description="정렬 (price/distance)"),
    db: Session = Depends(get_db)
):
    """쿼리 파라미터 기반 위치 검색 (프론트엔드용)

    필터 예시:
      ?lat=37.5&lng=126.9&radius=5&day=토&max_price=5000&sort=price
    """
    pools = crud.search_nearby_pools(
        db=db,
        lat=lat,
        lng=lng,
        radius_km=radius,
        min_price=min_price,
        max_price=max_price,
        has_free_swim=has_free_swim,
        day=day,
        time=time,
        sort=sort,
    )

    # 시간 필터 후처리 (SQL에서 처리 불가한 시간 범위 비교)
    if time and day:
        pools = [
            p for p in pools
            if crud.is_time_in_schedule(p.free_swim_schedule, day, time)
        ]

    return pools


@router.get("/{pool_id}", response_model=SwimmingPoolResponse)
def get_pool(
    pool_id: int = Path(..., pattern=r"^\d+$", description="수영장 ID"),
    db: Session = Depends(get_db)
):
    """특정 수영장 조회"""
    pool = crud.get_swimming_pool(db, pool_id=pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="수영장을 찾을 수 없습니다")
    return pool
