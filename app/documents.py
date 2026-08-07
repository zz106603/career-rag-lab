from dataclasses import dataclass
from pathlib import Path


class DocumentLoadError(ValueError):
    """문서를 안전하게 읽을 수 없을 때 사용하는 기본 예외."""


class EmptyDocumentError(DocumentLoadError):
    """Markdown 문서에 공백 외의 내용이 없을 때 발생한다."""


class UnsupportedDocumentError(DocumentLoadError):
    """단일 파일 로더에 Markdown이 아닌 파일이 전달되면 발생한다."""


@dataclass(frozen=True)
class DocumentMetadata:
    """원문과 분리해 검색 결과의 출처와 문서 성격을 추적하는 정보."""

    source: str
    file_name: str
    document_type: str
    project_name: str | None


@dataclass(frozen=True)
class Document:
    """파일에서 읽은 원문과 검색에 필요한 metadata를 함께 보관한다."""

    content: str
    metadata: DocumentMetadata


def load_markdown_file(path: str | Path) -> Document:
    """Markdown 원문을 변형하지 않고 하나의 Document로 읽는다."""
    document_path = Path(path)
    if not document_path.exists():
        raise FileNotFoundError(f"Document does not exist: {document_path}")
    if not document_path.is_file():
        raise IsADirectoryError(f"Document path is not a file: {document_path}")
    if document_path.suffix.lower() != ".md":
        raise UnsupportedDocumentError(
            f"Only Markdown files are supported: {document_path}"
        )

    content = document_path.read_text(encoding="utf-8")
    if not content.strip():
        raise EmptyDocumentError(f"Markdown document is empty: {document_path}")

    # 현재 학습 문서 규칙상 `프로젝트 개요` section이 있으면 프로젝트 문서다.
    # 프로젝트명은 첫 번째 H1에서 가져와 이후 Chunk와 검색 결과에도 전달한다.
    title = _extract_title(content) or document_path.stem
    is_project = "## 프로젝트 개요" in content
    metadata = DocumentMetadata(
        source=document_path.name,
        file_name=document_path.name,
        document_type="project" if is_project else "profile",
        project_name=title if is_project else None,
    )
    return Document(content=content, metadata=metadata)


def load_markdown_directory(path: str | Path) -> list[Document]:
    """디렉터리 바로 아래의 Markdown 문서를 파일명 순서로 읽는다.

    정렬된 순서는 같은 입력에서 같은 처리 결과를 재현하기 위한 것이다.
    Markdown 하나라도 비어 있으면 예외가 전파되어 누락을 조용히 숨기지 않는다.
    """
    directory_path = Path(path)
    if not directory_path.exists():
        raise FileNotFoundError(f"Document directory does not exist: {directory_path}")
    if not directory_path.is_dir():
        raise NotADirectoryError(
            f"Document directory path is not a directory: {directory_path}"
        )

    markdown_paths = sorted(directory_path.glob("*.md"))
    return [load_markdown_file(document_path) for document_path in markdown_paths]


def _extract_title(content: str) -> str | None:
    """첫 번째 Markdown H1을 문서 제목으로 사용한다."""
    for line in content.splitlines():
        if line.startswith("# "):
            title = line.removeprefix("# ").strip()
            return title or None
    return None
