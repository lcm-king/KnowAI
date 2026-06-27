from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Course,
    CourseReview,
    Favorite,
    Order,
    OrderItem,
    Teacher,
    User,
    UserCourse,
)


async def hard_delete_user(db: AsyncSession, user: User) -> None:
    user_id = user.id

    # 教师用户:先处理其名下课程
    if user.teacher_id is not None:
        teacher_id = user.teacher_id
        course_count = await db.scalar(
            select(func.count()).select_from(
                select(Course).where(Course.teacher_id == teacher_id).subquery()
            )
        )
        if course_count:
            # 找一个其他教师接收课程
            other_teacher_id = await db.scalar(
                select(Teacher.id).where(Teacher.id != teacher_id).limit(1)
            )
            if other_teacher_id is None:
                raise ValueError("该用户是教师且仍有关联课程,系统无其他教师可转移,请先手动处理课程")
            await db.execute(
                update(Course)
                .where(Course.teacher_id == teacher_id)
                .values(teacher_id=other_teacher_id)
            )
        # 先解除 user→teacher 引用,否则删 teacher 会触发外键约束
        user.teacher_id = None
        await db.flush()
        await db.execute(delete(Teacher).where(Teacher.id == teacher_id))

    # 按外键依赖顺序清理用户关联数据
    await db.execute(
        delete(OrderItem).where(
            OrderItem.order_id.in_(
                select(Order.id).where(Order.user_id == user_id)
            )
        )
    )
    await db.execute(delete(Order).where(Order.user_id == user_id))
    await db.execute(delete(UserCourse).where(UserCourse.user_id == user_id))
    await db.execute(delete(Favorite).where(Favorite.user_id == user_id))
    await db.execute(delete(CourseReview).where(CourseReview.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
