# career-rag-lab

전체 구현 흐름, 최종 설정, 평가 결과와 Java 이식 범위는
[`docs/FINAL_REVIEW.md`](docs/FINAL_REVIEW.md)에 정리되어 있다.

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

Embedding 구현은 학습 비교를 위해 두 경로를 함께 유지한다. `embed_chunks()`는
OpenAI SDK를 직접 호출하며, `embed_chunks_with_langchain()`은 LangChain의
`OpenAIEmbeddings.embed_documents()`를 사용한다. 두 경로 모두 기존 Qdrant
색인기가 받는 `EmbeddedChunk`를 반환하므로 저장 단계는 바뀌지 않는다.

Qdrant 색인도 비교를 위해 수동 `QdrantIndexer`와 LangChain
`QdrantVectorStore` 경로를 함께 유지한다. LangChain 경로는 이미 만들어진
Embedding을 재사용하므로 VectorStore 비교 중 OpenAI API를 다시 호출하지 않는다.
수동 payload는 metadata가 최상위에 있고, LangChain payload는 `metadata` 객체
아래에 중첩된다는 차이가 있다.

검색 비교에서도 기존 `QdrantSearcher`와 LangChain Retriever를 함께 유지한다.
일반 Retriever 반환값에는 유사도 score가 포함되지 않으므로 이 프로젝트의
Retriever는 Qdrant의 `(Document, score)` 결과를 받아 score를 명시적으로
`SearchResult`에 복원한다. 따라서 검색 근거는 답변 생성과 계속 분리된다.

답변 Prompt도 기존 `build_answer_prompt()`와 LangChain
`build_langchain_answer_prompt()`를 함께 유지한다. LangChain Template에는
`query`와 `context` 두 변수만 전달하고, Context에는 검색된 content, source,
section만 포함한다. 생성 안전 지침은 기존 Responses API의 `instructions`에
별도로 유지한다.

`LangChainRagService`는 Retriever → 근거 threshold 판정 → PromptTemplate →
`ChatOpenAI` → 문자열 파서를 LCEL로 연결한다. 조건 분기에서 근거가 없으면
모델 Chain으로 진입하지 않고 기존 거부 응답을 반환하며, 근거가 있으면 기존과
동일한 `answer`, `sources`, `retrieval`, `generated` 구조를 만든다.

## Chunking 전략 비교

기존 수동 구조 기반·고정 크기 Chunker와 LangChain의
`RecursiveCharacterTextSplitter`를 같은 Markdown 문서에서 비교한다.

```powershell
python -m app.compare_chunking data/documents/finance-transfer-system.md `
    --chunk-size 180 --overlap 20
```

출력의 `boundaries`는 각 Chunk의 원문 시작·끝 위치이며 `overlaps`는 인접
Chunk 사이에서 실제로 겹친 문자 수다. LangChain의 overlap 설정은 자연스러운
separator 경계를 우선하기 때문에 모든 경계에서 요청한 길이가 보장되지는 않는다.

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

학습 문서 전체를 실제 OpenAI Embedding과 Sparse Vector로 변환해 `career_documents_hybrid`에 저장한다. 이 명령은 변경된 문서가 있을 때만 유료 OpenAI API를 호출한다.

```powershell
python -m app.index_documents
```

완료 후 `http://localhost:6333/dashboard`의 Collections 화면에서 `career_documents_hybrid`를 선택하면 Dense·`text-sparse` Vector와 payload를 볼 수 있다. 각 Point의 `metadata`에는 원문의 `document_hash`와 색인 설정을 포함한 `index_fingerprint`가 저장된다.

같은 명령을 다시 실행하면 변경되지 않은 문서는 Chunking 결과 비교까지만 수행하고 OpenAI Embedding과 Qdrant 쓰기를 생략한다. 실행 결과에서 변경 상태를 확인할 수 있다.

```text
collection=career_documents_hybrid documents=6 chunks=28 added=0 updated=0 unchanged=6 deleted=0 embedded_chunks=0
```

- `added`: 새로 발견되어 색인한 문서 수
- `updated`: 내용 또는 색인 설정이 바뀌어 다시 색인한 문서 수
- `unchanged`: Hash가 같아 Embedding을 생략한 문서 수
- `deleted`: 디렉터리에서 사라져 Qdrant Point를 삭제한 문서 수
- `embedded_chunks`: 이번 실행에서 실제 Embedding한 Chunk 수

기존 Point에 Hash가 없는 상태에서 처음 실행하면 모든 문서가 `updated`로 분류되어 한 번 갱신된다. 이후부터 변경된 문서만 OpenAI API를 호출한다.

REST API로 원문과 metadata를 확인하려면 다음 명령을 사용한다.

```powershell
$body = @{ limit = 10; with_payload = $true; with_vector = $false } | ConvertTo-Json
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:6333/collections/career_documents_hybrid/points/scroll" `
    -ContentType "application/json" `
    -Body $body
```

