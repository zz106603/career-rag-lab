# 현재 진행 상태

## Current phase

학습 계획 완료

## Current task

완료 — 진행 중인 작업 없음

## Goal

- Phase 0~3과 종료 산출물이 모두 완료됐다.
- 다음 변경은 별도 목표와 완료 조건을 정의한 뒤 시작한다.

## In scope

- 없음

## Out of scope

- 새로운 작업 전체

## Completion criteria

- `docs/FINAL_REVIEW.md`를 기준으로 Java 이식 전 검토가 가능하다.

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
- P1-06 Prompt와 답변 생성
  - 검색 결과를 질문과 분리된 Context로 구성하고 검색 문서만 사용하도록 제한하는 Prompt를 구현했다.
  - threshold 이상의 상위 검색 근거가 있을 때만 `gpt-5-nano` Responses API로 답변을 생성한다.
  - `answer`, `sources`, threshold 적용 전 `retrieval`, `generated`를 분리한 `POST /answer` API를 추가했다.
  - 근거가 부족하면 OpenAI 답변 생성을 호출하지 않고 고정된 거부 응답을 반환한다.
  - 검색 단계 실패와 생성 단계 실패를 `retrieval_failed`, `generation_failed`로 구분했다.
  - 저비용 모델과 생성 전 근거 판정을 `docs/DECISIONS.md`의 D-009에 기록했다.
- P1-07 재색인과 변경 감지
  - 원문 SHA-256 `document_hash`와 색인 설정을 포함한 `index_fingerprint`를 Qdrant payload에 저장했다.
  - 현재 문서와 Qdrant 상태를 비교해 added, updated, unchanged, deleted를 구분하도록 전체 색인 명령을 증분 방식으로 변경했다.
  - 변경된 문서의 Chunk만 모아 OpenAI Embedding하고, 변경이 없으면 OpenAI 클라이언트 생성과 Qdrant 쓰기를 생략한다.
  - 수정 문서는 기존 Point를 현재 Chunk로 교체하고 디렉터리에서 사라진 문서의 Point를 삭제한다.
  - Embedding과 수정 문서 저장이 끝난 뒤 삭제를 수행해 Embedding 실패 시 기존 문서가 먼저 사라지지 않게 했다.
  - Qdrant payload를 상태 저장소로 사용하는 결정을 `docs/DECISIONS.md`의 D-010에 기록했다.
- P2-01 Text Splitter 교체
  - `langchain-text-splitters` 최소 의존성과 `RecursiveCharacterTextSplitter` 비교 구현을 추가했다.
  - 기존 구조 기반·고정 크기 Chunker를 유지하면서 같은 문서의 Chunk 개수, 평균 길이, 원문 경계와 실제 overlap을 나란히 요약한다.
  - LangChain `start_index`를 기존 `ChunkMetadata`의 원문 범위로 변환하고 source, section, 문서 유형, 프로젝트명을 보존했다.
  - 비교 결과를 직접 확인하는 `python -m app.compare_chunking` 명령을 추가했다.
  - Text Splitter 선택과 실제 overlap 차이를 `docs/DECISIONS.md`의 D-011에 기록했다.
- P2-02 Embedding 추상화 교체
  - `langchain-openai` 최소 의존성과 `OpenAIEmbeddings` 생성 함수를 추가했다.
  - 기존과 같은 `text-embedding-3-small`, 차원, batch 크기, API 키 설정을 LangChain에 전달한다.
  - LangChain `embed_documents()` 반환값의 개수·차원을 검증하고 기존 `EmbeddedChunk`로 변환한다.
  - 수동 OpenAI SDK 호출 구현과 기존 Qdrant 색인 파이프라인은 그대로 유지했다.
  - 추상화 경계와 단계적 교체 결정을 `docs/DECISIONS.md`의 D-012에 기록했다.
- P2-03 Qdrant VectorStore 교체
  - `langchain-qdrant` 최소 의존성과 `QdrantVectorStore` 비교 색인 경로를 추가했다.
  - 기존 `EmbeddedChunk` 벡터를 재사용하는 Adapter로 VectorStore 비교 시 OpenAI 재호출을 방지했다.
  - 동일 벡터와 결정적 UUID Point ID, content, source와 Chunk metadata 보존을 비교했다.
  - LangChain의 중첩 metadata payload에 맞춰 `metadata.document_id`로 stale Chunk를 제거한다.
  - 기존 수동 `QdrantIndexer`와 검색 파이프라인은 그대로 유지했다.
  - 기존 Embedding 재사용 결정을 `docs/DECISIONS.md`의 D-013에 기록했다.
