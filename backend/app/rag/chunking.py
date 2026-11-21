"""Split the policy markdown files into section-level chunks with citation metadata."""
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


def documents_dir() -> Path:
    configured = get_settings().RAG_DOCUMENTS_DIR
    # backend/app/rag/chunking.py -> parents[3] is the repo root (or "/" inside the Docker image)
    return Path(configured) if configured else Path(__file__).resolve().parents[3] / "rag_documents"


@dataclass
class Chunk:
    chunk_id: str
    slug: str
    document_title: str
    policy_id: str
    category: str
    version: str
    section: str
    content: str

    @property
    def embedding_text(self) -> str:
        return f"{self.document_title}. {self.section}. {self.content}"


def parse_policy(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, re.M).group(1).strip()
    meta = {k: re.search(rf"^{k}: (.+)$", text, re.M).group(1).strip() for k in ("Policy ID", "Category", "Version")}
    chunks = []
    for i, block in enumerate(re.split(r"^## ", text, flags=re.M)[1:]):
        heading, _, body = block.partition("\n")
        chunks.append(Chunk(f"{path.stem}-{i}", path.stem, title, meta["Policy ID"], meta["Category"], meta["Version"],
                            heading.strip(), " ".join(body.split())))
    return chunks


def load_all(directory: Path | None = None) -> list[Chunk]:
    return [c for p in sorted((directory or documents_dir()).glob("*.md")) for c in parse_policy(p)]
