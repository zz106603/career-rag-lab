import argparse
from pathlib import Path

from app.chunking import compare_chunking_strategies, summarize_chunks
from app.documents import load_markdown_file


def compare_document(path: str | Path, chunk_size: int, overlap: int) -> str:
    """같은 문서의 세 분할 결과를 사람이 비교하기 쉬운 표 형태로 만든다."""
    document = load_markdown_file(path)
    comparison = compare_chunking_strategies(
        document,
        structure_max_chars=chunk_size,
        fixed_chunk_size=chunk_size,
        fixed_overlap=overlap,
        langchain_chunk_size=chunk_size,
        langchain_overlap=overlap,
    )
    rows = ["strategy chunks average_length boundaries overlaps"]
    for strategy, chunks in (
        ("structure", comparison.structure),
        ("fixed", comparison.fixed),
        ("langchain_recursive", comparison.langchain_recursive),
    ):
        statistics = summarize_chunks(chunks)
        rows.append(
            f"{strategy} {statistics.chunk_count} "
            f"{statistics.average_length:.2f} "
            f"{list(statistics.boundaries)} {list(statistics.overlaps)}"
        )
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="수동 Chunker와 LangChain Text Splitter 결과를 비교합니다."
    )
    parser.add_argument("path", type=Path, help="비교할 Markdown 파일")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    args = parser.parse_args()
    print(compare_document(args.path, args.chunk_size, args.overlap))


if __name__ == "__main__":
    main()
