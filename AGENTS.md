# AGENTS.md

- Read `docs/PROGRESS.md` before changing code.
- Follow only the current task and its completion criteria.
- Use Python, FastAPI, Qdrant, OpenAI API, Docker Compose, and pytest.
- Do not use LangChain during Phase 1.
- From Phase 2, replace the manual pipeline incrementally with LangChain.
- Keep retrieval results observable separately from generated answers.
- Preserve source and metadata for every chunk.
- Do not generate an answer when retrieved evidence is insufficient.
- Do not add frameworks, databases, or features outside the current phase.
- Keep secrets and personal documents out of Git.
- Add or update tests for changed behavior.
- Update `docs/PROGRESS.md` after each completed task.
- Record important design choices in `docs/DECISIONS.md`.
- Explain the data flow and test results in the completion report.
- Never claim unimplemented work is complete.
