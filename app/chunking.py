import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.documents import Document


ChunkingStrategy = Literal["structure", "fixed", "langchain_recursive"]
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ChunkMetadata:
    """Chunk의 식별, 출처, 원문 위치를 추적하는 정보.

    `start_char:end_char`로 원문을 자르면 Chunk content와 정확히 일치한다.
    """

    chunk_id: str
    document_id: str
    source: str
    section: str
    chunk_index: int
    document_type: str
    project_name: str | None
    strategy: ChunkingStrategy
    start_char: int
    end_char: int


@dataclass(frozen=True)
class Chunk:
    """Embedding과 검색의 실제 입력 단위."""

    content: str
    metadata: ChunkMetadata


@dataclass(frozen=True)
class ChunkingComparison:
    """같은 문서를 수동 전략과 LangChain 전략으로 나란히 비교한다."""

    structure: list[Chunk]
    fixed: list[Chunk]
    langchain_recursive: list[Chunk]


@dataclass(frozen=True)
class ChunkingStatistics:
    """전략별 Chunk 개수·길이·경계·실제 overlap을 관찰하는 요약값."""

    chunk_count: int
    average_length: float
    lengths: tuple[int, ...]
    boundaries: tuple[tuple[int, int], ...]
    overlaps: tuple[int, ...]


def chunk_by_structure(document: Document, max_chars: int = 500) -> list[Chunk]:
    """Markdown section을 우선 보존하며 최대 길이 안에서 문서를 나눈다."""
    _validate_positive_size("max_chars", max_chars)
    headings = _find_headings(document.content)
    spans: list[tuple[int, int, str]] = []

    if headings:
        # 각 제목의 시작부터 다음 제목 직전까지를 하나의 의미 section으로 본다.
        for index, (start, section) in enumerate(headings):
            end = headings[index + 1][0] if index + 1 < len(headings) else len(
                document.content
            )
            spans.extend(
                (part_start, part_end, section)
                for part_start, part_end in _split_span(
                    document.content, start, end, max_chars
                )
            )
    else:
        spans.extend(
            (start, end, "document")
            for start, end in _split_span(
                document.content, 0, len(document.content), max_chars
            )
        )

    return _build_chunks(document, spans, strategy="structure")


def chunk_by_fixed_size(
    document: Document, chunk_size: int = 500, overlap: int = 50
) -> list[Chunk]:
    """문서 구조와 무관하게 일정한 글자 수와 overlap으로 나눈다."""
    _validate_positive_size("chunk_size", chunk_size)
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be at least 0 and smaller than chunk_size")

    headings = _find_headings(document.content)
    spans: list[tuple[int, int, str]] = []
    start = 0
    while start < len(document.content):
        end = min(start + chunk_size, len(document.content))
        spans.append((start, end, _section_at(headings, start)))
        if end == len(document.content):
            break
        # 이전 Chunk의 끝부분을 다음 Chunk 앞에도 넣어 경계에서 문맥이 끊기는
        # 문제를 줄인다. 대신 같은 문장이 여러 Chunk에 중복될 수 있다.
        start = end - overlap

    return _build_chunks(document, spans, strategy="fixed")


def chunk_by_langchain_recursive(
    document: Document, chunk_size: int = 500, overlap: int = 50
) -> list[Chunk]:
    """LangChain의 재귀 문자 분할기로 원문과 metadata를 보존해 나눈다."""
    _validate_positive_size("chunk_size", chunk_size)
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be at least 0 and smaller than chunk_size")

    # LangChain은 앞쪽 separator부터 시도해 문단·줄·공백·문자 순으로
    # 경계를 찾는다. start_index를 받아 각 결과를 원문 위치로 되돌린다.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""],
        keep_separator=True,
        add_start_index=True,
        strip_whitespace=False,
    )
    split_documents = splitter.create_documents(
        [document.content],
        metadatas=[
            {
                "source": document.metadata.source,
                "document_type": document.metadata.document_type,
                "project_name": document.metadata.project_name,
            }
        ],
    )
    headings = _find_headings(document.content)
    spans = [
        (
            int(item.metadata["start_index"]),
            int(item.metadata["start_index"]) + len(item.page_content),
            _section_at(headings, int(item.metadata["start_index"])),
        )
        for item in split_documents
    ]
    return _build_chunks(document, spans, strategy="langchain_recursive")