- P2-04 Retriever 교체
  - LangChain `BaseRetriever` 기반 `ObservableQdrantRetriever`와 비교 검색 서비스를 추가했다.
  - 같은 Qdrant Collection과 질문 벡터에서 기존 수동 검색과 content, source, 순서, score가 일치하는지 비교했다.
  - LangChain 중첩 payload도 기존 `QdrantSearcher`가 읽을 수 있도록 호환 변환을 추가했다.
  - top_k와 score threshold를 유지하고 근거가 없으면 빈 결과를 반환한다.
  - 서비스 생성 시 LangChain의 dummy Embedding 검증을 비활성화해 질문 전 불필요한 유료 호출을 방지했다.
  - score 관찰 가능성 결정을 `docs/DECISIONS.md`의 D-014에 기록했다.
- P2-05 PromptTemplate 적용
  - LangChain `PromptTemplate`에 질문과 검색 Context를 명시적 변수로 분리했다.
  - 같은 질문·근거에서 기존 수동 Prompt와 LangChain Prompt가 완전히 같은 문자열인지 비교했다.
  - Context에는 content, source, section만 포함하고 score와 내부 Chunk metadata는 제외했다.
  - 검색 문서 안의 지시 문구가 근거 content 영역에 머무는지 검증했다.
  - Responses API의 안전 지침은 기존 `instructions`에 별도로 유지했다.
  - Prompt 변수 경계를 `docs/DECISIONS.md`의 D-015에 기록했다.
- P2-06 RAG Chain 구성
  - LangChain Retriever, PromptTemplate, ChatOpenAI와 문자열 출력 파서를 LCEL로 연결했다.
  - retrieval 전체를 상태에 보존하고 threshold 통과 evidence만 Prompt Context에 전달한다.
  - evidence가 없으면 `RunnableBranch`가 생성 모델을 호출하지 않고 기존 거부 결과를 반환한다.
  - answer, sources, retrieval, generated와 검색·생성 오류 구분을 기존 수동 서비스와 동일하게 유지했다.
  - `gpt-5-nano`, minimal reasoning, 최대 출력 token과 Responses API 사용 설정을 유지했다.
  - 생성 전 조건 분기 결정을 `docs/DECISIONS.md`의 D-016에 기록했다.
- P2-07 수동·LangChain 파이프라인 평가
  - 기존 15개 평가 질문을 두 파이프라인에 동일한 `top_k=3`, threshold 0.4로 실행했다.
  - 검색 출처 재현율, 답변·거절 정확도, 답변 출처 정확도와 외부 API 호출 수를 질문별·전체로 기록했다.
  - 기존 28개 벡터를 재사용하고 payload만 중첩한 비교 Collection을 만들어 문서 Embedding 비용을 제거했다.
  - 두 파이프라인은 출처 재현율 0.933, 답변·거절 정확도 0.867, 답변 출처 정확도 0.400으로 같았다.
  - 각 경로는 질문 Embedding 15회, 답변 생성 10회를 호출했다.
  - `q14`의 낮은 점수 검색 결과 1·2위 순서만 달랐고 거절 결과에는 영향이 없었다.
  - 비교 결과를 `data/evaluation/pipeline-comparison.json`에 저장했다.
- P2-08 Phase 2 기본 경로 결정
  - LangChain 증분 색인이 중첩 metadata의 Hash 상태를 읽고 문서 추가·수정·삭제를 처리하도록 연결했다.
  - 기본 Collection을 `career_documents_langchain`으로 바꾸고 기존 28개 Point가 변경 없음으로 판정되는 것을 확인했다.
  - API의 기본 검색을 LangChain Retriever로, 기본 답변을 LangChain RAG Chain으로 전환했다.
  - 수동 구현은 삭제하지 않고 이후 회귀 비교에 보존했다.
  - 전환 이유와 유지 범위를 `docs/DECISIONS.md`의 D-018에 기록했다.
- P3-01 기준선 평가
  - 답변 가능 질문의 Hit@3, MRR과 전체 질문의 Answerability·Source accuracy를 분리해 계산했다.
  - 질문별 기대 출처 최초 순위와 관련 없는 검색 출처를 `data/evaluation/baseline.json`에 기록했다.
  - P2에서 실제 실행한 LangChain 결과를 재사용해 추가 OpenAI 호출과 문서 외부 전송 없이 기준선을 생성했다.
  - Hit@3 1.000, MRR 1.000, Answerability accuracy 0.867, Source accuracy 0.400을 확인했다.
  - 검색 지표의 평가 대상을 `docs/DECISIONS.md`의 D-019에 기록했다.
- P3-02 Metadata Filter
  - `document_type`, `project_name`, `source` exact-match 조건을 `SearchFilters`로 정의했다.
  - 입력된 조건을 `metadata.*` Qdrant FieldCondition의 AND filter로 변환해 Vector Search 전에 적용했다.
  - `/search`와 `/answer`, LCEL Chain이 같은 filter를 Retriever까지 전달하도록 연결했다.
  - 실제 Docker Qdrant에서 무조건 검색의 프로젝트·프로필 2개가 `document_type=project` 조건 적용 후 프로젝트 1개로 제한되는 것을 확인했다.
  - filter 적용 시점과 결합 방식을 `docs/DECISIONS.md`의 D-020에 기록했다.
