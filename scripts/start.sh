#!/usr/bin/env bash

set -e

echo "Starting IncidentIQ container..."

echo "Creating required directories..."
mkdir -p data/incidents
mkdir -p data/runbooks
mkdir -p storage/chroma

if [ "${AUTO_GENERATE_DATA}" = "true" ]; then
    echo "Generating IncidentIQ synthetic data..."
    python generate_data.py
else
    echo "Skipping data generation because AUTO_GENERATE_DATA is not true."
fi

if [ "${AUTO_INGEST_RAG}" = "true" ]; then
    echo "Ingesting IncidentIQ RAG corpus into ChromaDB..."
    python -m app.rag.ingest
else
    echo "Skipping RAG ingestion because AUTO_INGEST_RAG is not true."
fi

echo "Starting FastAPI application..."
exec uvicorn app.main:app --host "${API_HOST}" --port "${API_PORT}"