# 작업 요청 템플릿

아래 템플릿을 GitHub Issue와 Codex 요청에 함께 사용할 수 있다.

## Task

`P?-?? — 작업명`

## Purpose

이번 작업이 필요한 이유를 2~4문장으로 설명한다.

## Read first

- `AGENTS.md`
- `docs/PROGRESS.md`
- `docs/RAG_LEARNING_PLAN.md`의 해당 작업

## In scope

- 구현할 항목
- 변경 가능한 범위
- 필요한 테스트
- 필요한 문서 갱신

## Out of scope

- 아직 구현하지 않을 기능
- 다음 Phase 기능
- 불필요한 리팩터링

## Completion criteria

- 외부에서 확인 가능한 동작
- 테스트 통과 조건
- 실패 경로
- 문서 갱신 조건

## Implementation notes

특정 구현을 강제할 필요가 있을 때만 작성한다.
Codex가 기존 구조를 먼저 확인하고 합리적인 구현을 선택하게 한다.

## Completion report

작업 완료 후 다음을 보고한다.

1. 변경한 파일과 내용
2. 입력부터 출력까지의 데이터 흐름
3. 실행한 테스트와 결과
4. 직접 실행해 확인할 방법
5. `PROGRESS.md`와 `DECISIONS.md` 변경 여부
6. 남은 문제와 다음 작업

구현하지 않은 기능을 완료했다고 표현하지 않는다.
