# 기술 결정 기록

중요한 기술 선택만 기록한다. 단순 구현 내용이나 일일 작업 기록은
`PROGRESS.md`에 남긴다.

---

## 작성 형식

### D-XXX. 결정 제목

- 날짜:
- 상태: 제안 / 확정 / 폐기
- 관련 Phase:
- 문제:
- 선택지:
- 결정:
- 이유:
- 장점:
- 단점:
- 재검토 조건:

---

## D-001. Python 기반으로 RAG를 먼저 학습한다

- 날짜: 2026-08-07
- 상태: 확정
- 관련 Phase: 전체
- 문제: career-fit-ai의 Spring 구현 전 RAG 생태계와 데이터 흐름을 빠르게 학습해야 한다.
- 선택지:
  - Spring AI와 pgvector로 바로 구현
  - Python과 전용 Vector DB로 별도 학습
- 결정: Python, FastAPI, Qdrant 기반 학습 프로젝트를 먼저 진행한다.
- 이유: Python RAG 생태계, 전용 Vector DB, LangChain과 검색 평가 도구를 경험하기 쉽다.
- 장점: 자료와 라이브러리가 풍부하고 RAG 실험 속도가 빠르다.
- 단점: 이후 Java로 다시 구현해야 한다.
- 재검토 조건: Phase 3 완료 후 career-fit-ai 이식 구조를 설계할 때

---

## D-002. Phase 1에서는 LangChain을 사용하지 않는다

- 날짜: 2026-08-07
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: 처음부터 프레임워크를 사용하면 Embedding, 검색, Prompt 구성의 실제 흐름을 놓칠 수 있다.
- 선택지:
  - 처음부터 LangChain 사용
  - 수동 구현 후 단계별 교체
- 결정: Phase 1에서 직접 구현하고 Phase 2에서 LangChain으로 교체한다.
- 이유: 추상화가 대신 처리하는 범위를 비교하기 위해서다.
- 장점: 내부 동작과 오류 경계를 이해할 수 있다.
- 단점: 동일 기능을 일부 중복 구현한다.
- 재검토 조건: 없음

---

## D-003. Qdrant 데이터는 Docker named volume에 보존한다

- 날짜: 2026-08-07
- 상태: 확정
- 관련 Phase: Phase 0
- 문제: 로컬 Qdrant 컨테이너를 재생성해도 학습 데이터를 유지하면서 운영체제별 경로 차이를 피해야 한다.
- 선택지:
  - 호스트 디렉터리를 직접 마운트
  - Docker named volume 사용
  - 컨테이너 내부에만 저장
- 결정: `qdrant_storage` named volume을 `/qdrant/storage`에 마운트한다.
- 이유: Windows 경로와 권한 설정에 덜 의존하면서 컨테이너 생명주기와 데이터를 분리할 수 있다.
- 장점: `docker compose down` 이후에도 데이터가 유지되고 로컬 경로 설정이 단순하다.
- 단점: 데이터 파일을 호스트에서 직접 탐색하기 어렵고 별도 삭제 명령이 필요하다.
- 재검토 조건: Qdrant 데이터 파일을 직접 백업하거나 여러 프로젝트에서 공유해야 할 때

---

## D-004. 문서 로딩 오류는 조용히 건너뛰지 않는다

- 날짜: 2026-08-07
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: 빈 파일이나 잘못된 Markdown 문서를 조용히 제외하면 색인 누락을 발견하기 어렵다.
- 선택지:
  - 오류 문서를 건너뛰고 나머지만 반환
  - 첫 오류에서 로딩을 중단하고 명시적인 예외 발생
- 결정: 대상 Markdown 파일이 비어 있거나 읽을 수 없으면 디렉터리 로딩을 중단한다. 디렉터리의 비 Markdown 파일은 대상에서 제외하고, 단일 파일 로더에 전달된 비 Markdown 파일은 거부한다.
- 이유: Phase 1에서는 데이터 누락을 숨기지 않고 오류 경계를 관찰하는 것이 중요하다.
- 장점: 불완전한 문서 집합이 조용히 색인되는 것을 막고 실패 파일을 바로 확인할 수 있다.
- 단점: 하나의 잘못된 Markdown 파일 때문에 나머지 정상 문서도 반환되지 않는다.
- 재검토 조건: 대규모 문서를 부분 성공 방식으로 수집해야 할 때

