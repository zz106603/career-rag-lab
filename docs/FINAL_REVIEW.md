# Career RAG Lab 최종 리뷰

이 문서는 Python 학습 구현을 Java 기반 `career-fit-ai`로 옮기기 전에 구현·검증·미구현 범위를 구분한 종료 기록이다. 세부 근거는 [`DECISIONS.md`](DECISIONS.md), 실행 기록은 [`PROGRESS.md`](PROGRESS.md), 최종 수치는 [`final-search-evaluation.json`](../data/evaluation/final-search-evaluation.json)에 있다.

## 1. 직접 구현한 RAG 데이터 흐름

```text
Markdown → 로딩·metadata → 구조 기반 Chunk(최대 500자)
→ OpenAI Embedding → Qdrant dense+sparse 색인
→ 질문 Dense+Sparse 검색 → RRF 결합 → 근거 threshold 판정
→ 근거가 있을 때만 답변 생성 → answer/sources/retrieval/generated 반환
```

Chunk마다 결정적 `chunk_id`, `document_id`, source, section, 문서 유형, 프로젝트명, 원문 범위를 보존한다. 문서 Hash와 색인 fingerprint로 추가·수정·삭제·변경 없음을 판별하고 변경 Chunk만 다시 Embedding한다. 검색 결과는 생성 답변과 분리해 낮은 score나 잘못된 출처를 직접 관찰할 수 있다.

## 2. LangChain 적용 전후 비교

| 영역 | 수동 구현 | LangChain 적용 후 |
|---|---|---|
| Chunking | 구조/고정 크기 Chunker | RecursiveCharacterTextSplitter 비교 |
| Embedding | OpenAI SDK batch 호출 | OpenAIEmbeddings |
| 저장 | Qdrant Point 직접 관리 | QdrantVectorStore |
| 검색 | Qdrant query 직접 호출 | BaseRetriever 기반 observable retriever |
| Prompt | 문자열 조립 | PromptTemplate |
| RAG 흐름 | Python 조건문 | LCEL + RunnableBranch |

동일 벡터와 조건에서 수동·LangChain 파이프라인의 품질은 같았다. 프레임워크 교체는 품질 자동 개선이 아니라 조합 가능한 추상화로의 변경이다. 수동 구현은 회귀 비교용으로 남겼다. LCEL에서는 evidence 유무를 상태로 만들고 `RunnableBranch`가 근거 없는 경로에서 생성 모델을 호출하지 않도록 했다.

## 3. 최종 Chunk 전략

현재 색인과 추천은 Markdown 구조 기반 최대 500자 Chunk다.

| 전략 | Chunk 수 | 상대 입력량 | Hit@3 | MRR | Source recall |
|---|---:|---:|---:|---:|---:|
| Recursive 200/20 | 24 | 1.042 | 0.917 | 0.792 | 0.819 |
| Recursive 800/80 | 6 | 1.000 | 1.000 | 0.861 | 0.875 |
| 구조 기반 500 | 28 | 1.000 | 1.000 | 0.819 | 0.847 |

이는 재Embedding 없는 lexical proxy다. 큰 Chunk가 단어 검색에서는 가장 높았지만 Dense 벡터의 의미 희석은 측정하지 못했다. 이 결과만으로 재색인하지 않고 section 경계와 추적성이 검증된 구조 기반 설정을 유지한다.

## 4. 최종 검색 전략

- Dense와 Qdrant Sparse에서 후보를 각각 6개 가져온다.
- Chunk ID로 중복 제거 후 동일 가중치 RRF(`k=60`)로 결합한다.
- 최종 3개와 Dense·Sparse·Hybrid 원본 목록 및 순위를 보존한다.
- 명시적으로 아는 조건만 metadata exact-match AND filter로 검색 전에 적용한다.
- 현재 품질에서는 reranker를 추가하지 않는다.

`POST /search/hybrid`는 구현되어 있지만 `POST /answer`의 기본 Retriever는 아직 LangChain Dense 경로다. Hybrid를 답변 기본 경로에 연결하고 threshold를 재조정하는 작업은 구현되지 않았다. 최종 추천이 이미 답변 API에 적용된 것은 아니다.

## 5. 평가 결과

답변 가능 12개만 검색 정답 순위 평가에 포함했다.

| 지표 | Dense 기준선 | 최종 Hybrid |
|---|---:|---:|
| Hit@3 | 1.000 | 1.000 |
| MRR | 1.000 | 1.000 |
| Mean source recall | 0.917 | 0.917 |

