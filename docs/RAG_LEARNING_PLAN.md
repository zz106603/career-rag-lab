# RAG 학습 실행 계획

## 1. 프로젝트 목적

이 저장소는 기존 취업 문서를 이용해 RAG의 전체 흐름을 직접 구현하고,
프레임워크 적용 전후와 검색 전략별 품질 차이를 확인하기 위한 학습 프로젝트다.

최종 목적은 단순한 문서 챗봇 완성이 아니다.

- 문서가 어떻게 Chunk로 변환되는지 이해한다.
- Embedding과 Vector Search의 입력·출력을 직접 확인한다.
- 검색 결과와 LLM 생성 결과를 분리해 관찰한다.
- 검색 품질을 수치와 테스트 질문으로 비교한다.
- LangChain이 무엇을 대신 처리하는지 직접 구현과 비교한다.
- 이후 career-fit-ai의 Java/Spring 구조로 옮길 기준을 확보한다.

Java 이식은 이 저장소의 현재 범위에 포함하지 않는다.

---

## 2. 고정 기술 스택

- Python 3.12
- FastAPI
- Qdrant
- Qdrant Python Client
- OpenAI API
- Docker Compose
- pytest
- LangChain: Phase 2부터 사용

선택 기능을 이유 없이 추가하지 않는다.

- 프론트엔드
- 사용자 인증
- 클라우드 배포
- 메시지 큐
- 별도 관계형 데이터베이스
- Agent 또는 LangGraph
- 다중 사용자 기능

---

## 3. 전체 학습 순서

```text
Phase 0  환경과 평가 기준 준비
Phase 1  LangChain 없이 RAG 직접 구현
Phase 2  직접 구현을 LangChain으로 단계별 교체
Phase 3  검색 품질 개선과 평가
종료     Java 이식 기준 정리
```

각 Phase는 이전 Phase의 완료 조건을 충족한 뒤 진행한다.

---

# Phase 0. 환경과 평가 기준 준비

## 목표

코드를 작성하기 전에 실행 환경, 테스트 문서, 평가 질문을 고정한다.

## 작업

### P0-01. 프로젝트 초기화

- Python 프로젝트 생성
- FastAPI 기본 애플리케이션 구성
- pytest 설정
- 환경변수 로딩
- `.env.example` 작성
- `.gitignore` 작성
- `GET /health` 구현

### P0-02. Qdrant 실행 환경

- Docker Compose로 Qdrant 실행
- 로컬 저장 볼륨 구성
- 애플리케이션 연결 설정
- Qdrant 상태 확인 테스트 작성

### P0-03. 학습용 문서 준비

실제 개인정보가 없는 Markdown 문서 5~10개를 준비한다.

권장 내용:

- 정밀 의료 프로젝트
- 재무자료 전송 프로젝트
- 소셜 대시보드 프로젝트
- 개인 프로젝트 README
- 보유 기술 설명
- 일부러 경험이 없는 기술을 명시한 문서

실제 이력서 원본이나 개인정보 문서는 Git에 올리지 않는다.

### P0-04. 평가 질문 세트

`data/evaluation/questions.json`에 최소 15개 질문을 작성한다.

질문 유형:

1. 의미 검색이 필요한 질문
2. 기술명이 정확히 포함된 질문
3. 기간이나 프로젝트 조건이 포함된 질문
4. 여러 문서가 함께 검색돼야 하는 질문
5. 문서에 근거가 없어 답변을 거부해야 하는 질문

예시:

```json
{
  "id": "q01",
  "question": "비동기 메시지 처리 경험을 알려줘.",
  "expected_sources": ["finance-transfer.md"],
  "answerable": true
}
```

## 완료 조건

- FastAPI와 Qdrant가 로컬에서 실행된다.
- 테스트가 통과한다.
- 샘플 문서가 준비돼 있다.
- 평가 질문과 기대 출처가 기록돼 있다.
- 실제 개인정보나 API 키가 Git 추적 대상에 없다.

---

# Phase 1. LangChain 없이 RAG 직접 구현

## 목표

프레임워크가 내부 동작을 숨기지 않도록 RAG 파이프라인을 직접 연결한다.

```text
문서 로딩
→ 정규화
→ Chunk 생성
→ Embedding 생성
→ Qdrant 저장
→ 질문 Embedding
→ Vector Search
→ Prompt 구성
→ LLM 답변
```

Phase 1이 끝날 때까지 LangChain을 설치하거나 사용하지 않는다.

---

