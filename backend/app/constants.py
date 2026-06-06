# backend/app/constants.py
"""프로젝트 전역 상수 정의.

MVP 단계에서는 단일 사용자(user_id=1)를 사용합니다.
인증 도입 시 이 상수를 제거하고 JWT 토큰에서 user_id를 읽도록 변경하세요.
"""

MVP_USER_ID: int = 1