---

## D-005. Chunk ID와 원문 위치를 결정적으로 생성한다

- 날짜: 2026-08-07
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: 재색인과 전략 비교에서 같은 Chunk를 식별하고 검색 결과를 원문으로 추적해야 한다.
- 선택지:
  - 실행할 때마다 임의 UUID 생성
  - source, 전략, 문자 범위, content를 해시해 ID 생성
- 결정: document ID는 source의 SHA-256 해시로, Chunk ID는 document ID·전략·문자 범위·content의 SHA-256 해시로 결정적으로 생성한다. 각 Chunk에는 `start_char`와 `end_char`도 저장한다.
- 이유: 같은 입력과 전략에서는 ID가 재현되고, 원문 일부가 바뀌면 영향을 받은 Chunk ID도 달라져야 한다.
- 장점: 재색인 중복 방지 기반을 제공하고 Chunk content를 원문 위치로 직접 검증할 수 있다.
- 단점: 파일명이 같으면 document ID가 충돌할 수 있고 분할 전략이나 내용 변경 시 Chunk ID가 바뀐다.
- 재검토 조건: 중첩 디렉터리나 동일 파일명의 여러 source를 지원할 때

---

## D-006. 기본 Embedding 모델은 text-embedding-3-small을 사용한다

- 날짜: 2026-08-07
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: RAG 학습에 필요한 실제 Embedding을 생성하면서 API 비용을 최소화해야 한다.
- 선택지:
  - `text-embedding-3-small` 1536차원
  - `text-embedding-3-large` 3072차원
- 결정: 기본 모델은 `text-embedding-3-small`, 기본 차원은 1536, batch 크기는 100으로 설정하고 모두 환경변수로 변경할 수 있게 한다.
- 이유: 현재 OpenAI Embedding 모델 중 small 모델의 입력 토큰 비용이 large 모델보다 낮고 학습용 데이터 규모에도 충분하다.
- 장점: 실제 API 호출 비용과 Qdrant 저장 크기를 낮게 유지하면서 다국어 의미 검색을 실험할 수 있다.
- 단점: large 모델보다 검색 품질이 낮을 수 있으며 batch 크기는 호출 횟수만 줄이고 입력 토큰 과금 자체를 줄이지 않는다.
- 재검토 조건: 평가 질문에서 검색 품질이 부족하거나 다른 차원의 Collection을 실험할 때

---

## D-007. 재색인은 문서 단위 삭제 후 교체한다

- 날짜: 2026-08-07
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: 문서 내용이나 Chunking 결과가 바뀌어 Chunk 수가 줄면 기존의 불필요한 Point가 남을 수 있다.
- 선택지:
  - 결정적 Point ID로 현재 Chunk만 upsert
  - document ID로 기존 Point를 모두 삭제한 뒤 현재 Chunk를 upsert
- 결정: 모든 새 벡터의 차원을 먼저 검증한 후 동일 document ID의 Point를 삭제하고 현재 Chunk 집합을 upsert한다.
- 이유: 단순 upsert만으로는 새 결과에 없는 이전 Chunk를 식별해 제거할 수 없기 때문이다.
- 장점: 재색인 후 Qdrant의 Point 집합이 현재 문서와 정확히 일치하고 중복이나 stale Chunk가 남지 않는다.
- 단점: 삭제 후 upsert가 실패하면 해당 문서가 일시적으로 색인에서 사라질 수 있다.
- 재검토 조건: 무중단 재색인이나 원자적인 버전 전환이 필요할 때

---

## D-008. 검색 결과를 생성 답변과 분리한다