## P1-01. 문서 모델과 로더

### 구현

- Markdown 파일 로딩
- 원문과 metadata를 가진 문서 모델 정의
- 파일명, 문서 유형, 프로젝트명 등의 metadata 유지
- 지원하지 않는 파일과 빈 문서 처리

### 확인할 내용

- 원문과 metadata의 책임이 어떻게 구분되는가
- 파일 경로가 검색 결과의 출처로 어떻게 이어지는가
- 로딩 실패가 전체 색인을 중단해야 하는가

### 완료 조건

- 여러 Markdown 파일을 일관된 문서 모델로 읽는다.
- 빈 파일과 잘못된 경로 테스트가 있다.
- source metadata가 보존된다.

---

## P1-02. Chunking

### 1차 전략

Markdown 제목과 문단 경계를 우선 사용한다.

각 Chunk에는 다음을 저장한다.

- `chunk_id`
- `document_id`
- `content`
- `source`
- `section`
- `chunk_index`
- `document_type`
- 필요한 도메인 metadata

### 실험

최소 두 전략을 비교한다.

1. 구조 기반 분할
2. 고정 글자 또는 토큰 크기 분할

Chunk overlap은 기본값을 작게 시작하고 실제 중복 효과를 확인한다.

### 완료 조건

- 같은 입력에서 동일한 Chunk ID가 생성된다.
- Chunk가 지나치게 짧거나 긴 경우를 확인할 수 있다.
- 각 Chunk가 원문 위치와 출처를 추적할 수 있다.
- 전략별 결과를 테스트 또는 스크립트로 비교할 수 있다.

---

## P1-03. Embedding 생성

### 구현

- OpenAI Embedding API 직접 호출
- 입력 목록의 batch 처리
- 모델과 차원 설정 관리
- API 오류와 빈 입력 처리
- 호출 결과의 개수와 차원 검증

### 확인할 내용

- Embedding은 어떤 입력 단위로 생성되는가
- 모델을 바꾸면 기존 Collection을 그대로 쓸 수 있는가
- 동일한 문장의 벡터가 항상 완전히 동일한가
- 비용과 요청 크기는 어떻게 관리하는가

### 완료 조건

- 하나와 여러 Chunk의 Embedding을 생성한다.
- 벡터 차원을 검증한다.
- API 호출부가 단위 테스트 가능한 구조다.
- API 키가 코드나 로그에 노출되지 않는다.

---

## P1-04. Qdrant 색인

### 구현

- Collection 생성
- Point ID와 payload 설계
- Chunk embedding 및 metadata 저장
- 같은 문서 재색인 시 중복 방지
- 문서 단위 삭제 후 재색인

### 권장 payload

```json
{
  "document_id": "doc-001",
  "chunk_id": "doc-001:003",
  "source": "finance-transfer.md",
  "section": "성과",
  "document_type": "career",
  "content": "..."
}
```

### 완료 조건

- Qdrant에서 저장된 Point와 payload를 확인할 수 있다.
- 동일 문서를 다시 색인해도 중복이 늘지 않는다.
- 문서 단위 삭제와 재색인이 가능하다.
- Collection 설정과 Embedding 차원이 일치한다.

---

## P1-05. Vector Search

### 구현

- 질문 Embedding 생성
- Qdrant 유사도 검색
- `top_k`와 score threshold 설정
- 검색 결과에 content, source, score, metadata 반환
- 검색 API 제공

예시:

```http
POST /search
```

```json
{
  "query": "비동기 처리 경험",
  "top_k": 5
}
```

### 완료 조건

- LLM 호출 없이 검색 결과만 확인할 수 있다.
- score 순서와 출처를 확인할 수 있다.
- `top_k`와 threshold 변경 결과를 비교할 수 있다.
- 근거 없는 질문에서 낮은 점수 또는 빈 결과가 확인된다.

---

## P1-06. Prompt와 답변 생성

### 구현

- 검색 결과를 Context로 변환
- 질문과 Context를 구분한 Prompt 구성
- 검색된 문서만 사용하도록 지시
- 출처 포함 답변 반환
- 검색 근거 부족 시 LLM 호출 생략 또는 답변 거부

응답에는 최소한 다음을 포함한다.

```json
{
  "answer": "...",
  "sources": [],
  "retrieval": []
}
```

### 완료 조건

- 검색 결과와 생성 답변을 별도로 볼 수 있다.
- 답변에 사용된 출처를 확인할 수 있다.
- 문서에 없는 경험을 질문하면 답변을 거부한다.
- 검색 실패와 LLM 실패가 구분된다.