색인이 끝난 문서에서 LLM 답변 생성 없이 관련 Chunk만 검색할 수 있다. 질문
Embedding을 생성하므로 이 요청은 OpenAI API 비용이 소량 발생한다.

`filters`를 지정하면 Qdrant가 Vector Search 전에 문서 범위를 제한한다. 지원 조건은
`document_type`, `project_name`, `source`이며 여러 조건은 AND로 결합한다.

```powershell
$body = @{
    query = "장애 대응 자동화 경험이 있나요?"
    filters = @{
        document_type = "project"
        project_name = "장애 대응 자동화 도구"
    }
    top_k = 5
    score_threshold = 0.3
} | ConvertTo-Json
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/search" `
    -ContentType "application/json" `
    -Body $body
```

응답의 `results`에는 `content`, `source`, `score`, `metadata`만 포함된다.
`top_k`는 최대 결과 개수이며 `score_threshold`를 높이면 유사도가 낮은 근거는
제외된다. 검색 근거가 부족하면 `results`가 빈 배열이 될 수 있다.

Embedding 없이 실제 단어가 포함된 Chunk만 보려면 Keyword Search를 호출한다.
Keyword score는 Dense Cosine score와 다른 값이므로 직접 비교하거나 더하지 않는다.

```powershell
$body = @{
    query = "Playwright를 어디에 사용했나요?"
    top_k = 3
} | ConvertTo-Json
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/search/keyword" `
    -ContentType "application/json" `
    -Body $body
```

Qdrant에 저장된 Sparse Vector로 검색하려면 `/search/sparse`를 사용한다. 요청 형식은
Keyword Search와 같으며 Qdrant가 sparse score와 Top K를 계산한다.

Dense 의미 검색과 Sparse 단어 검색을 결합한 결과는 `/search/hybrid`에서 확인한다.
두 score의 단위가 다르므로 직접 더하지 않고 RRF(Reciprocal Rank Fusion)로 순위를
합친다. `dense`, `sparse`, `hybrid`가 각각 반환되어 결합 전후를 따로 볼 수 있다.

```powershell
$body = @{
    query = "RabbitMQ를 사용한 프로젝트와 처리 방식을 알려주세요."
    top_k = 3
    candidate_k = 6
} | ConvertTo-Json
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/search/hybrid" `
    -ContentType "application/json" `
    -Body $body
```

`candidate_k`는 각 검색 방식에서 결합 전에 가져올 후보 수이며 `top_k` 이상이어야
한다. 생략하면 `max(top_k * 2, 5)`를 사용한다. Hybrid 결과의 metadata에는 원래
`dense_rank`, `sparse_rank`, `dense_score`, `sparse_score`가 남는다.

현재 데이터에서 reranker 도입 필요성을 다시 계산하려면 다음 명령을 실행한다.

```powershell
python -m app.assess_reranking
```

결과는 `data/evaluation/reranking-assessment.json`에 저장된다. 현재는 기대 출처가
이미 모두 1위라 외부 호출과 새 모델 의존성을 추가하지 않고 도입을 보류했다.

작은 Chunk(200/20), 큰 Chunk(800/80), Markdown 구조 기반 Chunk(최대 500)의
경계 영향을 비용 없이 비교하려면 다음 명령을 실행한다.

```powershell
python -m app.evaluate_chunk_strategies
```

이 비교는 재Embedding하지 않고 동일한 lexical 검색을 사용하는 proxy 평가다.
따라서 Chunk 개수·중복 입력량과 경계 차이를 비교할 수 있지만 Dense 검색의 최종
기본 전략을 확정하는 결과로 사용하지 않는다.

저장된 실제 Dense 기준선과 현재 Qdrant Sparse Search를 결합해 전체 질문의 최종
검색 평가를 재현하려면 Qdrant 실행 후 다음 명령을 사용한다.

```powershell
python -m app.evaluate_final_search
```

질문 Embedding과 답변 생성은 다시 호출하지 않는다. 결과에는 기준선·Hybrid 지표,
질문별 변화, 남은 실패와 최종 추천 설정이 함께 기록된다.

검색 결과를 근거로 자연어 답변을 생성하려면 `/answer`를 호출한다. 기본 생성
모델은 비용을 최소화한 `gpt-5-nano`이며, 기준 score 이상의 상위 3개 Chunk만
Context로 전달한다.

```powershell
$body = @{
    query = "장애 대응 자동화 경험이 있나요?"
} | ConvertTo-Json
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/answer" `
    -ContentType "application/json" `
    -Body $body
```

응답은 생성된 `answer`, 실제 Context 출처인 `sources`, threshold 적용 전 검색
결과인 `retrieval`, 생성 여부인 `generated`를 분리해 반환한다. 근거가 기준보다
낮으면 OpenAI 답변 생성 API를 호출하지 않고 `insufficient_evidence` 상태와
고정된 거부 문구를 반환한다.

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