- 날짜: 2026-08-09
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: 검색 품질과 LLM 답변 품질을 한 응답에 섞으면 어떤 단계에서 잘못된 근거가 선택됐는지 관찰하기 어렵다.
- 선택지:
  - 검색과 답변 생성을 하나의 API에서만 제공
  - LLM을 호출하지 않는 검색 API를 독립적으로 제공
- 결정: `/search`는 content, source, score, metadata만 반환하고 답변 생성 필드를 포함하지 않는다. `top_k`와 score threshold는 요청마다 조정할 수 있게 한다.
- 이유: 검색 순위와 근거 부족 상태를 LLM의 해석 없이 직접 평가해야 하기 때문이다.
- 장점: 검색 실패와 답변 생성 실패를 구분하고 threshold 변화에 따른 결과를 쉽게 비교할 수 있다.
- 단점: 최종 사용자용 답변을 얻으려면 별도의 답변 생성 단계를 호출해야 한다.
- 재검토 조건: 검색 관찰 가능성을 유지하면서 운영용 API를 통합할 때

---

## D-009. 근거 판정 후 gpt-5-nano로 답변을 생성한다

- 날짜: 2026-08-10
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: 검색 근거에 기반한 답변을 제공하면서 비용과 근거 없는 생성을 함께 줄여야 한다.
- 선택지:
  - 검색 결과와 무관하게 항상 고성능 모델 호출
  - score 기준을 통과한 근거가 있을 때만 저비용 모델 호출
- 결정: threshold 이상의 검색 결과가 있을 때만 상위 3개를 Context로 구성해 `gpt-5-nano` Responses API를 호출한다. 최대 출력은 300 token으로 제한한다.
- 이유: 현재 작업은 검색된 짧은 근거를 한국어로 정리하는 단순 생성이며, 근거 부족은 모델이 아니라 검색 단계에서 차단할 수 있다.
- 장점: 답변 생성 비용을 낮추고 문서에 없는 질문에는 생성 모델 호출 자체를 생략한다.
- 단점: 작은 모델은 복잡한 다중 근거 합성 품질이 부족할 수 있고 score threshold는 평가 결과에 따라 조정해야 한다.
- 재검토 조건: 평가 질문에서 답변·출처 정확도가 부족하거나 Context 길이가 크게 늘어날 때

---

## D-010. 증분 색인 상태는 Qdrant Point payload에 저장한다

- 날짜: 2026-08-10
- 상태: 확정
- 관련 Phase: Phase 1
- 문제: 변경되지 않은 문서의 Embedding 비용을 피하려면 현재 원문과 마지막 색인 상태를 비교해야 한다.
- 선택지:
  - 별도 상태 파일이나 데이터베이스에 문서 Hash 저장
  - 모든 Chunk의 Qdrant payload에 문서 Hash와 색인 fingerprint 저장
- 결정: 원문 SHA-256은 `document_hash`, 원문 Hash·Chunk 전략·최대 길이·Embedding 모델·차원을 조합한 값은 `index_fingerprint`로 모든 Point payload에 저장한다.
- 이유: Phase 1 범위에서 별도 저장소를 추가하지 않고도 Qdrant 자체에서 현재 색인 상태와 삭제 문서를 확인할 수 있다.
- 장점: 내용뿐 아니라 Chunking·Embedding 설정 변경도 재색인 대상으로 감지하며 문서 삭제 상태도 한 곳에서 계산할 수 있다.
- 단점: 문서의 모든 Point에 같은 상태 값이 중복되고, 기존 Hash 없는 Point는 최초 한 번 전체 갱신해야 한다.
- 재검토 조건: 여러 색인 버전을 동시에 운영하거나 원자적 상태 전환을 위한 별도 manifest가 필요할 때

---

## D-011. Text Splitter는 재귀 문자 분할기부터 비교한다

- 날짜: 2026-08-10
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: 수동 Chunker를 LangChain으로 교체할 때 어떤 동작 차이가 생기는지 관찰하면서 기존 metadata와 원문 추적성을 유지해야 한다.
- 선택지:
  - LangChain 전체 패키지와 Markdown header splitter 도입
  - `langchain-text-splitters`만 추가하고 `RecursiveCharacterTextSplitter` 비교