---

## P1-07. 재색인과 변경 감지

### 구현

- 원문 Hash 저장
- 변경되지 않은 문서는 재처리하지 않음
- 변경된 문서는 기존 Chunk 삭제 후 재색인
- 삭제된 문서의 Point 정리

### 완료 조건

- 변경 없음, 수정, 삭제 시나리오가 구분된다.
- 문서 수정 후 이전 Chunk가 남지 않는다.
- 재색인 결과를 로그나 응답으로 확인할 수 있다.

---

## Phase 1 완료 기준

다음 질문에 코드와 실행 결과를 근거로 답할 수 있어야 한다.

- RAG와 단순 LLM 호출의 차이는 무엇인가
- Chunk가 너무 크거나 작으면 어떤 문제가 생기는가
- Embedding 모델과 Vector DB 차원의 관계는 무엇인가
- Vector Search 결과의 score는 어떻게 활용하는가
- 검색 실패와 생성 실패는 어떻게 구분하는가
- 출처 추적을 위해 어떤 metadata가 필요한가
- 근거 없는 답변을 어느 단계에서 막는가

---

# Phase 2. LangChain으로 단계별 교체

## 목표

완성된 수동 파이프라인을 유지한 상태에서 한 구성요소씩 LangChain으로 교체하고 차이를 기록한다.

처음부터 전체 체인이나 자동 RAG 예제를 복사하지 않는다.

## 원칙

- 수동 구현을 삭제하기 전에 동일한 입력과 출력을 비교한다.
- 한 번에 하나의 구성요소만 교체한다.
- 교체 전후 평가 질문 결과를 기록한다.
- LangChain 객체 이름만 아는 것이 아니라 내부 역할을 설명한다.

---

## P2-01. Text Splitter 교체

- 기존 Chunker와 LangChain Text Splitter 결과 비교
- Chunk 개수, 평균 길이, 경계, overlap 비교
- 구조 기반 분할이 손실되는지 확인

## P2-02. Embedding 추상화 교체

- 직접 OpenAI API 호출과 LangChain Embeddings 비교
- batch, retry, 설정 방식 비교
- 생성된 벡터 개수와 차원 검증

## P2-03. Qdrant VectorStore 교체

- 직접 Qdrant Client와 LangChain QdrantVectorStore 비교
- payload와 metadata 구조 확인
- 추가·검색·삭제 동작 비교

## P2-04. Retriever 적용

- VectorStore 검색을 Retriever로 감싸기
- `top_k`, threshold, metadata filter 전달 방식 확인
- 검색 결과 관찰 기능 유지

## P2-05. Prompt와 Chat Model 교체

- PromptTemplate 적용
- Chat Model 추상화 적용
- 수동 Prompt와 최종 메시지 비교
- 답변과 출처 응답 구조 유지

## P2-06. 전체 파이프라인 비교

다음 기준으로 수동 구현과 LangChain 구현을 비교한다.

- 코드량
- 설정 가시성
- 디버깅 난이도
- 오류 처리
- metadata 제어
- 테스트 용이성
- 프레임워크 종속성
- 검색 품질 차이

## Phase 2 완료 기준

- 수동 구현과 LangChain 구현을 둘 다 실행할 수 있다.
- 같은 평가 질문으로 결과를 비교할 수 있다.
- LangChain이 대신 처리하는 부분을 설명할 수 있다.
- 편리함과 제어권의 trade-off를 문서화했다.

---

# Phase 3. 검색 품질 개선과 평가

## 목표

단순 Dense Vector Search를 기준선으로 삼고 검색 실패 유형을 분석한 뒤 개선한다.

모든 기능을 넣는 것이 아니라, 평가 결과가 개선 필요성을 보여줄 때만 추가한다.

---

## P3-01. 기준선 평가

평가 질문별로 다음을 기록한다.

- 기대 문서가 Top K에 포함됐는지
- 기대 문서의 최초 순위
- 답변 가능 여부 판단이 맞았는지
- 잘못 검색된 문서
- 답변의 출처 일치 여부

최소 지표:

- Hit@K
- MRR
- Answerability accuracy
- Source accuracy

---

## P3-02. Metadata Filter

다음과 같은 조건 검색을 추가한다.

- 문서 유형
- 프로젝트
- 연도
- 기술
- 사용자 또는 소유자 구분을 가정한 식별자

Vector Search와 metadata filter의 역할 차이를 확인한다.

