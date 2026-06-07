---
description: PR 리뷰 루프 — 기존 PR을 받아 스펙 준수 + 품질 검토 후 피드백 작성
---

When the user types `/pr-review <PR번호 또는 브랜치명>`, execute the following:

## Step 1: 컨텍스트 수집

PR의 변경 파일 목록과 diff를 수집한다.
`artifacts/issue.md`가 있으면 읽어 수용 기준을 파악한다.
없으면 PR 설명에서 목적을 추론한다.

## Step 2: 스펙 준수 리뷰 (@reviewer)

@reviewer가 `code-review` 스킬의 Stage 1을 실행한다.
미충족 기준 목록을 `artifacts/review.md`에 기록한다.

## Step 3: 코드 품질 리뷰 (@reviewer)

스펙 준수 확인 완료 후 `code-review` 스킬의 Stage 2를 실행한다.
결과를 `artifacts/review.md`에 추가한다.

## Step 4: 피드백 출력

`artifacts/review.md` 전체를 사용자에게 출력한다.
반드시 고칠 항목 / 권장 사항 / 참고용 세 그룹으로 분리해 보여준다.
