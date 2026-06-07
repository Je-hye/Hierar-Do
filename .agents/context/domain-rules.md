# Domain Rules

## 핵심 용어

| 용어 | 정의 | 코드에서 사용하는 이름 |
|------|------|----------------------|
| 목표 | 사용자의 월간 달성 목표 | `Goal` |
| 마일스톤 | 목표를 4등분한 주간 중간 목표 | `Milestone` |
| 할 일 | 마일스톤을 구성하는 일별 실행 단위 | `Todo` |
| 가용 시간 | 사용자가 하루에 쓸 수 있는 학습/작업 시간 | `available_hours` |
| 소요 시간 | AI가 추정한 Todo 1개 완료에 필요한 분 | `estimated_minutes` |
| AI 제안 | AI가 생성한 마일스톤 또는 할 일 | `suggested_by_ai=True` |

## 데이터 계층

```
Goal (월간, 사용자당 N개)
└── Milestone (주간, 목표당 정확히 4개)
    └── Todo (일별, 마일스톤당 N개)
```

## 비즈니스 규칙

- 목표 하나당 마일스톤은 **반드시 4개** — 초과/미만 생성 금지
- `schedule` 노드: 하루 배분된 `estimated_minutes` 합이 `available_hours` 초과 시 다음 날로 이월
- `suggested_by_ai=True`인 항목은 사용자 승인 전까지 `pending` 상태
- LLM은 `parse_goal`과 `decompose` 노드에서만 호출 — `schedule`, `store`에서 LLM 호출 금지

## 불변 조건

- Goal의 `status`: `pending` → `active` → `done` (역방향 전환 불가)
- Todo의 `due_date`는 Goal의 `deadline`을 초과할 수 없음
- `estimated_minutes`는 양의 정수만 허용

## 금지 패턴

- `schedule` 노드에서 Claude API 호출 금지 (비용 최적화 설계)
- MVP 단계에서 `user_id=1` 외 멀티유저 로직 추가 금지
- pgvector, 인증(JWT), suggest/apply 등 고도화 기능은 별도 브랜치에서 진행
