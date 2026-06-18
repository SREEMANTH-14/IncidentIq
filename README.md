# IncidentIQ

AI-powered DevOps incident triage and resolution.

## Use Case

IncidentIQ accepts a production incident payload, classifies severity, retrieves similar past incidents and runbooks using RAG, proposes remediation steps, invokes mocked DevOps tools for safe actions, and returns a Slack/email-ready incident response.

## Tech Stack

- Python 3.11+
- FastAPI + Uvicorn
- LangChain + LangGraph
- ChromaDB embedded persistent vector store
- sentence-transformers/all-MiniLM-L6-v2 embeddings
- Pydantic v2
- Docker + docker-compose
- OpenAI / Ollama / Mock LLM provider

## Required Endpoints

- `GET /health`
- `POST /process`
- `GET /incidents/{incident_id}`

## Agent Roles

- Orchestrator
- Triage Agent
- Knowledge Agent
- Remediation Agent
- Notifier Agent

## Current Status

Step 1 completed:

- Project structure created
- Dependencies listed
- Environment template added