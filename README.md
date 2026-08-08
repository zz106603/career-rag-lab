# career-rag-lab

기존 취업 관련 샘플 문서를 사용해 RAG의 수집, Chunking, Embedding,
Vector Search, 생성, 평가 과정을 학습하는 프로젝트다.

## 진행 방법

1. `docs/PROGRESS.md`에서 현재 작업을 확인한다.
2. `docs/RAG_LEARNING_PLAN.md`의 해당 절만 읽는다.
3. GitHub Issue에 `docs/TASK_TEMPLATE.md`를 사용한다.
4. Codex에는 현재 Issue 범위만 요청한다.
5. 구현과 테스트 후 `docs/PROGRESS.md`를 갱신한다.

## 고정 순서

```text
Phase 0: 환경과 평가 기준
Phase 1: LangChain 없는 수동 RAG
Phase 2: LangChain 단계별 적용
Phase 3: Hybrid Search, reranking, 평가
```

Java/Spring 이식은 이 저장소 범위에 포함하지 않는다.

## 문서

- `AGENTS.md`: Codex 상시 규칙
- `docs/RAG_LEARNING_PLAN.md`: 전체 학습 계획
- `docs/PROGRESS.md`: 현재 작업과 완료 상태
- `docs/DECISIONS.md`: 중요한 기술 결정
- `docs/TASK_TEMPLATE.md`: Issue 및 Codex 요청 템플릿
- `docs/FINAL_REVIEW.md`: Phase 3 종료 검토

## 로컬 실행

Python 3.11 이상이 필요하다. 저장소 루트에서 가상 환경을 만들고 개발 의존성을 설치한다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

환경변수가 필요할 때는 `.env.example`을 `.env`로 복사한 뒤 실제 값을 `.env`에만 입력한다. `.env`와 API 키는 Git에 커밋하지 않는다.

Embedding 설정은 기본적으로 비용이 낮은 `text-embedding-3-small`, 1536차원, batch 크기 100을 사용한다. 실제 OpenAI API를 호출하는 최소 검증은 유료 호출임을 명시하는 다음 옵션으로만 실행된다.

```powershell
pytest -m live_api --run-live-api
```

FastAPI 애플리케이션을 실행한다.

```powershell
uvicorn app.main:app --reload
```

`http://127.0.0.1:8000/health`에서 상태를 확인할 수 있다.

## Qdrant 실행

Docker Desktop을 실행한 뒤 저장소 루트에서 Qdrant를 시작한다.

```powershell
docker compose up -d
docker compose ps
```

Qdrant REST API는 `http://localhost:6333`, gRPC API는 `localhost:6334`에서 사용할 수 있다. 데이터는 Docker의 `qdrant_storage` named volume에 유지된다. 애플리케이션은 `QDRANT_URL` 환경변수를 사용하며 기본값은 `http://localhost:6333`이다.

학습 문서 전체를 실제 OpenAI Embedding으로 변환해 `career_documents`에 저장한다. 이 명령은 유료 OpenAI API를 호출한다.

```powershell
python -m app.index_documents
```

완료 후 `http://localhost:6333/dashboard`의 Collections 화면에서 `career_documents`를 선택하면 Point와 payload를 볼 수 있다. 같은 명령을 다시 실행해도 문서 단위로 교체되므로 Point 수는 증가하지 않는다.

REST API로 원문과 metadata를 확인하려면 다음 명령을 사용한다.

```powershell
$body = @{ limit = 10; with_payload = $true; with_vector = $false } | ConvertTo-Json
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:6333/collections/career_documents/points/scroll" `
    -ContentType "application/json" `
    -Body $body
```

실제 Qdrant 연결 상태를 검사하려면 통합 테스트를 실행한다.

```powershell
pytest -m integration --run-integration
```

사용을 마친 컨테이너는 다음 명령으로 중지한다. 이 명령은 저장 볼륨을 삭제하지 않는다.

```powershell
docker compose down
```

## 테스트

```powershell
pytest
```