- 결정: 최소 패키지인 `langchain-text-splitters`만 추가하고, 문단·줄·공백·문자 순서의 separator를 사용하는 재귀 문자 분할기를 기존 구조 기반·고정 크기 구현과 비교한다. `start_index`를 원문 위치 metadata로 변환한다.
- 이유: 이번 단계는 Text Splitter만 교체하는 범위이며, 재귀 분할기는 길이를 제한하면서 자연 경계를 우선하는 동작을 수동 구현과 직접 비교하기 적합하다.
- 장점: Embedding과 VectorStore를 바꾸지 않고 LangChain의 경계 선택 및 overlap 동작만 분리해 관찰할 수 있으며 source·section·원문 위치를 계속 보존한다.
- 단점: 설정한 overlap은 separator 선택에 따라 실제 모든 Chunk 경계에 동일하게 적용되지 않으며, section은 원문 시작 위치를 이용해 기존 metadata 규칙으로 보완한다.
- 재검토 조건: Markdown 제목 metadata를 LangChain 자체 splitter에서 직접 생성하거나 token 기반 길이 제한이 필요할 때

---

## D-012. LangChain Embedding 결과를 기존 색인 모델로 변환한다

- 날짜: 2026-08-10
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: Embedding 추상화를 교체하면서 수동 OpenAI 호출과 Qdrant 색인 사이의 데이터 흐름을 비교 가능하게 유지해야 한다.
- 선택지:
  - 색인 파이프라인 전체를 LangChain 타입으로 즉시 변경
  - LangChain `OpenAIEmbeddings` 결과만 기존 `EmbeddedChunk`로 변환
- 결정: `langchain-openai`의 `OpenAIEmbeddings.embed_documents()`를 추가하되 반환 벡터를 기존 `EmbeddedChunk`로 변환하고, 수동 `embed_chunks()` 구현도 유지한다.
- 이유: 이번 단계의 교체 범위를 Embedding 호출 추상화에 한정하고 Qdrant 저장 방식은 다음 단계에서 독립적으로 비교해야 한다.
- 장점: 동일한 Chunk·모델·차원 설정을 사용하면서 호출 방식만 비교할 수 있고 기존 Qdrant 색인기와 증분 색인이 계속 동작한다.
- 단점: 두 Embedding 경로와 응답 검증 코드가 일시적으로 공존하며, 실제 결과 비교는 동일 입력에 API 비용이 두 번 발생할 수 있다.
- 재검토 조건: Qdrant VectorStore 교체 결과가 안정되어 LangChain 경로를 기본값으로 전환할 때

---

## D-013. VectorStore 비교에서는 기존 Embedding을 재사용한다

- 날짜: 2026-08-10
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: 수동 Qdrant 색인과 LangChain VectorStore를 같은 조건에서 비교하면서 불필요한 OpenAI 비용과 다른 Embedding 값의 영향을 제거해야 한다.
- 선택지:
  - 각 색인 경로에서 OpenAI Embedding을 별도로 생성
  - 이미 생성한 `EmbeddedChunk` 벡터를 LangChain Embeddings Adapter로 재사용
- 결정: 비교용 `PrecomputedEmbeddings`가 예상 Chunk content에 기존 벡터를 반환하게 하고, 같은 Point UUID와 content key를 사용해 별도 Collection에 저장한다.
- 이유: 비교 대상은 VectorStore의 저장 방식이며 Embedding 생성은 P2-02에서 이미 독립적으로 비교했기 때문이다.
- 장점: 외부 API 비용 없이 동일 벡터·Point ID·content·metadata 보존 여부를 직접 비교할 수 있다.
- 단점: LangChain은 metadata를 지정한 payload key 아래 중첩하므로 기존 평면 payload와 필터 경로가 달라진다.
- 재검토 조건: LangChain VectorStore를 기본 색인 경로로 전환해 증분 상태 payload와 검색 필터를 통합할 때

---

## D-014. Retriever에서도 검색 score를 별도로 보존한다