---

## P3-03. Keyword 또는 Sparse Search

정확한 기술명이나 고유명사가 Vector Search에서 누락되는 사례를 기준으로 추가한다.

예시:

- Java 17
- OpenFGA
- RabbitMQ
- 특정 프로젝트명

Qdrant의 sparse vector 또는 별도의 간단한 BM25 구현 중 하나를 선택한다.
선택 이유를 `DECISIONS.md`에 기록한다.

---

## P3-04. Hybrid Retrieval

Dense와 keyword/sparse 결과를 결합한다.

비교 대상:

1. Dense only
2. Keyword 또는 sparse only
3. Hybrid

결합 방식과 가중치를 명시한다.

---

## P3-05. Reranking

초기 검색 후보에 reranker를 적용한다.

- 검색과 reranking의 역할을 구분한다.
- reranker 적용 전후 순위를 기록한다.
- 데이터가 작을 때 비용 대비 효과를 평가한다.

검색 품질이 이미 충분하면 구현을 보류할 수 있다.

---

## P3-06. Chunk 전략 비교

최소 세 구성을 비교한다.

- 작은 Chunk
- 큰 Chunk
- 구조 기반 Chunk

질문 유형별로 어떤 전략이 유리한지 기록한다.

---

## P3-07. 최종 평가

모든 평가 질문을 다시 실행하고 기준선과 비교한다.

결과 문서에는 다음을 포함한다.

- 개선된 질문
- 악화된 질문
- 개선이 없던 질문
- 실패 원인
- 최종 추천 설정
- career-fit-ai에 적용할 검색 전략

---

## Phase 3 완료 기준

- Dense Search의 실패 유형을 설명할 수 있다.
- metadata filter와 semantic search의 역할을 구분할 수 있다.
- Hybrid Search가 필요한 질문 유형을 확인했다.
- reranker의 비용과 효과를 비교했다.
- 설정 변경을 감이 아니라 평가 결과로 결정했다.

---

# 4. 종료 산출물

Java 이식 전 다음 문서를 작성한다.

## `docs/FINAL_REVIEW.md`

포함 내용:

1. 직접 구현한 RAG 데이터 흐름
2. LangChain 적용 전후 비교
3. 최종 Chunk 전략
4. 최종 검색 전략
5. 평가 결과
6. 근거 없는 답변 방지 방식
7. 운영 시 고려할 항목
8. career-fit-ai에 이식할 구성요소
9. Java에서 다시 설계해야 할 부분
10. 현재 구현의 한계

---

# 5. 권장 저장소 구조

```text
career-rag-lab/
├─ AGENTS.md
├─ README.md
├─ pyproject.toml
├─ docker-compose.yml
├─ .env.example
├─ src/
│  └─ app/
│     ├─ api/
│     ├─ core/
│     ├─ ingestion/
│     ├─ retrieval/
│     ├─ generation/
│     └─ evaluation/
├─ tests/
├─ data/
│  ├─ samples/
│  └─ evaluation/
└─ docs/
   ├─ RAG_LEARNING_PLAN.md
   ├─ PROGRESS.md
   ├─ DECISIONS.md
   ├─ TASK_TEMPLATE.md
   └─ FINAL_REVIEW.md
```

현재 단계에서 필요하지 않은 디렉터리는 미리 만들지 않아도 된다.

---

# 6. Git 진행 원칙

GitHub 저장소를 사용하되 복잡한 협업 절차는 적용하지 않는다.

- 작업 하나당 Issue 하나
- Issue 완료 시 로컬 테스트
- 의미 있는 단위로 커밋
- 기본적으로 `main`에 직접 커밋해도 됨
- 큰 실험이나 되돌릴 가능성이 높은 변경만 브랜치 사용
- PR은 필수가 아님
- Issue 완료 후 `PROGRESS.md` 갱신

권장 커밋 예시:

```text
feat: add markdown document loader
test: cover empty document loading
docs: record chunking decision
```

---

# 7. Codex 요청 원칙

Codex에는 전체 Phase가 아니라 현재 Issue만 요청한다.

요청 시 포함할 내용:

- 현재 Issue
- 구현 목적
- In scope
- Out of scope
- 완료 조건
- 참고할 계획 문서 위치

Codex가 작업을 마친 후 반드시 설명하게 할 내용:

- 변경 파일
- 데이터 흐름
- 테스트 결과
- 직접 확인할 실행 방법
- 남은 문제
- 다음 작업 제안
