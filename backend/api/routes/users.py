from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from core.db import get_db
from core.security import get_current_user, get_password_hash
from models.models import User as UserModel
from api.schemas.users import UserCreate, UserUpdate, User

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверка, что пользователь с таким email не существует
    result = await db.execute(select(UserModel).where(UserModel.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Создание нового пользователя
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(email=user.email, password_hash=hashed_password)
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user

@router.get("/me", response_model=User)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=User)
async def update_user(
    user: UserUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Обновление данных пользователя
    if user.email is not None and user.email != current_user.email:
        # Проверка, что новый email не занят
        result = await db.execute(select(UserModel).where(UserModel.email == user.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user.email
    
    if user.password is not None:
        current_user.password_hash = get_password_hash(user.password)
    
    await db.flush()
    await db.refresh(current_user)
    return current_user