- 날짜: 2026-08-10
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: 일반적인 LangChain Retriever는 `Document` 목록을 반환해 Qdrant 유사도 score가 최종 검색 결과에서 보이지 않는다.
- 선택지:
  - score 없이 기본 `VectorStoreRetriever` 사용
  - `BaseRetriever`를 확장해 VectorStore의 `(Document, score)`를 metadata에 전달한 뒤 기존 `SearchResult`로 변환
- 결정: `ObservableQdrantRetriever`가 `similarity_search_with_score()`를 호출하고 score를 보존하며, 서비스 경계에서 기존 `SearchResult`로 변환한다.
- 이유: 검색과 답변 품질을 분리해서 평가하려면 top_k와 threshold뿐 아니라 실제 score도 계속 관찰할 수 있어야 한다.
- 장점: 기존 `/search` 응답 계약과 답변의 retrieval 필드를 유지하면서 LangChain Retriever 인터페이스를 사용할 수 있다.
- 단점: 기본 Retriever를 그대로 사용하는 것보다 얇은 사용자 정의 계층이 추가되며 LangChain의 내부 payload 식별 metadata도 함께 반환된다.
- 재검토 조건: LangChain이 Retriever 결과 score를 표준 필드로 제공하거나 평가 계층에서 별도 trace로 score를 관리할 때

---

## D-015. PromptTemplate은 질문과 검색 Context만 변수화한다

- 날짜: 2026-08-10
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: 수동 Prompt를 LangChain으로 교체하면서 검색 근거의 경계와 Responses API의 상위 지침을 유지해야 한다.
- 선택지:
  - 안전 지침까지 하나의 PromptTemplate 문자열에 포함
  - 안전 지침은 Responses API `instructions`에 유지하고 질문·Context만 Template 변수로 분리
- 결정: `PromptTemplate`은 `query`와 `context`만 입력받고, Context에는 검색된 content, source, section만 넣는다. 기존 `ANSWER_INSTRUCTIONS`는 변경하지 않는다.
- 이유: 검색 문서 안의 텍스트와 애플리케이션 지침을 같은 계층에 섞지 않고, 이번 단계에서는 Prompt 형식화 부분만 독립적으로 비교하기 위해서다.
- 장점: 같은 입력에서 수동 Prompt와 완전히 동일한 문자열을 비교할 수 있고 score·내부 metadata가 모델 Context에 불필요하게 포함되지 않는다.
- 단점: Context 직렬화 로직이 수동·LangChain 경로에 일시적으로 중복되며 실제 생성 호출 연결은 다음 Chain 구성 단계에 남는다.
- 재검토 조건: LangChain RAG Chain이 기본 경로가 되어 메시지 기반 ChatPromptTemplate 또는 구조화 Context가 필요할 때

---

## D-016. 근거 판정은 생성 모델 앞의 Chain 분기로 유지한다

- 날짜: 2026-08-11
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: Retriever, PromptTemplate과 생성 모델을 Chain으로 연결하면서도 근거 부족 시 생성 비용과 hallucination을 차단해야 한다.
- 선택지:
  - 모든 검색 결과를 모델에 보내고 Prompt로 거부를 요청
  - 검색 결과를 보존한 뒤 LCEL `RunnableBranch`에서 threshold 근거 유무를 판정
- 결정: retrieval 전체를 상태에 보존하고 threshold를 통과한 evidence가 없으면 거부 `AnswerResult`를 반환한다. evidence가 있을 때만 `PromptTemplate | ChatOpenAI | StrOutputParser`를 실행한다.
- 이유: 수동 파이프라인에서 검증한 생성 전 근거 판정과 API 비용 절감 규칙을 LangChain 추상화에서도 유지해야 한다.
- 장점: 모델을 호출하지 않은 거부와 생성된 답변을 `generated`로 구분하고 기존 API 결과 계약을 그대로 비교할 수 있다.
- 단점: 단순한 직선형 Chain보다 상태 변환과 조건 분기 코드가 추가되며 검색·생성 오류를 별도로 변환해야 한다.
- 재검토 조건: 평가 결과에 따라 threshold 판정을 reranker나 구조화된 정책 Chain으로 교체할 때