- P3-03 Keyword Search
  - 영문 기술명과 한글을 분리하는 tokenizer와 Chunk 단어 일치 기반 keyword score를 구현했다.
  - `/search/keyword`에서 Dense Search와 분리된 content, source, score, matched terms를 반환한다.
  - 기존 Metadata Filter를 Keyword Search에도 동일하게 적용했다.
  - 정확 키워드 질문 3개를 추가 API 호출 없이 비교해 `data/evaluation/keyword-comparison.json`에 기록했다.
  - Playwright와 Celery 질문은 기대 출처만 1위로 반환했고, RabbitMQ 질문은 기술 요약 문서가 1위·기대 프로젝트 문서가 2위였다.
  - 학습용 lexical 기준선 선택과 한계를 `docs/DECISIONS.md`의 D-021에 기록했다.
  - token SHA-256 index와 term frequency로 Sparse Vector를 만들고 Qdrant IDF modifier를 적용했다.
  - 기존 Dense Point 28개를 재Embedding 없이 `career_documents_hybrid`로 복사하고 `text-sparse` vector를 추가했다.
  - `/search/sparse`에서 Qdrant Sparse Search 결과를 Dense·Keyword 결과와 분리해 반환한다.
  - 세 정확 키워드 질문에서 Sparse와 Keyword 순위가 같음을 확인했다: q04 기대 출처 2위, q05·q06 1위.
  - Sparse Vector 방식을 `docs/DECISIONS.md`의 D-022에 기록했다.
- P3-04 Hybrid Retrieval
  - LangChain Dense Search와 Qdrant Sparse Search에서 각각 후보를 가져와 Chunk ID로 중복 제거했다.
  - 서로 다른 원점수를 직접 더하지 않고 동일 가중치의 RRF(`k=60`)로 순위를 결합했다.
  - `/search/hybrid`가 Dense·Sparse·Hybrid 목록과 각 후보의 원래 순위·score를 분리해 반환한다.
  - 정확 키워드 질문 3개의 기존 실제 검색 순위를 재사용해 `data/evaluation/hybrid-comparison.json`에 비교 결과를 기록했다.
  - q04는 Dense 1위·Sparse 2위·Hybrid 1위였고, q05·q06은 세 방식 모두 기대 출처가 1위였다.
  - RRF 선택과 후보 수 결정을 `docs/DECISIONS.md`의 D-023에 기록했다.
- P3-05 Reranking
  - 기준선과 Hybrid의 최초 기대 출처 순위를 이용해 reranker의 개선 가능 폭을 재현 가능하게 계산했다.
  - 기준선 MRR 1.0, 정확 키워드 Hybrid MRR 1.0, 개선 가능 폭 0.0을 확인했다.
  - 외부 cross-encoder, 로컬 cross-encoder, lexical heuristic의 비용과 한계를 비교했다.
  - 현재는 정답 순위가 이미 상한이고 Chunk 단위 relevance 정답이 없어 reranker 도입을 보류했다.
  - 적용 전 순위, 보류 사유와 재검토 조건을 `data/evaluation/reranking-assessment.json`에 기록했다.
  - 보류 결정을 `docs/DECISIONS.md`의 D-024에 기록했다.
- P3-06 Chunk 전략 비교
  - 작은 LangChain Recursive(200/20), 큰 LangChain Recursive(800/80), Markdown 구조 기반(최대 500) 세 구성을 정의했다.
  - 12개 답변 가능 질문을 동일한 lexical Top 3 조건으로 평가해 Hit@3, MRR, source recall을 전체·질문 유형별로 기록했다.
  - 작은/큰/구조 기반의 전체 결과는 각각 Hit@3 0.917/1.000/1.000, MRR 0.792/0.861/0.819, source recall 0.819/0.875/0.847이었다.
  - Chunk 수는 24/6/28개였고 overlap을 포함한 상대 입력 문자량은 1.042/1.000/1.000이었다.
  - 큰 Chunk가 lexical proxy에서는 가장 높았지만 Dense 의미 표현 희석을 측정하지 못하므로 기본 전략은 확정하지 않았다.
  - 질문별 결과와 비용 지표를 `data/evaluation/chunk-strategy-comparison.json`에 기록했다.
  - 비용 없는 proxy 비교 범위를 `docs/DECISIONS.md`의 D-025에 기록했다.