개선 0개, 악화 0개, 변화 없음 12개였다. 답변 불가 3개는 기대 출처가 없어 제외했다. q10은 기대 출처 1개, q11은 2개가 Top 3에서 누락됐다. Hit@3와 MRR은 최초 정답만 보므로 다중 문서 질문에서는 source recall도 필요하다.

저장된 생성 기준선의 거절 정확도는 0.867, 답변 출처 완전 일치는 0.400이다. P3-07에서는 생성 API를 다시 호출하지 않았으므로 최종 Hybrid 생성 품질이 아닌 기존 수치다.

## 6. 근거 없는 답변 방지 방식

Prompt만 믿지 않고 애플리케이션이 먼저 score threshold를 적용한다. 통과 evidence가 없으면 `insufficient_evidence`를 반환하고 생성 API를 호출하지 않는다. Prompt는 검색 Context만 사실로 사용하도록 제한한다. threshold 전 `retrieval`, 실제 `sources`, `generated`를 분리하고 검색 실패와 생성 실패도 다른 오류로 처리한다.

## 7. 운영 시 고려할 항목

- `.env`와 개인 문서는 Git에서 제외하고 키를 로그에 노출하지 않는다.
- Qdrant schema, vector 차원, distance, sparse 설정 호환성을 확인한다.
- 원문·Chunk·Embedding 설정 변경은 fingerprint로 재색인 범위를 정한다.
- 변경 저장 후 삭제해 API 실패 시 기존 검색 상태를 보존한다.
- latency, API/token 비용, 빈 근거 비율과 질문 유형별 품질을 관찰한다.
- threshold, candidate/top K와 RRF 가중치는 데이터 변화 후 재평가한다.
- Qdrant 백업·복구, migration, rollback과 실제 문서의 외부 전송 정책이 필요하다.

## 8. career-fit-ai에 이식할 구성요소

- `Document`, `Chunk`, `SearchResult`, `AnswerResult` 도메인 계약
- source·원문 범위를 끝까지 보존하는 metadata 규칙
- Hash와 fingerprint 기반 증분 재색인
- Dense·Sparse 관찰과 RRF 결합 경계
- metadata filter와 retrieval/evidence/answer 분리 계약
- 근거 부족 시 생성을 건너뛰는 상태 전환
- 고정 평가 질문과 Hit@K, MRR, source recall, answerability 지표

Python 클래스 자체보다 이 계약과 상태 전환을 Java의 명시적 타입과 테스트로 옮기는 것이 핵심이다.

## 9. Java에서 다시 설계해야 할 부분

- Spring 설정 검증, 의존성 주입과 외부 클라이언트 생명주기
- Java record/class 도메인 모델과 API DTO 분리
- Qdrant Java Client의 named vector, filter와 batch upsert
- OpenAI 비동기 호출, timeout, retry, rate limit과 비용 계측
- LCEL 분기를 대신할 orchestration 서비스 또는 상태 머신
- Qdrant 재색인 실패 복구, Collection alias, 동시 실행 방지와 모니터링
- 한글 tokenizer 또는 형태소 분석기 선택

LangChain4j 사용은 별도 선택이다. 먼저 정책을 순수 Java로 테스트할 수 있어야 프레임워크가 바뀌어도 근거 부족 방어가 유지된다.

## 10. 현재 구현의 한계

- 합성 문서 6개와 질문 15개라 실제 규모를 대표하지 않는다.
- 최종 평가는 저장된 실제 Dense source 순위와 로컬 Sparse 순위를 source 단위로 결합했으며 전체 질문을 Chunk 단위 Dense로 재실행하지 않았다.
- Hybrid 적용 후 생성 품질을 재평가하지 않았다.
- `/answer` 기본 경로에는 Hybrid가 아직 연결되지 않았다.
- q10·q11 다중 문서 source recall 실패가 남았다.
- Chunk 비교는 lexical proxy이며 한글 tokenizer는 정규식 기반이다.
- RRF는 질문 유형과 관계없이 동일 가중치다.
- reranker와 Chunk 단위 relevance 정답이 없다.
- Starlette `TestClient` deprecation warning이 남아 있다.

최종 성과는 프레임워크 자체가 아니라 색인·검색·근거 판정·생성을 분리하고 각 단계의 결과를 평가 가능한 형태로 남긴 것이다.