---

## D-017. 파이프라인 평가는 동일 벡터와 결과 계약으로 비교한다

- 날짜: 2026-08-11
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: 수동·LangChain 경로를 비교할 때 Embedding 변동과 서로 다른 결과 형식이 품질 차이로 섞일 수 있다.
- 선택지:
  - 두 문서 집합을 각각 다시 Embedding하고 최종 답변만 비교
  - 기존 벡터를 재사용하고 공통 `AnswerResult`에서 검색·거절·출처 지표를 분리
- 결정: 수동 Collection의 28개 벡터를 LangChain payload 구조로 복사하고, 동일 질문·top_k·threshold에서 검색 출처 재현율, 거절 정확도, 답변 출처 정확도와 API 호출 수를 비교한다.
- 이유: VectorStore 구조와 Chain 교체의 영향만 관찰하고 검색 결과와 생성 답변을 분리해서 실패 원인을 확인해야 한다.
- 장점: 문서 Embedding 비용과 벡터 변동을 제거하고 질문별 차이를 재현 가능한 JSON으로 남길 수 있다.
- 단점: 답변 출처 정확도의 완전 일치 기준은 관련된 추가 출처도 오답으로 계산하므로 지표를 사례와 함께 해석해야 한다.
- 재검토 조건: reranker, hybrid search 또는 별도 정답 문장 기준을 추가할 때

---

## D-018. API 기본 경로를 LangChain 파이프라인으로 전환한다

- 날짜: 2026-08-11
- 상태: 확정
- 관련 Phase: Phase 2
- 문제: 수동·LangChain 평가 품질이 같을 때 학습 목표를 이어가면서 데이터 최신성도 보장할 기본 경로를 결정해야 한다.
- 선택지:
  - 수동 파이프라인을 기본값으로 유지
  - 증분 색인을 LangChain payload에 맞춘 뒤 API까지 LangChain으로 전환
- 결정: 증분 색인이 LangChain 중첩 metadata에서 문서 상태를 읽고 추가·수정·삭제를 처리하게 한 뒤 검색·답변 API의 기본 factory를 LangChain으로 전환한다. 수동 구현은 비교·회귀용으로 유지한다.
- 이유: Phase 2의 목적은 추상화를 단계적으로 교체하고 실제 기본 경로에서 학습을 이어가는 것이다. 평가 품질이 동일하므로 증분 색인 정합성까지 보완하면 수동 경로를 기본값으로 남길 이유가 없다.
- 장점: 색인, Retriever, Prompt, Chain이 같은 LangChain payload를 사용하며 Phase 3 개선을 LangChain 기본 경로에서 진행할 수 있다.
- 단점: 기존 수동 Collection과 중첩 payload Collection이 로컬에 함께 남고, 수동·LangChain 구현을 회귀 비교 기간 동안 함께 관리한다.
- 재검토 조건: LangChain 의존성 문제나 검색 품질 회귀가 발생해 기본 경로를 안정적으로 실행할 수 없을 때

---

## D-019. 기준선 검색 지표는 답변 가능 질문만 계산한다

- 날짜: 2026-08-11
- 상태: 확정
- 관련 Phase: Phase 3
- 문제: 기대 출처가 없는 답변 불가 질문을 Hit@K와 MRR에 포함하면 검색 정답의 순위를 정의할 수 없다.
- 선택지:
  - 모든 질문에서 기대 출처가 없으면 검색 실패로 계산
  - 답변 가능 질문에서만 Hit@K·MRR을 계산하고 답변 불가 질문은 Answerability 지표로 평가
