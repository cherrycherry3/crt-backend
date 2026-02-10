from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.models import College
from app.schemas.college_schema import CollegeCreate, CollegeUpdate


class AdminCollegeService:
    """
    Admin service for managing colleges
    - ASYNC SAFE
    - SOFT DELETE ENABLED
    """

    # -------------------------------------------------
    # CREATE COLLEGE
    # -------------------------------------------------
    async def create_college(
        self,
        db: AsyncSession,
        payload: CollegeCreate
    ) -> College:
        # Prevent duplicate college code
        existing = await db.scalar(
            select(College).where(College.code == payload.code)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="College with this code already exists"
            )

        college = College(
            name=payload.name,
            code=payload.code,
            description=payload.description,
            email=payload.email,
            phone=payload.phone,
            website=payload.website,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            established_year=payload.established_year,
            is_active=True,
        )

        db.add(college)
        await db.commit()
        await db.refresh(college)

        return college

    # -------------------------------------------------
    # LIST COLLEGES (ACTIVE ONLY)
    # -------------------------------------------------
    async def list_colleges(
        self,
        db: AsyncSession
    ) -> list[College]:
        result = await db.execute(
            select(College)
            .where(College.is_active.is_(True))
            .order_by(College.created_at.desc())
        )
        return result.scalars().all()

    # -------------------------------------------------
    # GET COLLEGE BY ID (ADMIN – ACTIVE / INACTIVE)
    # -------------------------------------------------
    async def get_college(
        self,
        db: AsyncSession,
        college_id: int
    ) -> College | None:
        return await db.scalar(
            select(College).where(College.id == college_id)
        )

    # -------------------------------------------------
    # UPDATE COLLEGE
    # -------------------------------------------------
    async def update_college(
        self,
        db: AsyncSession,
        college_id: int,
        payload: CollegeUpdate
    ) -> College:
        college = await self.get_college(db, college_id)

        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found"
            )

        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(college, field, value)

        await db.commit()
        await db.refresh(college)

        return college

    # -------------------------------------------------
    # DELETE COLLEGE (SOFT DELETE)
    # -------------------------------------------------
    async def delete_college(
        self,
        db: AsyncSession,
        college_id: int
    ) -> bool:
        college = await self.get_college(db, college_id)

        if not college or not college.is_active:
            return False

        college.is_active = False
        await db.commit()

        return True
