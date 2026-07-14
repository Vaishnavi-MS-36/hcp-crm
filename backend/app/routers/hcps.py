from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@router.get("", response_model=List[schemas.HCPOut])
def search_hcps(q: str = "", db: Session = Depends(get_db)):
    query = db.query(models.HCP)
    if q:
        query = query.filter(models.HCP.name.ilike(f"%{q}%"))
    return query.limit(20).all()
