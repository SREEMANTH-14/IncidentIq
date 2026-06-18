import logging

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer
import torch

from app.core.config import ConfigSettings, get_settings
from app.rag.chunker import RAGChunk

logger = logging.getLogger("IncidentIQ.RAG.VectorStore")


class IncidentIQVectorStore:
    """
    IncidentIQVectorStore manages the embedded persistent ChromaDB collection.

    This class is responsible for:
    - Loading the sentence-transformers embedding model
    - Creating or loading the ChromaDB collection
    - Storing RAG chunks with embeddings
    - Returning collection statistics
    """

    def __init__(self, settings: ConfigSettings | None = None) -> None:
        """
        Initializes ChromaDB client and embedding model.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

        self.settings.create_required_directories()

        chroma_path = self.settings.get_chroma_persist_path()

        self.client = chromadb.PersistentClient(path=str(chroma_path))

        self.collection = self.client.get_or_create_collection(
            name=self.settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.embedding_model = SentenceTransformer(self.settings.embedding_model_name, device=device)

        logger.info(
            "IncidentIQVectorStore initialized with collection=%s path=%s",
            self.settings.chroma_collection_name,
            chroma_path,
        )

    def reset_collection(self) -> None:
        """
        Deletes and recreates the ChromaDB collection.

        This is useful during local development because it avoids duplicate
        or stale RAG records.
        """

        try:
            self.client.delete_collection(name=self.settings.chroma_collection_name)
            logger.info(
                "Deleted existing ChromaDB collection: %s",
                self.settings.chroma_collection_name,
            )
        except Exception as error:
            logger.info(
                "No existing ChromaDB collection deleted. Reason: %s",
                str(error),
            )

        self.collection = self.client.get_or_create_collection(
            name=self.settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "Recreated ChromaDB collection: %s",
            self.settings.chroma_collection_name,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Converts text chunks into embedding vectors using SentenceTransformer.

        normalize_embeddings=True is useful for cosine similarity search.
        """

        if not texts:
            return []

        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
        )

        embedding_list = embeddings.tolist()
        return embedding_list

    def add_chunks(self, chunks: list[RAGChunk]) -> int:
        """
        Stores RAG chunks in ChromaDB.

        Uses upsert instead of add so repeated ingestion can safely update
        existing chunk IDs.
        """

        if not chunks:
            logger.warning("No chunks provided for ChromaDB ingestion.")
            return 0

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str]] = []

        for chunk in chunks:
            ids.append(chunk.chunk_id)
            documents.append(chunk.content)
            metadatas.append(chunk.to_chroma_metadata())

        embeddings = self.embed_texts(documents)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        logger.info("Upserted %s chunks into ChromaDB.", len(chunks))

        return len(chunks)

    def get_collection(self) -> Collection:
        """
        Returns the active ChromaDB collection.
        """

        return self.collection

    def get_collection_count(self) -> int:
        """
        Returns the number of records stored in the ChromaDB collection.
        """

        count = self.collection.count()
        return count
