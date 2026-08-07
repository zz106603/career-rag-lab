from fastapi import FastAPI

app = FastAPI(title="career-rag-lab")


@app.get("/health")
def health() -> dict[str, str]:
    """외부 서비스와 무관하게 FastAPI 자체가 응답 가능한지 확인한다."""
    return {"status": "ok"}
