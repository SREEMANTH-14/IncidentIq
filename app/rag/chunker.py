import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("IncidentIQ.RAG.Chunker")


@dataclass(slots=True)
class SourceDocument:
    """
    SourceDocument represents one raw knowledge document before chunking.

    """

    source_id: str
    source_type: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RAGChunk:
    """
    RAGChunk represents one chunk that will be embedded and stored in ChromaDB.

    The Knowledge Agent will retrieve these chunks later for grounded answers.
    """

    chunk_id: str
    source_id: str
    source_type: str
    title: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_chroma_metadata(self) -> dict[str, str]:
        """
        Converts chunk metadata into a ChromaDB-safe metadata dictionary.

        ChromaDB metadata values should be simple scalar values.
        To keep this stable, we convert metadata values to strings.
        """

        chroma_metadata: dict[str, str] = {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "chunk_index": str(self.chunk_index),
        }

        for key, value in self.metadata.items():
            if value is None:
                continue

            metadata_key = str(key)
            metadata_value = str(value)
            chroma_metadata[metadata_key] = metadata_value

        return chroma_metadata


def split_text_with_overlap(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """
    Splits text into overlapping chunks.

    Example:
    chunk_size = 800
    chunk_overlap = 120

    This means each new chunk starts 120 characters before the previous
    chunk ended. Overlap helps preserve context between chunks.
    """

    cleaned_text = text.strip()

    if not cleaned_text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    chunks: list[str] = []
    start_index = 0
    text_length = len(cleaned_text)

    while start_index < text_length:
        end_index = start_index + chunk_size
        chunk_text = cleaned_text[start_index:end_index].strip()

        if chunk_text:
            chunks.append(chunk_text)

        if end_index >= text_length:
            break

        start_index = end_index - chunk_overlap

    return chunks


def create_chunks_from_document(
    document: SourceDocument,
    chunk_size: int,
    chunk_overlap: int,
) -> list[RAGChunk]:
    """
    Creates RAG chunks from one SourceDocument.

    The generated chunk_id is deterministic so repeated ingestion can update
    the same ChromaDB records.
    """

    text_chunks = split_text_with_overlap(
        text=document.content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    rag_chunks: list[RAGChunk] = []

    for index, chunk_text in enumerate(text_chunks, start=1):
        chunk_id = f"{document.source_id}-chunk-{index}"

        rag_chunk = RAGChunk(
            chunk_id=chunk_id,
            source_id=document.source_id,
            source_type=document.source_type,
            title=document.title,
            content=chunk_text,
            chunk_index=index,
            metadata=document.metadata,
        )

        rag_chunks.append(rag_chunk)

    logger.info(
        "Created %s chunks for source_id=%s source_type=%s",
        len(rag_chunks),
        document.source_id,
        document.source_type,
    )

    return rag_chunks


def create_chunks_from_documents(
    documents: list[SourceDocument],
    chunk_size: int,
    chunk_overlap: int,
) -> list[RAGChunk]:
    """
    Creates RAG chunks from multiple SourceDocument objects.
    """

    all_chunks: list[RAGChunk] = []

    for document in documents:
        document_chunks = create_chunks_from_document(
            document=document,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        all_chunks.extend(document_chunks)

    logger.info("Total RAG chunks created: %s", len(all_chunks))

    return all_chunks
