# 현재 진행 상태

## Current phase

Phase 1 — LangChain 없이 RAG 직접 구현

## Current task

P1-06 — Prompt와 답변 생성

## Goal

- 검색된 Chunk만 Context로 사용해 질문에 답한다.
- 답변에 사용한 출처를 검색 결과와 별도로 반환한다.
- 검색 근거가 부족하면 LLM 호출 없이 답변을 거부한다.

## In scope

- 질문과 Context를 구분한 Prompt 구성
- 검색 결과 기반 OpenAI 답변 생성
- 답변과 출처 응답 구조
- 근거 부족 판정과 LLM 호출 생략
- 검색 결과와 생성 답변의 분리 관찰
- 단위 테스트와 실제 API 검증

## Out of scope

- 문서 변경 감지와 증분 재색인
- Hybrid Search와 reranking
- 대화 기록과 멀티턴 질의
- LangChain

## Completion criteria

- 검색 결과와 생성 답변을 별도로 확인할 수 있다.
- 답변에 사용된 출처를 확인할 수 있다.
- 문서 근거 안에서만 답변하도록 Prompt가 제한한다.
- 근거가 부족하면 LLM을 호출하지 않고 답변을 거부한다.
- 문서에 없는 경험을 사실처럼 생성하지 않는다.

## Completed

- P0-01 프로젝트 초기화
  - `pyproject.toml`에 Python 3.11, FastAPI, Uvicorn, pytest, httpx 의존성과 pytest 설정을 정의했다.
  - `app/main.py`에 FastAPI 애플리케이션과 `GET /health`를 구현했다.
  - `tests/test_health.py`에 HTTP 200과 `{\"status\": \"ok\"}` 응답 검증을 추가했다.
  - `.env.example`과 `.gitignore`로 로컬 비밀정보 관리 기준을 만들었다.
  - README에 가상환경 생성, 설치, 실행, 테스트 방법을 추가했다.
- P0-02 Docker Compose 기반 Qdrant 실행 환경 구성
  - `compose.yaml`에 Qdrant 1.15.5 서비스와 REST/gRPC 포트 매핑을 정의했다.
  - `qdrant_storage` named volume을 `/qdrant/storage`에 연결했다.
  - `QDRANT_URL` 설정과 Qdrant 클라이언트 생성·상태 확인 로직을 추가했다.
  - 외부 서비스 없는 단위 테스트와 실제 Qdrant 연결 통합 테스트를 분리했다.
  - README에 Qdrant 실행, 상태 확인, 중지 방법을 추가했다.
  - named volume 선택 이유를 `docs/DECISIONS.md`의 D-003에 기록했다.
- P0-03 학습용 문서 준비
  - `data/documents`에 서로 다른 주제의 합성 Markdown 문서 6개를 작성했다.
  - 정밀 의료, 재무자료 전송, 소셜 분석, 장애 대응, 백엔드 기술, 경험 범위를 구분했다.
  - 모든 문서에 합성 학습 데이터임을 표시하고 실제 인물이나 회사의 경력이 아님을 명시했다.
  - Kafka, Kubernetes, Go, OpenFGA의 미경험 사실을 별도 문서에 명시했다.
  - 문서 개수, 합성 데이터 표시, 연락처 패턴 부재, 미경험 기술 표현을 검증하는 테스트를 추가했다.
- P0-04 평가 질문 세트 준비
  - `data/evaluation/questions.json`에 평가 질문 15개를 작성했다.
  - 의미 검색, 정확한 기술명, 프로젝트 조건, 다중 문서, 답변 거부 유형을 각각 3개씩 구성했다.
  - 각 질문에 고유 ID, category, 기대 출처, 답변 가능 여부를 기록했다.
  - 답변 불가능한 질문은 기대 출처를 빈 배열로 두어 근거 부족 판정을 명확히 했다.
  - 질문 구조, 유형 분포, 출처 파일, 답변 가능 여부의 일관성을 검증하는 테스트를 추가했다.
- P1-01 문서 모델과 로더
  - 원문과 metadata를 분리한 불변 `Document`, `DocumentMetadata` 모델을 정의했다.
  - 단일 Markdown 파일과 디렉터리를 UTF-8로 읽는 로더를 구현했다.
  - source, 파일명, 문서 유형, 프로젝트명을 metadata로 보존했다.
  - 프로젝트 문서는 최상위 제목을 프로젝트명으로 사용하고 기술·경험 문서는 profile로 구분했다.
  - 빈 Markdown은 전체 디렉터리 로딩을 중단하고, 단일 비 Markdown 파일은 명시적으로 거부하도록 했다.
  - 오류를 조용히 건너뛰지 않는 이유를 `docs/DECISIONS.md`의 D-004에 기록했다.