- P3-07 최종 평가
  - 15개 전체 질문에서 저장된 실제 Dense 기준선과 현재 Qdrant Sparse 검색을 source 단위 RRF로 결합했다.
  - 답변 가능 12개 기준 Dense와 Hybrid 모두 Hit@3 1.000, MRR 1.000, source recall 0.917이었다.
  - 개선 0개·악화 0개·변화 없음 12개였고, 답변 불가 3개는 검색 정답이 없어 순위 변화에서 제외했다.
  - q10의 출처 1개와 q11의 출처 2개가 Top 3에서 누락되는 다중 문서 recall 실패가 남았다.
  - 구조 기반 500자, Dense+Sparse RRF(k=60), candidate 6·최종 3, 명시적 metadata filter, reranker 보류, 생성 전 근거 판정을 최종 추천했다.
  - 질문별 변화·실패·추천 설정을 `data/evaluation/final-search-evaluation.json`에 기록했다.
  - 최종 검색 정책을 `docs/DECISIONS.md`의 D-026에 기록했다.
- FINAL-01 최종 리뷰 문서
  - 직접 구현한 RAG 흐름부터 현재 한계까지 종료 산출물 10개 항목을 `docs/FINAL_REVIEW.md`에 정리했다.
  - LangChain 적용은 품질 자동 개선이 아니라 추상화 교체였음을 수동 구현과 비교했다.
  - `/search/hybrid`는 구현됐지만 `/answer` 기본 경로에는 아직 연결되지 않았다는 미구현 경계를 명시했다.
  - 운영 고려사항, career-fit-ai 이식 계약과 Java 재설계 범위를 기록했다.

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
- `.venv\Scripts\python.exe -m pytest -q tests/test_answers.py tests/test_answer_api.py tests/test_config.py`: 19 passed, 1 warning
- `.venv\Scripts\python.exe -m pytest -q tests/test_answers_live.py --run-live-api`: 1 passed
- `.venv\Scripts\python.exe -m pytest -q`: 73 passed, 5 skipped, 1 warning
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 3 passed, 75 deselected, 1 warning
- 실제 `gpt-5-nano` Responses API에 짧은 합성 근거 하나를 전달해 비어 있지 않은 한국어 답변과 출처 반환을 확인했다.
- 답변 데이터 흐름: 질문 → 검색 결과 전체 보존 → score threshold 이상의 근거 선택 → 근거 없음이면 생성 생략·거부 → 근거 있음이면 질문·Context 분리 Prompt → `gpt-5-nano` → answer·sources와 retrieval 분리 반환
- `.venv\Scripts\python.exe -m pytest -q tests/test_indexing.py tests/test_index_documents.py`: 13 passed
- `.venv\Scripts\python.exe -m pytest -q tests/test_indexing_integration.py --run-integration`: 2 passed
- `.venv\Scripts\python.exe -m pytest -q`: 77 passed, 6 skipped, 1 warning
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 4 passed, 79 deselected, 1 warning
- 실제 Docker Qdrant 임시 Collection에서 문서 2개 최초 추가, 변경 없는 두 번째 실행의 Embedding 0개, 이후 문서 1개 수정·1개 삭제와 Hash payload 보존을 확인했다.
- 증분 색인 데이터 흐름: 현재 Markdown 원문 Hash·색인 fingerprint 계산 → Qdrant 문서 상태 조회 → added·updated·unchanged·deleted 분류 → 변경 Chunk만 Embedding → 문서 단위 교체 → 삭제 문서 Point 정리 → 실행 집계 반환
- `.venv\Scripts\python.exe -m pytest -q tests/test_chunking.py`: 14 passed
- 180자·overlap 20 비교: 수동 구조 기반 5개/평균 119.20자/실제 overlap 없음, 수동 고정 크기 4개/평균 164.00자/매 경계 20자, LangChain 재귀 분할 4개/평균 150.75자/실제 overlap 0·0·7자를 확인했다.
- Text Splitter 비교 데이터 흐름: Markdown `Document` → 수동 2개 전략과 LangChain 재귀 분할 → LangChain `start_index`를 원문 범위로 변환 → 기존 source·section·문서 metadata 결합 → 전략별 개수·평균 길이·경계·실제 overlap 요약
- `.venv\Scripts\python.exe -m pytest -q tests/test_embeddings.py tests/test_indexing.py`: 25 passed
- `.venv\Scripts\python.exe -m pytest -q`: 89 passed, 7 skipped, 1 warning
- LangChain Embedding 데이터 흐름: `Settings`의 API 키·모델·차원·batch 크기 → `OpenAIEmbeddings` → Chunk content 목록을 `embed_documents()`에 전달 → 반환 개수·차원 검증 → 원본 Chunk와 결합한 기존 `EmbeddedChunk` → 기존 Qdrant 색인기
- `.venv\Scripts\python.exe -m pytest -q tests/test_langchain_indexing.py tests/test_indexing.py`: 12 passed
- `.venv\Scripts\python.exe -m pytest -q`: 92 passed, 8 skipped, 1 warning
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 5 passed, 95 deselected, 1 warning
- 실제 Docker Qdrant의 두 임시 Collection에 수동·LangChain 방식으로 동일 Point 2개를 저장해 UUID, 4차원 vector, content와 source가 일치하고 payload metadata 구조만 다른 것을 확인했다.
- LangChain VectorStore 데이터 흐름: 기존 `EmbeddedChunk` → 입력·차원 검증 → 기존 Qdrant Collection 설정 검증 → `PrecomputedEmbeddings`로 같은 벡터 재사용 → 결정적 UUID·content·중첩 metadata 구성 → `metadata.document_id` 기존 Point 삭제 → `QdrantVectorStore.add_texts()`
- LangChain Retriever 데이터 흐름: 질문 → LangChain Embeddings의 `embed_query()` → Qdrant 유사도 검색 → `(Document, score)` → score를 보존한 Retriever `Document` → content·source·score·metadata가 분리된 기존 `SearchResult`
- `.venv\Scripts\python.exe -m pytest -q tests/test_langchain_retrieval.py tests/test_search.py`: 13 passed
- `.venv\Scripts\python.exe -m pytest -q`: 99 passed, 9 skipped, 1 warning
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 6 passed, 102 deselected, 1 warning
- 실제 Docker Qdrant 임시 Collection에서 같은 질문 벡터로 수동 검색과 LangChain Retriever를 실행해 상위 2개 content, source, 순서와 Cosine score가 일치하는 것을 확인했다.
- `.venv\Scripts\python.exe -m pytest -q tests/test_langchain_prompts.py tests/test_answers.py tests/test_answer_api.py`: 14 passed, 1 warning
- `.venv\Scripts\python.exe -m pytest -q`: 103 passed, 9 skipped, 1 warning
- PromptTemplate 데이터 흐름: 질문과 threshold 통과 `SearchResult` → content·source·section만 Context 문자열로 직렬화 → `query`·`context` Template 변수 치환 → 기존 수동 Prompt와 동일한 Responses API input 문자열
- `.venv\Scripts\python.exe -m pytest -q tests/test_langchain_rag.py tests/test_langchain_prompts.py tests/test_answers.py`: 17 passed
- `.venv\Scripts\python.exe -m pytest -q`: 109 passed, 10 skipped, 1 warning
- LangChain RAG Chain 데이터 흐름: 질문·top_k·threshold → Retriever 검색 전체 보존 → threshold evidence 선택 → 근거 없음이면 생성 생략·거부 → 근거 있음이면 PromptTemplate → Responses API 기반 `ChatOpenAI` → 문자열 파서 → 기존 `AnswerResult`
- `.venv\Scripts\python.exe -m pytest -q tests/test_evaluation.py`: 5 passed
- `.venv\Scripts\python.exe -m app.evaluate_pipelines`: 수동·LangChain 각 15개 질문의 실제 OpenAI/Qdrant 비교 완료
- 평가 데이터 흐름: 수동 Collection의 기존 벡터 28개 → LangChain payload 비교 Collection → 동일 질문 15개를 각 파이프라인에서 Embedding·검색·근거 판정·생성 → 질문별 지표 → JSON 비교 보고서
- `.venv\Scripts\python.exe -m pytest -q tests/test_langchain_indexing.py tests/test_index_documents.py tests/test_pipeline.py tests/test_config.py tests/test_search_api.py tests/test_answer_api.py`: 24 passed, 1 warning
- `.venv\Scripts\python.exe -m app.index_documents`: documents=6, chunks=28, unchanged=6, embedded_chunks=0
- `.venv\Scripts\python.exe -m pytest -q -m integration --run-integration`: 6 passed, 121 deselected, 1 warning
- 전체 테스트는 코드 검증 115개가 통과했고 Windows `WinError 10014`로 FastAPI 테스트 2개가 일시 실패했으며, 해당 API 테스트만 재실행해 3 passed를 확인했다.
- 기본 API 데이터 흐름: Markdown 변경 → LangChain payload 증분 색인 → `/search`의 LangChain Retriever → `/answer`의 LCEL 근거 분기·생성
- `.venv\Scripts\python.exe -m app.evaluate_baseline`: Hit@3=1.000, MRR=1.000, Answerability=0.867, Source=0.400
- `.venv\Scripts\python.exe -m pytest -q tests/test_evaluation.py`: 7 passed
- `.venv\Scripts\python.exe -m pytest -q`: 119 passed, 10 skipped, 1 warning
- 기준선 데이터 흐름: P2 실제 LangChain 평가 결과 → 질문별 기대 출처와 검색 순위 비교 → Hit@3·MRR → 생성·거절 및 답변 출처 비교 → JSON 기준선
- `.venv\Scripts\python.exe -m pytest -q tests/test_langchain_retrieval_integration.py --run-integration`: 2 passed
- `.venv\Scripts\python.exe -m pytest -q tests/test_langchain_retrieval.py tests/test_langchain_rag.py`: 15 passed
- 전체 테스트는 121 passed, 11 skipped였고 Windows `WinError 10014`로 API 테스트 1개가 일시 실패했으며, 해당 테스트를 재실행해 1 passed를 확인했다.
- Metadata Filter 데이터 흐름: API filter 입력 → `SearchFilters` → `metadata.*` exact-match AND 조건 → Qdrant 후보 제한 → 제한된 범위의 Cosine Top K → retrieval·답변
- `.venv\Scripts\python.exe -m pytest -q tests/test_keyword_search.py tests/test_keyword_search_api.py tests/test_langchain_retrieval.py`: 12 passed, 1 warning
- `.venv\Scripts\python.exe -m pytest -q`: 126 passed, 11 skipped, 1 warning
- `.venv\Scripts\python.exe -m app.compare_keyword_search`: q04 기대 출처 2위, q05·q06 기대 출처 1위, 외부 API 호출 0회
- `.venv\Scripts\python.exe -m app.migrate_hybrid_collection`: 기존 Dense Point 28개에 Sparse Vector 추가, Embedding 호출 0회
- `.venv\Scripts\python.exe -m app.index_documents`: hybrid Collection의 문서 6개·Chunk 28개가 unchanged, Embedding 0개
- `.venv\Scripts\python.exe -m pytest -q`: 129 passed, 11 skipped, 1 warning
- Keyword Search 데이터 흐름: 질문 tokenize → Qdrant Chunk payload 조회 → metadata filter → Chunk tokenize·일치 단어 score → keyword 순위 → Dense 결과와 별도 비교
- Sparse Search 데이터 흐름: 문서·질문 tokenize → 결정적 token hash·term frequency Sparse Vector → Qdrant IDF score → `text-sparse` Top K → Dense·Keyword와 별도 비교
- `.venv\Scripts\python.exe -m app.evaluate_hybrid_search`: q04 Dense/Sparse/Hybrid 최초 기대 출처 순위 1/2/1, q05·q06 1/1/1, 외부 API 호출 0회
- `.venv\Scripts\python.exe -m pytest`: 133 passed, 11 skipped, 1 warning
- Hybrid Search 데이터 흐름: 같은 질문·filter → Dense와 Sparse 후보 각각 조회 → Chunk ID 중복 제거 → 검색별 순위를 RRF 점수로 변환·합산 → 결정적 정렬 → Dense·Sparse·Hybrid 목록을 함께 반환
- `.venv\Scripts\python.exe -m app.assess_reranking`: decision=defer, 기준선 MRR 1.000, Hybrid 정확 키워드 MRR 1.000, 개선 가능 폭 0.000, 외부 API 호출 0회
- `.venv\Scripts\python.exe -m pytest tests/test_assess_reranking.py`: 3 passed
- `.venv\Scripts\python.exe -m pytest`: 136 passed, 11 skipped, 1 warning
- Reranking 판단 데이터 흐름: 저장된 기준선 MRR·Hybrid 질문별 최초 기대 출처 순위 → Hybrid MRR·상한까지의 개선 폭 계산 → 후보 비용과 함께 도입·보류 결정 JSON 생성
- `.venv\Scripts\python.exe -m app.evaluate_chunk_strategies`: 작은/큰/구조 기반 Hit@3 0.917/1.000/1.000, MRR 0.792/0.861/0.819, 외부 API 호출 0회
- `.venv\Scripts\python.exe -m pytest tests/test_evaluate_chunk_strategies.py`: 3 passed
- `.venv\Scripts\python.exe -m pytest`: 139 passed, 11 skipped, 1 warning
- Chunk 비교 데이터 흐름: 학습 문서 6개 → 전략별 분할 → 같은 tokenizer·lexical score → 질문별 Top 3 Chunk·출처 중복 제거 → 전체·category 지표와 Chunk 수·입력 문자량 JSON 기록
- `.venv\Scripts\python.exe -m pytest tests/test_evaluate_final_search.py`: 2 passed
- `.venv\Scripts\python.exe -m app.evaluate_final_search`: Dense/Hybrid Hit@3 1.000/1.000, MRR 1.000/1.000, source recall 0.917/0.917, 외부 API 호출 0회
- `.venv\Scripts\python.exe -m pytest`: 141 passed, 11 skipped, 1 warning
- 최종 평가 데이터 흐름: 저장된 실제 Dense source 순위 + 로컬 Qdrant Sparse source 순위 → source RRF → 답변 가능 질문의 순위·recall 비교 → 질문별 변화·실패와 추천 설정 JSON 기록
- `.venv\Scripts\python.exe -m pytest tests/test_final_review.py`: 최종 리뷰 10개 항목, 평가 수치와 미구현 경계 검증
- `.venv\Scripts\python.exe -m pytest`: 143 passed, 11 skipped, 1 warning

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
- threshold 적용 전 retrieval을 응답에 남겨야 답변 거부가 검색 결과 없음 때문인지 낮은 score 때문인지 확인할 수 있다.
- 근거 부족을 LLM Prompt에만 맡기지 않고 생성 호출 전에 판정하면 hallucination 가능성과 API 비용을 함께 줄일 수 있다.
- 검색과 생성 예외를 다른 타입과 API 오류 코드로 바꾸면 어느 외부 단계가 실패했는지 구분할 수 있다.
- 원문 Hash만 비교하면 Chunk 크기나 Embedding 모델 변경을 놓치므로 색인 설정을 포함한 fingerprint가 함께 필요하다.
- Qdrant payload에 문서 상태를 저장하면 별도 데이터베이스 없이 삭제 문서를 찾을 수 있지만 모든 Chunk에 같은 상태 값이 중복된다.
- 삭제를 변경 문서 Embedding 뒤로 미루면 외부 API 실패 시 기존 검색 가능 상태를 보존할 수 있다.
- LangChain의 `chunk_overlap`은 목표 최대 overlap이며 자연스러운 separator 경계가 멀리 떨어져 있으면 모든 인접 Chunk가 설정값만큼 겹치지는 않는다.
- `start_index`를 사용하면 LangChain 결과도 원문 범위로 검증할 수 있지만 section 같은 프로젝트 metadata는 기존 규칙으로 명시적으로 보완해야 한다.
- LangChain `OpenAIEmbeddings`는 batch 분할과 OpenAI SDK 호출을 내부로 감추지만, 결과 개수·차원과 원본 Chunk 연결은 애플리케이션 경계에서 계속 검증해야 한다.
- LangChain 결과를 기존 도메인 모델로 변환하면 다음 추상화를 교체하기 전까지 downstream 코드를 바꾸지 않아도 된다.
- LangChain QdrantVectorStore는 기본적으로 원문과 metadata를 각각 payload key 아래 저장하므로 수동 평면 payload와 필터 경로가 달라진다.
- VectorStore만 비교할 때 기존 벡터를 Adapter로 재사용하면 비용뿐 아니라 서로 다른 API 응답이 비교 결과에 섞이는 것도 막을 수 있다.
- LangChain의 기본 Retriever 반환값은 문서 중심이므로 검색 품질을 수치로 관찰하려면 VectorStore의 score 결과를 명시적으로 전달해야 한다.
- QdrantVectorStore의 Collection 검증은 dummy text Embedding을 실행하므로 검색 서비스 생성 시 API 호출을 피하려면 색인 단계 검증과 역할을 분리해야 한다.
- PromptTemplate은 문자열 조합을 구조화하지만 어떤 검색 metadata를 Context에 포함할지는 애플리케이션이 계속 명시적으로 결정해야 한다.
- 검색 문서 content와 모델 지침을 다른 API 입력 영역으로 유지하면 문서 안의 문장을 상위 지침으로 취급하지 않는 경계를 보존할 수 있다.
- LCEL Chain도 조건 분기를 명시하지 않으면 검색 결과가 비어 있어도 생성 모델을 호출할 수 있으므로 비용·거부 정책은 애플리케이션 상태 전환으로 유지해야 한다.
- 수동 서비스와 LangChain Chain이 같은 `AnswerResult`를 반환하게 하면 API를 바꾸지 않고 내부 파이프라인만 평가할 수 있다.
- 동일 벡터와 평가 조건에서 두 경로의 결과가 같았으므로 현재 품질 차이는 프레임워크보다 `top_k`와 threshold 설정의 영향을 더 크게 받는다.
- 단일 기대 출처 질문도 threshold를 통과한 관련 없는 Chunk가 함께 답변 근거가 되면 출처 정확도가 낮아지므로 검색 적중과 답변 출처 정확도를 별도 지표로 봐야 한다.
- LangChain을 기본 경로로 전환하려면 Chain만 바꾸는 것이 아니라 증분 색인의 상태 조회·삭제 filter도 중첩 metadata 경로에 맞춰야 한다.
- Hit@K는 기대 출처 중 하나만 찾아도 성공하므로 다중 문서 질문의 전체 출처 누락을 드러내지 못하며 source recall을 함께 봐야 한다.
- MRR 1.0은 정답 문서가 항상 첫 번째라는 뜻이지만 뒤 순위에 관련 없는 문서가 섞이지 않았다는 뜻은 아니다.
- Metadata Filter는 의미 유사도를 개선하는 알고리즘이 아니라 검색 가능한 문서 범위를 먼저 줄이는 장치이므로, 올바른 조건을 알고 있는 질문에서만 사용해야 한다.
- Keyword Search는 Playwright·Celery처럼 고유한 기술명을 정확히 찾지만 RabbitMQ처럼 여러 문서에 같은 단어가 있으면 일반 단어 일치와 반복 횟수 때문에 기대 프로젝트보다 기술 요약 문서가 앞설 수 있다.
- Dense와 Keyword의 score는 의미와 범위가 다르므로 숫자를 직접 더하지 말고 다음 단계에서 순위 기반 결합을 검토해야 한다.
- 현재 Sparse Search는 Keyword와 같은 token 정보를 사용하므로 세 정확 키워드 질문의 순위가 같았고, Qdrant로 후보 생성과 IDF 계산 위치가 이동한 것이 핵심 차이다.
- Dense Cosine score와 Sparse IDF score는 직접 비교할 수 없지만 RRF는 각 검색의 순위만 사용하므로 별도 score 정규화 없이 결합할 수 있다.
- q04처럼 Sparse에서 기술 요약 문서가 앞서도 기대 프로젝트가 Dense와 Sparse 양쪽에 나타나면 두 순위의 기여가 합쳐져 Hybrid 1위가 될 수 있다.
- reranker는 초기 검색 후보를 새로 찾는 검색기가 아니라 이미 찾은 후보의 관련성을 다시 판단해 순서만 바꾸므로, 정답이 후보에 없으면 복구할 수 없다.
- MRR이 이미 1.0이면 최초 정답 순위를 개선할 수 없으며, 뒤 순위 precision을 평가하려면 문서명이 아닌 Chunk 단위 relevance 정답이 필요하다.
- 작은 Chunk는 답이 여러 경계로 흩어질 수 있고 같은 문서의 여러 Chunk가 Top K를 차지해 다중 문서 source recall이 낮아질 수 있다.
- 큰 Chunk는 이번 lexical proxy에서 문서 문맥을 함께 보존해 가장 높은 지표를 냈지만, 실제 Dense Embedding에서는 여러 주제가 한 벡터에 섞이는 희석 효과를 별도로 검증해야 한다.
- 구조 기반 Chunk는 제목 경계를 보존하고 overlap 중복 입력이 없다는 장점이 있지만 짧은 section이 많아 Chunk 수가 가장 많았다.
- Hybrid는 정확 키워드 후보를 보완하는 구조적 안전망이지만, 현재 평가 집합에서는 Dense가 이미 기대 출처 1위여서 전체 MRR·recall 수치를 높이지 않았다.
- 전체 baseline JSON의 기존 mean source recall 0.933은 답변 불가 질문의 recall 1.0도 포함한다. 검색 정답이 정의된 답변 가능 12개만 공정하게 비교하면 Dense와 Hybrid 모두 0.917이다.
- 다중 문서 질문은 하나의 정답만 찾는 Hit@3·MRR이 1.0이어도 기대 출처 전체를 놓칠 수 있으므로 source recall을 반드시 함께 봐야 한다.