- 결정: Hit@K와 MRR은 기대 출처가 있는 12개 질문만 대상으로 계산한다. 답변 가능 여부와 답변 출처 완전 일치는 15개 전체에서 별도로 계산한다.
- 이유: 검색 정답이 정의되지 않은 질문에 임의의 reciprocal rank를 부여하지 않고 검색과 거절 품질을 분리해야 한다.
- 장점: 검색 순위 개선과 threshold 기반 거절 개선의 영향을 독립적으로 비교할 수 있다.
- 단점: Hit@K 1.0이어도 다중 문서 질문의 기대 출처를 전부 찾았다는 뜻은 아니므로 source recall과 질문별 결과를 함께 봐야 한다.
- 재검토 조건: 답변 불가 질문에도 검색하면 안 되는 명시적 negative 문서 기준을 추가할 때

---

## D-020. Metadata Filter는 Vector Search 전에 AND 조건으로 적용한다

- 날짜: 2026-08-11
- 상태: 확정
- 관련 Phase: Phase 3
- 문제: 관련 없는 문서를 줄이기 위해 metadata 조건을 검색 결과에 언제, 어떤 방식으로 적용할지 정해야 한다.
- 선택지:
  - Vector Search Top K 결과를 받은 뒤 애플리케이션에서 제거
  - Qdrant 검색 요청에 중첩 metadata exact-match 조건을 전달
- 결정: `document_type`, `project_name`, `source`의 입력된 조건을 `metadata.*` FieldCondition으로 만들고 Qdrant Vector Search 전에 AND로 적용한다.
- 이유: 검색 후 제거하면 결과 수가 Top K보다 부족해지고, 조건 밖 문서가 후보 순위를 먼저 차지하는 문제를 막지 못한다.
- 장점: 조건 범위 안에서 Top K를 채우며 Retriever, `/search`, `/answer`가 같은 filter 계약을 사용한다.
- 단점: 사용자가 잘못된 조건을 주면 관련 문서가 있어도 결과가 비며, exact match라 값의 표기와 대소문자가 정확해야 한다.
- 재검토 조건: 복수 값 OR 조건, 날짜 범위 또는 자동 filter 추출이 필요할 때

---

## D-021. Keyword Search는 Dense 결과와 분리된 학습용 lexical 기준선으로 시작한다

- 날짜: 2026-08-11
- 상태: 확정
- 관련 Phase: Phase 3
- 문제: 정확한 기술명 검색을 관찰하기 위해 처음부터 Sparse Vector 색인과 Hybrid 결합까지 동시에 도입할지 결정해야 한다.
- 선택지:
  - Sparse Vector와 Hybrid Search를 한 번에 구현
  - 기존 Chunk payload를 토큰화한 독립 Keyword Search를 먼저 구현
- 결정: 영문 기술명과 한글 토큰을 분리하고 서로 다른 일치 단어 수와 제한된 반복 횟수로 keyword score를 계산한다. 결과는 `/search/keyword`로 Dense Search와 분리해 노출한다.
- 이유: P3-03에서는 어휘 일치 검색의 장단점을 먼저 관찰하고 결합 방식은 P3-04에서 독립적으로 다뤄야 한다.
- 장점: 추가 Embedding이나 외부 API 없이 정확한 기술명 후보를 확인하고 Dense 결과와 직접 비교할 수 있다.
- 단점: 모든 Chunk를 읽어 애플리케이션에서 점수를 계산하므로 대규모 운영에 부적합하고, corpus 기반 IDF나 형태소 분석이 없어 일반 단어가 순위에 과도하게 영향을 줄 수 있다.
- 재검토 조건: P3-04 Hybrid Search에서 운영 가능한 Sparse Vector 또는 Qdrant 전문 검색 방식으로 결합할 때

---

## D-022. Sparse Vector는 결정적 token hash와 Qdrant IDF를 사용한다

- 날짜: 2026-08-11
- 상태: 확정
- 관련 Phase: Phase 3
- 문제: 외부 Sparse Embedding 모델을 추가하지 않고 Qdrant 기반 Sparse Search와 Hybrid Retrieval 구조를 학습해야 한다.
- 선택지:
  - 외부 SPLADE·BM25 Embedding 모델 의존성 추가
  - 기존 tokenizer의 token을 결정적 index로 변환하고 Qdrant IDF modifier 사용
