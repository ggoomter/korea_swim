from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.crud import swimming_pool as crud
from app.schemas.swimming_pool import SwimmingPoolResponse, SwimmingPoolCreate, SwimmingPoolSearch
from database.connection import get_db

router = APIRouter(prefix="/pools", tags=["pools"])

@router.get("/", response_model=List[SwimmingPoolResponse])
def get_pools(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """모든 수영장 조회"""
    pools = crud.get_swimming_pools(db, skip=skip, limit=limit)
    return pools

@router.get("/{pool_id}", response_model=SwimmingPoolResponse)
def get_pool(pool_id: int, db: Session = Depends(get_db)):
    """특정 수영장 조회"""
    pool = crud.get_swimming_pool(db, pool_id=pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="수영장을 찾을 수 없습니다")
    return pool

@router.post("/", response_model=SwimmingPoolResponse)
def create_pool(pool: SwimmingPoolCreate, db: Session = Depends(get_db)):
    """수영장 등록"""
    return crud.create_swimming_pool(db=db, pool=pool)

@router.post("/search", response_model=List[SwimmingPoolResponse])
def search_pools(search: SwimmingPoolSearch, db: Session = Depends(get_db)):
    """위치 기반 수영장 검색"""
    pools = crud.search_nearby_pools(
        db=db,
        lat=search.lat,
        lng=search.lng,
        radius_km=search.radius_km,
        min_price=search.min_price,
        max_price=search.max_price,
        has_free_swim=search.has_free_swim
    )
    return pools
