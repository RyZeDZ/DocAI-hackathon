from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from models import User
from schemas import UserCreate, UserLogin, UserResponse
from db import get_db
from auth.security import hash_password, verify_password, create_access_token, get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription))
        .where( 
            or_(
                User.email == user_data.email,
                User.username == user_data.username
            )
        )
    )
    user = result.scalars().first()
    if user:
        raise HTTPException(status_code=400, detail="Email or username already registered")

    hashed_pw = await hash_password(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_pw
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription))
        .where(User.email == credentials.email)
    )
    user = result.scalars().first()
    if user is None or not await verify_password(credentials.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token = await create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