- 결정: token의 SHA-256 앞 32bit를 sparse index로, 문서 내 출현 횟수를 값으로 사용하고 `text-sparse` vector에 Qdrant IDF modifier를 적용한다.
- 이유: 추가 모델 다운로드와 외부 API 없이 문서·질문을 같은 sparse 공간에 넣고 Qdrant 자체 sparse 검색을 경험할 수 있다.
- 장점: 같은 token은 실행마다 같은 index를 가지며 기존 Dense Vector를 재Embedding하지 않고 새 Collection으로 복사할 수 있다.
- 단점: 32bit hash 충돌 가능성이 있고 형태소 분석·학습된 sparse 표현이 없어 어휘가 다른 동의어는 찾지 못한다.
- 재검토 조건: 실제 규모의 corpus에서 충돌·품질 문제가 나타나거나 학습된 Sparse Embedding 모델을 도입할 때

---

## D-023. Dense와 Sparse 후보는 동일 가중치 RRF로 결합한다

- 날짜: 2026-08-17
- 상태: 확정
- 관련 Phase: Phase 3
- 문제: Dense Cosine score와 Sparse IDF score는 의미와 범위가 달라 원점수를 직접 더하면 한쪽 검색 방식이 부당하게 우세해질 수 있다.
- 선택지:
  - 두 원점수를 정규화하거나 가중 합산
  - 각 결과의 순위만 사용하는 Reciprocal Rank Fusion(RRF)
- 결정: 각 검색에서 최종 `top_k`의 2배(최소 5개) 후보를 가져와 Chunk ID로 중복을 제거하고, 동일 가중치와 `k=60`인 RRF로 결합한다. 원래 결과와 순위·score는 응답 metadata에 함께 보존한다.
- 이유: 별도 score 보정 데이터 없이도 서로 다른 검색 score 체계를 안전하게 결합하고 결과를 결정적으로 재현할 수 있다.
- 장점: 두 검색에서 함께 상위에 나타난 후보가 강화되며 Dense·Sparse·Hybrid 결과를 독립적으로 비교할 수 있다.
- 단점: 모든 질문에 동일 가중치를 사용하므로 질문 유형별 최적 가중치를 반영하지 못하고, 초기 후보에 포함되지 않은 문서는 복구할 수 없다.
- 재검토 조건: 전체 평가에서 질문 유형별 가중치가 필요하거나 reranker가 더 좋은 순위를 일관되게 만들 때

---

## D-024. 현재 검색 품질에서는 reranker 도입을 보류한다

- 날짜: 2026-08-17
- 상태: 확정
- 관련 Phase: Phase 3
- 문제: 별도 reranker가 작은 현재 문서 집합에서 검색 품질을 개선할 가능성과 비용·복잡도를 비교해야 한다.
- 선택지:
  - 외부 cross-encoder API를 호출
  - 로컬 cross-encoder 모델과 의존성을 추가
  - 현재 지표의 개선 가능 폭을 계산하고 필요할 때까지 보류
- 결정: 기준선 MRR과 정확 키워드 Hybrid MRR이 모두 1.0이고 기대 출처가 전부 1위이므로 reranker 구현을 보류한다. 적용 전 순위와 후보별 비용, 재검토 조건은 평가 JSON에 기록한다.
- 이유: 현재 정답 순위 지표의 상한에 도달해 reranker가 개선을 증명할 공간이 없으며, Chunk relevance 정답도 없어 뒤 순위 precision 개선을 객관적으로 측정할 수 없다.
- 장점: 외부 문서 전송, 요청 비용, 모델 다운로드와 추론 지연, 새 의존성을 추가하지 않는다.
- 단점: 뒤 순위의 관련 없는 Chunk를 줄일 가능성은 아직 평가하지 못하고, 문서가 늘어나면 현재 판단이 유효하지 않을 수 있다.
- 재검토 조건: 기대 출처가 1위가 아닌 Hybrid 사례가 생기거나, Chunk 단위 relevance 정답을 마련하거나, 관련 없는 후보가 답변 품질을 낮출 때
