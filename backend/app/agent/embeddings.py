import os
from openai import AsyncOpenAI

# OpenAI client initialization
# It uses the OPENAI_API_KEY environment variable by default
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_embedding(text: str) -> list[float]:
    """
    Get the embedding vector for the given text using OpenAI API.
    Uses 'text-embedding-3-small' which returns a 1536-dimensional vector.
    """
    # If no API key is provided, return a mock embedding for testing purposes
    if not os.getenv("OPENAI_API_KEY"):
        return [0.0] * 1536

    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


async def store_goal_embedding(goal_id: int, user_id: int):
    """
    Generate a summary of a completed goal and store its embedding.
    Runs in the background, fetches the goal fresh from DB.
    """
    from app.db.session import AsyncSessionLocal
    from app.models.goal import Goal
    from app.models.milestone import Milestone
    from app.models.goal_embedding import GoalEmbedding
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        # 0. Goal 가져오기 (Milestone, Todo 포함)
        result = await db.execute(
            select(Goal)
            .where(Goal.id == goal_id)
            .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
        )
        goal = result.scalar_one_or_none()
        if not goal:
            return

        # 1. 목표 데이터 요약 문자열 생성
    
    # 1. 목표 데이터 요약 문자열 생성
    # goal.milestones와 goal.milestones.todos가 로드되어 있어야 합니다.
    milestones_info = []
    for m in getattr(goal, "milestones", []):
        todos_info = [f"  - {t.title} ({t.estimated_minutes}분)" for t in getattr(m, "todos", [])]
        milestones_info.append(f"마일스톤: {m.title}\n" + "\n".join(todos_info))
    
    summary = (
        f"목표: {goal.title}\n"
        f"원래 입력: {goal.raw_input}\n"
        f"기간: ~{goal.deadline}\n"
        f"할당 시간: 평일 {goal.available_hours_weekday}시간, 주말 {goal.available_hours_weekend}시간\n\n"
        + "\n\n".join(milestones_info)
    )
    
    # 2. 임베딩 생성
    vector = await get_embedding(summary)
    
    # 3. DB에 저장 (기존에 있으면 업데이트)
    from sqlalchemy import select
    result = await db.execute(select(GoalEmbedding).where(GoalEmbedding.goal_id == goal.id))
    existing = result.scalar_one_or_none()
    
        if existing:
            existing.embedding = vector
            existing.content_summary = summary
        else:
            new_embedding = GoalEmbedding(
                goal_id=goal.id,
                user_id=user_id,
                content_summary=summary,
                embedding=vector
            )
            db.add(new_embedding)
        
        await db.commit()


async def search_similar_goals(db, user_id: int, new_goal_text: str, limit: int = 3):
    """
    Find past completed goals for the user that are similar to the new goal text.
    """
    from app.models.goal_embedding import GoalEmbedding
    from sqlalchemy import select
    
    # 1. 새 목표 텍스트 임베딩
    vector = await get_embedding(new_goal_text)
    
    # 2. 벡터 유사도 검색 (Cosine Distance <-> Cosine Similarity)
    # pgvector uses `<=>` for cosine distance. We order by it ascending.
    query = (
        select(GoalEmbedding)
        .where(GoalEmbedding.user_id == user_id)
        .order_by(GoalEmbedding.embedding.cosine_distance(vector))
        .limit(limit)
    )
    
    result = await db.execute(query)
    embeddings = result.scalars().all()
    
    return [e.content_summary for e in embeddings]