## Problems

- 테스트는 통과하지만 현재 설치된 Starlette가 기존 `httpx` 기반 `TestClient` 사용에 대한 deprecation warning을 출력한다. 동작에는 영향이 없으며 향후 의존성 조합을 갱신할 때 확인한다.
- 제한된 실행 환경에서는 Windows 소켓 생성이 `WinError 10014`로 실패했지만, 로컬 권한으로 실행한 전체 테스트와 Qdrant 통합 테스트는 통과했다.
- 실제 영속 Collection의 검색 원문을 OpenAI 답변 생성으로 보내는 end-to-end 실행은 외부 데이터 전송 보안 검토에서 차단됐다. 합성 근거의 실제 OpenAI 호출과 실제 Qdrant 검색은 각각 독립적으로 검증했다.
- 기존 영속 Collection의 학습 문서를 Hash payload 형식으로 갱신하는 실제 OpenAI 호출은 데이터 외부 전송 보안 검토에서 차단됐다. 임시 합성 문서와 실제 Qdrant를 사용한 증분 시나리오는 검증했다.
- P3 기준선의 실제 API 재실행은 검색 문서 외부 전송 승인이 없어 중단했고, 이미 저장된 P2 실제 실행 결과를 비용 없이 재계산했다.
- P3-04의 실제 질문 Embedding 재실행도 외부 전송 승인이 없어 중단했다. P3-03에 저장된 실제 Dense·Sparse source 순위를 재사용해 문서 단위 RRF를 평가했고, Chunk 단위 결합은 단위 테스트로 검증했다.
- P3-07은 질문 Embedding과 답변 생성을 재호출하지 않아 생성 품질 지표를 다시 계산하지 않았다. 저장된 Dense 실제 결과와 로컬 Sparse 검색으로 검색 변화만 평가했다.

## Next task

없음 — 학습 계획 완료

## Update rule

현재 작업이 끝나면 아래 내용을 갱신한다.

1. 완료한 구현
2. 실행한 테스트와 결과
3. 직접 확인한 데이터 흐름
4. 예상과 달랐던 점
5. 남은 문제
6. 다음 작업