- P1-02 Chunking
  - 불변 `Chunk`, `ChunkMetadata` 모델과 구조 기반·고정 크기 분할 전략을 구현했다.
  - 구조 기반 전략은 Markdown 제목, 빈 줄, 줄바꿈 순으로 자연스러운 경계를 우선한다.
  - 고정 크기 전략은 기본 500자와 50자 overlap을 사용한다.
  - 모든 Chunk에 결정적 chunk ID·document ID, source, section, index, 문서 유형, 프로젝트명, 전략, 원문 문자 범위를 보존했다.
  - 전략별 Chunk 목록을 동시에 반환하는 비교 함수를 추가했다.
  - ID와 원문 위치 설계를 `docs/DECISIONS.md`의 D-005에 기록했다.
- P1-03 Embedding 생성
  - OpenAI Python SDK를 사용해 하나 이상의 Chunk를 batch 단위로 Embedding하는 로직을 구현했다.
  - `text-embedding-3-small`, 1536차원, batch 크기 100을 저비용 기본 설정으로 추가했다.
  - `.env`를 자동 로딩하고 API 키가 설정 객체 표현에 노출되지 않게 했다.
  - 입력 순서와 API response index를 연결하고 반환 개수와 벡터 차원을 검증했다.
  - 빈 입력, API 오류, 응답 개수·차원 오류를 실제 API 없이 테스트했다.
  - 유료 실제 API 테스트를 `--run-live-api` 옵션으로 분리하고 작은 Chunk 하나의 1536차원 벡터 생성을 확인했다.
  - 모델 선택 이유를 `docs/DECISIONS.md`의 D-006에 기록했다.
- P1-04 Qdrant 색인
  - Collection을 생성하고 기존 Collection의 vector size와 Cosine distance 설정을 검증하는 `QdrantIndexer`를 구현했다.
  - 결정적 chunk ID를 Qdrant가 허용하는 UUID5 Point ID로 변환하고 원래 ID는 payload에 보존했다.
  - content, source, section, document ID, Chunk metadata와 원문 위치를 payload로 저장했다.
  - 새 입력을 검증한 후 document ID로 기존 Point를 삭제하고 현재 Chunk 집합을 upsert하도록 구현했다.
  - 동일 문서 재색인, stale Chunk 제거, 문서 단위 삭제와 다른 문서 보존을 검증했다.
  - 전체 학습 문서를 로딩·Chunking·Embedding·색인하는 `python -m app.index_documents` 실행 명령을 추가했다.
  - Qdrant 서버 1.15.5와 Python Client 1.15.1의 minor 버전을 맞춰 호환성 경고를 제거했다.
  - 문서 단위 교체 전략을 `docs/DECISIONS.md`의 D-007에 기록했다.
- P1-05 Vector Search
  - 질문을 OpenAI로 한 번 Embedding하고 Qdrant에서 Cosine 유사 Chunk를 조회하는 `SearchService`를 구현했다.
  - content, source, score, metadata를 보존하는 독립적인 `SearchResult` 모델을 추가했다.
  - `top_k`와 score threshold를 요청별로 조정하고 근거가 없으면 빈 목록을 반환하도록 했다.
  - LLM과 answer 필드 없이 검색 근거만 반환하는 `POST /search` API를 추가했다.
  - 검색과 생성 답변 분리 결정을 `docs/DECISIONS.md`의 D-008에 기록했다.

## Verified

