---
description: 기능 개발 전체 루프 — 스펙 정의부터 PR까지 에이전트가 자동으로 이어받는다
---

When the user types `/dev-loop <feature>`, execute the following pipeline:

## 세션 시작: 상태 확인

`artifacts/state.md`가 있으면 읽는다.
- `status: in_progress`이면 → 해당 `current_step`부터 재개하고 사용자에게 알린다
- 없거나 `status: done`이면 → Step 0부터 시작

---

## Step 0: 사전 위험 검토 (@pm + pre-mortem skill)

`artifacts/issue.md`가 이미 없을 때만 실행한다.
@pm이 `<feature>`의 외부 통합·설계 리스크를 `pre-mortem` 스킬로 빠르게 검토한다.
Critical 리스크가 있으면 사용자에게 알리고 계속할지 확인한다.

→ 상태 저장: `current_step: 1`

---

## Step 1: 스펙 정의 (@pm + spec-writing skill)

@pm이 `<feature>`를 받아 `spec-writing` 스킬로 `artifacts/issue.md`를 작성한다.
`context/domain-rules.md`와 `context/error-codes.md`를 참조해 도메인 용어와 에러 코드를 일치시킨다.
완료 후 사용자에게 `artifacts/issue.md`를 보여주고 승인을 요청한다.
승인 전까지 Step 2로 진행하지 않는다.

→ 상태 저장: `current_step: 2`

---

## Step 2: 구현 (@engineer + tdd-implement skill)

사용자가 승인하면 @engineer가 `artifacts/issue.md`를 읽는다.
기능이 크면 `incremental-implementation` 스킬로 먼저 슬라이스를 나눈다.
테스트 모드를 선언한 뒤 구현 시작:

- 요구사항 확정 → TDD (수용 기준 하나씩 커밋)
- 설계 탐색 중 → Test-after (구현 완료 후 테스트 추가, PR 전 필수)
- 1회성 코드 → No-test (커밋 메시지에 이유 명시)

막히면 `doubt-driven-development` 또는 `systematic-debugging` 스킬을 사용한다.
구현 완료 후 `code-simplification` 스킬로 리팩터 단계를 실행한다.
모든 기준 완료 시 구현 결과 요약을 출력하고 Step 3으로 이동한다.

→ 상태 저장: `current_step: 3`

---

## Step 3: 리뷰 (@reviewer + code-review skill)

@reviewer가 `code-review` 스킬을 실행한다.
보안 관련 기능이면 `security-and-hardening` 스킬을 추가 실행한다.
중요한 기능이면 `adversarial-reviewer` 스킬로 반대 관점 검토를 추가한다.
`artifacts/review.md`에 결과 저장.

- ✅ 승인 → Step 4로 이동
- ❌ 반려 → @engineer에게 피드백 전달, Step 2로 복귀 (해당 항목만 재처리)

→ 상태 저장: `current_step: 4`

---

## Step 4: QA 검증 (@qa + verification-before-completion skill)

@qa가 `verification-before-completion` 스킬을 실행한다.
`artifacts/issue.md`의 엣지 케이스와 에러 시나리오를 기반으로 테스트한다.
결과를 `artifacts/test-plan.md`에 저장.

- 이슈 발견 → @engineer에게 위임 후 Step 3부터 재시작
- 통과 → Step 5로 이동

→ 상태 저장: `current_step: 5`

---

## Step 5: PR 생성 (@pm + shipping-and-launch skill)

@pm이 `shipping-and-launch` 스킬로 최종 체크리스트를 확인한다.
구현 브랜치에서 main으로 PR을 생성한다.
PR 설명에 `artifacts/issue.md` 수용 기준과 `artifacts/review.md` 리뷰 결과를 포함한다.
PR URL을 사용자에게 출력한다.

→ 상태 저장: `status: done`

---

## 상태 파일 형식 (artifacts/state.md)

각 스텝 완료 시 아래 형식으로 `artifacts/state.md`를 갱신한다:

```markdown
## Workflow State
- workflow: dev-loop
- feature: <feature>
- current_step: <숫자>
- last_completed: Step <N> (<YYYY-MM-DD HH:MM>)
- next_action: <다음에 할 일>
- status: in_progress | done
```