def compare_chunking_strategies(
    document: Document,
    structure_max_chars: int = 500,
    fixed_chunk_size: int = 500,
    fixed_overlap: int = 50,
    langchain_chunk_size: int = 500,
    langchain_overlap: int = 50,
) -> ChunkingComparison:
    """같은 원문에 수동 2종과 LangChain 전략을 적용해 비교한다."""
    return ChunkingComparison(
        structure=chunk_by_structure(document, max_chars=structure_max_chars),
        fixed=chunk_by_fixed_size(
            document, chunk_size=fixed_chunk_size, overlap=fixed_overlap
        ),
        langchain_recursive=chunk_by_langchain_recursive(
            document, chunk_size=langchain_chunk_size, overlap=langchain_overlap
        ),
    )


def summarize_chunks(chunks: list[Chunk]) -> ChunkingStatistics:
    """분할 구현과 무관한 공통 지표로 결과 차이를 수치화한다."""
    lengths = tuple(len(chunk.content) for chunk in chunks)
    boundaries = tuple(
        (chunk.metadata.start_char, chunk.metadata.end_char) for chunk in chunks
    )
    overlaps = tuple(
        max(0, previous.metadata.end_char - current.metadata.start_char)
        for previous, current in zip(chunks, chunks[1:])
    )
    return ChunkingStatistics(
        chunk_count=len(chunks),
        average_length=sum(lengths) / len(lengths) if lengths else 0.0,
        lengths=lengths,
        boundaries=boundaries,
        overlaps=overlaps,
    )


def _build_chunks(
    document: Document,
    spans: list[tuple[int, int, str]],
    strategy: ChunkingStrategy,
) -> list[Chunk]:
    # source가 같으면 같은 document ID가 만들어진다. Chunk ID에는 전략과
    # 원문 범위, 실제 내용을 모두 넣어 입력이 바뀌면 ID도 바뀌게 한다.
    document_id = _stable_hash(document.metadata.source, length=16)
    chunks: list[Chunk] = []
    for chunk_index, (start, end, section) in enumerate(spans):
        content = document.content[start:end]
        chunk_id = _stable_hash(
            f"{document_id}:{strategy}:{start}:{end}:{content}", length=24
        )
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            source=document.metadata.source,
            section=section,
            chunk_index=chunk_index,
            document_type=document.metadata.document_type,
            project_name=document.metadata.project_name,
            strategy=strategy,
            start_char=start,
            end_char=end,
        )
        chunks.append(Chunk(content=content, metadata=metadata))
    return chunks


def _find_headings(content: str) -> list[tuple[int, str]]:
    return [(match.start(), match.group(2)) for match in HEADING_PATTERN.finditer(content)]


def _section_at(headings: list[tuple[int, str]], position: int) -> str:
    """고정 크기 Chunk 시작점에서 가장 가까운 이전 제목을 찾는다."""
    section = "document"
    for heading_start, heading_title in headings:
        if heading_start > position:
            break
        section = heading_title
    return section


def _split_span(
    content: str, start: int, end: int, max_chars: int
) -> list[tuple[int, int]]:
    """section을 최대 길이로 나누되 문단과 줄 경계를 먼저 선택한다."""
    parts: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        candidate_end = min(cursor + max_chars, end)
        if candidate_end < end:
            # 너무 짧은 Chunk를 피하려고 최대 길이의 절반 이후에서만
            # 자연스러운 경계를 찾는다. 없으면 최대 길이에서 그대로 자른다.
            boundary = content.rfind("\n\n", cursor + max_chars // 2, candidate_end)
            if boundary == -1:
                boundary = content.rfind("\n", cursor + max_chars // 2, candidate_end)
            if boundary != -1:
                separator_length = 2 if content.startswith("\n\n", boundary) else 1
                candidate_end = boundary + separator_length
        parts.append((cursor, candidate_end))
        cursor = candidate_end
    return parts


def _validate_positive_size(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")


def _stable_hash(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
