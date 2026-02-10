from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Course, CourseFile
from app.core.s3 import upload_file_to_s3


class AdminCourseFileService:

    # --------------------------------------------------
    # UPLOAD COURSE FILE
    # --------------------------------------------------
    async def upload_course_file(
        self,
        db: AsyncSession,
        course_id: int,
        file: UploadFile,
        file_title: str | None = None,
        file_description: str | None = None,
        duration_seconds: int | None = None,
    ):
        # --------------------------------------------------
        # 1️⃣ Validate course
        # --------------------------------------------------
        result = await db.execute(
            select(Course).where(Course.id == course_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # --------------------------------------------------
        # 2️⃣ Upload file to S3
        # --------------------------------------------------
        s3_result = await upload_file_to_s3(
            file=file,
            folder=f"Courses/{course_id}",
        )

        # --------------------------------------------------
        # 3️⃣ Detect file type
        # --------------------------------------------------
        content_type = file.content_type or ""

        if content_type == "application/pdf":
            file_type = "PDF"
        elif content_type.startswith("video/"):
            file_type = "VIDEO"
        else:
            file_type = "DOCUMENT"

        # --------------------------------------------------
        # 4️⃣ Update course thumbnail URL
        # --------------------------------------------------
        course.thumbnail_url = s3_result["file_url"]

        # --------------------------------------------------
        # 5️⃣ Save course file record
        # --------------------------------------------------
        course_file = CourseFile(
            course_id=course_id,
            file_name=file.filename,
            file_title=file_title or file.filename,
            file_description=file_description,
            duration_seconds=duration_seconds,
            file_type=file_type,
            file_size=s3_result["file_size"],
            mime_type=s3_result["content_type"],
            file_url=s3_result["file_url"],
            is_published=True,
            download_allowed=True,
        )

        db.add(course_file)

        # --------------------------------------------------
        # 6️⃣ Commit transaction
        # --------------------------------------------------
        await db.commit()

        await db.refresh(course_file)
        await db.refresh(course)

        return course_file

    # --------------------------------------------------
    # LIST COURSE FILES
    # --------------------------------------------------
    async def list_course_files(
        self,
        db: AsyncSession,
        course_id: int,
    ):
        result = await db.execute(
            select(CourseFile)
            .where(CourseFile.course_id == course_id)
            .order_by(CourseFile.created_at.desc())
        )
        return result.scalars().all()