- `.venv\Scripts\python.exe -m pytest -q`: 1 passed, 1 warning
- 테스트 데이터 흐름: pytest → FastAPI `TestClient` → `GET /health` 라우트 → JSON 응답 → 상태 코드와 본문 검증
- `git check-ignore -v .env .idea/workspace.xml .venv/pyvenv.cfg`: 세 경로 모두 제외 규칙 적용 확인
- `docker compose config`: Compose 구성 유효성 확인
- `docker compose ps`: `qdrant/qdrant:v1.15.5`가 포트 6333, 6334에서 실행 중임을 확인
- `docker volume inspect career-rag-lab_qdrant_storage`: named volume 생성 및 마운트 확인
- `.venv\Scripts\python.exe -m pytest -q`: 4 passed, 1 skipped, 1 warning
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 1 passed, 4 deselected, 1 warning
- Qdrant 상태 확인 데이터 흐름: `QDRANT_URL` → `QdrantClient` → REST API의 collection 목록 조회 → 정상 응답을 연결 가능 상태로 판정
- `.venv\Scripts\python.exe -m pytest -q tests/test_learning_documents.py`: 4 passed
- `.venv\Scripts\python.exe -m pytest -q`: 8 passed, 1 skipped, 1 warning
- 학습 문서 데이터 흐름: `data/documents/*.md` → 파일 개수 및 UTF-8 본문 로딩 → 합성 데이터 문구·연락처 패턴·경험 경계 검증
- `.venv\Scripts\python.exe -m pytest -q tests/test_evaluation_questions.py`: 4 passed
- `.venv\Scripts\python.exe -m pytest -q`: 12 passed, 1 skipped, 1 warning
- 평가 데이터 흐름: `questions.json` → JSON 파싱 → 필수 필드·고유 ID·유형 분포 확인 → `expected_sources`와 실제 Markdown 파일명 대조 → `answerable` 일관성 검증
- `.venv\Scripts\python.exe -m pytest -q tests/test_documents.py`: 9 passed
- `.venv\Scripts\python.exe -m pytest -q`: 21 passed, 1 skipped, 1 warning
- 문서 로딩 데이터 흐름: 파일 경로 → 경로·확장자·빈 내용 검증 → UTF-8 원문 로딩 → H1 제목과 `프로젝트 개요` 구조 해석 → 원문과 metadata가 분리된 `Document` 반환
- `.venv\Scripts\python.exe -m pytest -q tests/test_chunking.py`: 10 passed
- `.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_health.py`: 30 passed, 1 skipped
- 전체 pytest 시도: Chunking 포함 30 passed, Qdrant 통합 1 skipped, 기존 health 테스트 1 failed (`WinError 10014`)
- 180자 기준 실제 비교: 구조 기반 Chunk는 56~180자이며 section 경계를 보존했고, 고정 크기 Chunk는 대부분 180자이며 인접 Chunk에 20자 overlap이 적용됐다.
- Chunking 데이터 흐름: `Document` → 제목 위치와 section 분석 또는 고정 문자 범위 계산 → source·section·원문 위치 metadata 복사 → 입력·전략·범위·content 해시 → `Chunk` 목록
- `.venv\Scripts\python.exe -m pytest -q tests/test_config.py tests/test_embeddings.py`: 15 passed
- `.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_health.py`: 43 passed, 2 skipped
- `.venv\Scripts\python.exe -m pytest -q -m live_api --run-live-api`: 1 passed, 40 deselected, 1 warning
- 실제 설정 확인: API 키 설정됨, `text-embedding-3-small`, 1536차원, batch 크기 100, Settings repr에서 키 숨김
- Embedding 데이터 흐름: `.env` → 비밀 키·모델·차원·batch 설정 → Chunk content 목록을 batch로 분할 → OpenAI Embeddings API → response index 정렬 → 개수·차원 검증 → 원본 Chunk와 vector를 결합한 `EmbeddedChunk`
- `.venv\Scripts\python.exe -m pytest -q tests/test_indexing.py`: 8 passed
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 2 passed, 54 deselected, 1 warning
- `.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_health.py`: 53 passed, 3 skipped
- 실제 Qdrant 임시 Collection에서 Point 2개와 payload·4차원 벡터 저장, 동일 문서 재색인 후 2개 유지, Chunk 축소 후 1개, 문서 삭제 후 0개를 확인했다.
- 실제 OpenAI API와 영속 Qdrant를 연결해 학습 문서 6개를 28개 Chunk로 색인했다.
- `career_documents` 직접 조회 결과 Point 28개, 문서 6개, vector size 1536, Cosine distance를 확인했다.
- 저장된 모든 Point를 읽어 source별 4~5개 Chunk와 content, source, section, 원문 위치를 포함한 payload 및 1536차원 vector를 확인했다.
- Qdrant 색인 데이터 흐름: `EmbeddedChunk` 목록 → 단일 document ID·고유 chunk ID·벡터 차원 검증 → Collection 생성 또는 설정 확인 → 기존 document ID Point 삭제 → UUID5 Point ID와 payload 변환 → wait 방식 upsert
- 전체 색인 데이터 흐름: `data/documents`의 Markdown 6개 → 구조 기반 Chunk 28개 → OpenAI batch Embedding → 문서별 기존 Point 교체 → `career_documents` 영속 Collection
- `.venv\Scripts\python.exe -m pytest -q tests/test_search.py tests/test_search_api.py`: 8 passed, 1 warning
- `.venv\Scripts\python.exe -m pytest -q tests/test_search_integration.py --run-integration`: 1 passed
- `.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_health.py`: 61 passed, 4 skipped, 1 warning
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 3 passed, 63 deselected, 1 warning
- `.venv\Scripts\python.exe -m pytest -q`: 62 passed, 4 skipped, 1 warning
- 실제 질문 `장애 대응 자동화 경험이 있나요?` 검색 결과 `incident-response-tool.md`가 score 0.4869와 0.4575로 1·2위에 반환됐다.
- 답변 불가능 평가 질문의 상위 score가 0.2924, 0.2895, 0.2863이었고 threshold 0.5 적용 시 빈 결과가 반환됐다.
- Vector Search 데이터 흐름: 질문 → OpenAI Embedding 1개 → Qdrant Cosine 검색 → top_k·threshold 적용 → content·source·score·metadata를 가진 결과 목록

## Learned

- 애플리케이션 상태 확인은 외부 서비스에 의존하지 않는 단순한 엔드포인트로 시작하면 프로젝트 실행 가능 여부를 독립적으로 검증할 수 있다.
- Windows 환경에서 최초 pip 설치 시 출력 인코딩 관련 `OSError`가 발생했으며, UTF-8 출력과 progress bar 비활성화 후 설치가 완료됐다.
- 외부 서비스 통합 테스트를 기본 테스트와 분리하면 Docker가 없는 환경에서도 단위 테스트를 실행하면서 실제 연결 검증을 명시적으로 수행할 수 있다.
- Docker named volume은 컨테이너와 데이터의 생명주기를 분리하므로 `docker compose down` 이후에도 데이터를 보존한다.
- 평가용 문서에 사실과 미경험 범위를 함께 기록하면 이후 RAG가 유사 기술을 실제 경험으로 과장하는지 검증할 수 있다.
- 프로젝트별 문서와 기술 요약 문서를 분리하면 단일 출처 검색과 여러 출처를 결합하는 검색을 모두 평가할 수 있다.
- 평가 질문에 category를 명시하면 이후 검색 전략별로 어떤 유형에서 품질이 낮은지 분리해 측정할 수 있다.
- 답변 불가능 질문의 기대 출처를 빈 배열로 두면 검색 실패와 올바른 답변 거부를 구분하는 기준으로 사용할 수 있다.
- 원문을 수정하지 않고 metadata를 별도 모델로 두면 이후 Chunking 전략이 바뀌어도 입력 문서와 검색 출처를 동일하게 유지할 수 있다.
- 디렉터리 로딩 순서를 파일명 기준으로 고정하면 같은 문서 집합에서 이후 ID 생성 순서와 테스트 결과를 재현하기 쉽다.
- 구조 기반 분할은 section 의미를 유지하지만 짧은 Chunk가 생길 수 있고, 고정 크기 분할은 길이가 균일하지만 section 경계를 가로지를 수 있다.
- 문자 시작·끝 위치를 metadata에 저장하면 overlap이 있어도 각 Chunk가 원문의 정확한 어느 범위인지 직접 검증할 수 있다.
- Embedding API는 여러 입력을 한 요청에 보낼 수 있지만 과금은 입력 토큰 기준이므로 batch는 비용보다 호출 횟수와 지연을 줄이는 설정이다.
- API response index를 기준으로 결과를 정렬해야 batch 안의 각 벡터를 원래 Chunk와 안전하게 연결할 수 있다.
- 실제 키가 필요한 테스트를 기본 pytest에서 제외하면 반복 개발 중 의도하지 않은 유료 호출을 막을 수 있다.
- Qdrant는 임의 길이 문자열을 Point ID로 허용하지 않으므로 결정적 chunk ID를 UUID5로 변환하되 payload에는 원래 ID를 유지해야 한다.
- 결정적 ID upsert만으로는 Chunk 수가 줄었을 때 stale Point가 남으므로 문서 단위 교체가 필요하다.
- Qdrant 서버와 Python Client의 minor 버전 차이가 크면 호환성 경고가 발생하므로 같은 1.15 계열로 제한했다.
- Cosine score는 질문과 문서 구성에 따라 달라지므로 threshold를 임의의 고정 정답으로 취급하지 않고 평가 질문으로 조정해야 한다.
- 검색 API에서 answer를 제거하면 낮은 score와 빈 결과를 LLM의 표현에 가리지 않고 직접 관찰할 수 있다.

## Problems

- 테스트는 통과하지만 현재 설치된 Starlette가 기존 `httpx` 기반 `TestClient` 사용에 대한 deprecation warning을 출력한다. 동작에는 영향이 없으며 향후 의존성 조합을 갱신할 때 확인한다.
- 제한된 실행 환경에서는 Windows 소켓 생성이 `WinError 10014`로 실패했지만, 로컬 권한으로 실행한 전체 테스트와 Qdrant 통합 테스트는 통과했다.

## Next task

P1-07 — 재색인과 변경 감지

## Update rule

현재 작업이 끝나면 아래 내용을 갱신한다.

1. 완료한 구현
2. 실행한 테스트와 결과
3. 직접 확인한 데이터 흐름
4. 예상과 달랐던 점
5. 남은 문제
6. 다음 작업
