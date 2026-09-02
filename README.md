# Agentic RAG

An enterprise-style, agentic retrieval-augmented generation (RAG) application for answering technical questions from a document collection. The project contains:

- A FastAPI backend that exposes the agent workflow.
- A Streamlit chat UI that calls the backend.
- A document ingestion pipeline for PDF, HTML, TXT, DOCX, and PPTX files.
- Local `sentence-transformers` embeddings, Qdrant vector search, FlashRank reranking, LangGraph orchestration, NeMo Guardrails, and Logfire/LangSmith observability.

## Workflow

```text
Documents in DATA/
				|
				v
Parse file -> chunk text -> save processed_data/<source_type>/ -> embed -> upsert to Qdrant
																																	|
User -> Streamlit UI -> POST /query -> NeMo Guardrails
																					 |
												 blocked/dialogue | technical question
																					 |                 |
																					 v                 v
																			response       LangGraph planner
																													 |
																			conversational <-----+-----> retriever
																					 |                         |
																					 +------ responder <--------+
																												|
																												v
																							 answer returned to UI
```

For a technical question, the planner creates a search query, Qdrant returns up to 15 candidates, FlashRank keeps the top 5 chunks, and the responder synthesizes the answer. Each UI session sends a `thread_id`, which enables LangGraph's in-memory conversation checkpointing.

## Requirements

- Windows, macOS, or Linux
- Python 3.10+ recommended
- A reachable Qdrant Cloud instance and API key
- API credentials for the configured LLM gateway/provider
- Internet access on the first run so `sentence-transformers` can download `all-mpnet-base-v2`

## Setup

Run these commands from the repository root (`Agentic_RAG`). The commands below use PowerShell on Windows.

```powershell
python -m venv tenv
.\tenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, activate the environment in Command Prompt instead:

```bat
tenv\Scripts\activate.bat
```

Create a root `.env` file. Do not commit it or place credentials in source code. The application reads these variables:

```dotenv
# LLM gateway and providers
GROQ_API_KEY=replace-with-your-key
GROQ_FALLBACK_API_KEY=replace-with-your-fallback-key
PORTKEY_API_KEY=replace-with-your-portkey-key

# Qdrant Cloud
QDRANT_CLUSTER_ENDPOINT=https://your-cluster.region.aws.cloud.qdrant.io
QDRANT_API_KEY=replace-with-your-qdrant-key

# Optional observability
LOGFIRE_TOKEN=
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=agentic-rag
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# Used by the Streamlit UI; defaults to the local API
BACKEND_URL=http://localhost:8000
```

The Qdrant collection is created automatically as `enterprise_rag`. Its vector size is resolved from the configured embedding model (`all-mpnet-base-v2`, 768 dimensions).

## Ingest Documents

Place source documents in `DATA/`. The included layout uses `DATA/true_data` and `DATA/noisy`; folder names are converted into the `source_type` payload field.

Ingest all documents and create the collection if it does not exist:

```powershell
python -m app.ingestion.processor DATA
```

Delete and recreate the Qdrant collection, then ingest everything from scratch:

```powershell
python -m app.ingestion.processor DATA --wipe
```

Ingest one directory and explicitly assign its source type:

```powershell
python -m app.ingestion.processor DATA/true_data true
python -m app.ingestion.processor DATA/noisy_data noisy
```

Supported extensions are `.pdf`, `.html`, `.htm`, `.txt`, `.docx`, and `.pptx`. Parsed chunks are also written locally under `processed_data/<source_type>/` for inspection. `processed_data/` is ignored by Git.

Important: `--wipe` is destructive for the configured Qdrant collection. Use it when rebuilding the index, not during normal incremental ingestion.

## Run the Backend

Keep the virtual environment active and start FastAPI with Uvicorn:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at:

- `GET http://localhost:8000/` - liveness response
- `GET http://localhost:8000/docs` - interactive Swagger documentation
- `GET http://localhost:8000/graph` - PNG rendering of the LangGraph workflow
- `POST http://localhost:8000/query` - execute a query

Example request from a second PowerShell window:

```powershell
Invoke-RestMethod `
	-Uri http://localhost:8000/query `
	-Method Post `
	-ContentType "application/json" `
	-Body '{"q":"How does the documented system handle autoscaling?","thread_id":"local-user"}'
```

The response contains `question`, `answer`, `thought_process`, `status`, and `sources`.

## Run the Streamlit UI

Start the backend first, then run the UI in another terminal:

```powershell
.\tenv\Scripts\Activate.ps1
streamlit run ui/app.py
```

Open the URL printed by Streamlit, normally `http://localhost:8501`. The UI uses `BACKEND_URL` from `.env`, or `http://localhost:8000` when it is not set.

For the Streamlit Cloud-oriented entry point, use:

```powershell
streamlit run ui/st_cloud_ui.py
```

## Production Server Commands

For a single-process server without the development reloader:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For a Linux deployment, the equivalent commands are:

```bash
python3 -m venv tenv
source tenv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run the ingestion job as a deployment/preparation step before serving queries. The API process and Streamlit process are separate services, so configure the UI service's `BACKEND_URL` to the public or internal URL of the API.

## Folder Guide

| Path | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI application, lifecycle initialization, `/query`, `/graph`, and health endpoint. |
| `app/config.py` | Loads environment variables and defines model, Qdrant, gateway, and tracing settings. |
| `app/agents/graph.py` | Defines and compiles the LangGraph planner -> retriever -> responder workflow with memory. |
| `app/agents/state.py` | Typed state passed between graph nodes. |
| `app/agents/node/` | The planner, retrieval, and answer-generation implementations. |
| `app/agents/nodes/` | Compatibility exports for the node implementations. |
| `app/ingestion/processor.py` | CLI ingestion entry point: parse, chunk, persist metadata, embed, and index. |
| `app/ingestion/loaders/` | Parsers for PDF, HTML, text, and office documents. |
| `app/ingestion/chunking/` | Text chunking logic used before embedding. |
| `app/services/retrieval/` | Embedding, Qdrant search, and semantic reranking services. |
| `app/gateway/` | LLM gateway setup and provider/fallback routing. |
| `app/guardrails/` | NeMo Guardrails initialization and request safety/dialogue handling. |
| `ui/app.py` | Local Streamlit chat client. |
| `ui/st_cloud_ui.py` | Streamlit Cloud-oriented chat client. |
| `DATA/` | Source documents to ingest, split into `true_data` and `noisy_data`. |
| `processed_data/` | Generated parsed/chunked JSON metadata; ignored by Git. |
| `requirements.txt` | Python runtime dependencies. |

## Troubleshooting

- **Backend Offline in Streamlit:** confirm Uvicorn is running and that `BACKEND_URL` points to the API without a trailing path such as `/query`.
- **Qdrant errors:** verify both `QDRANT_CLUSTER_ENDPOINT` and `QDRANT_API_KEY`; run ingestion with `--wipe` only when rebuilding the collection.
- **Empty retrieval results:** confirm ingestion completed successfully and that the Qdrant collection is `enterprise_rag`.
- **Model download errors:** ensure the machine has internet access and enough disk space for `all-mpnet-base-v2`.
- **LLM failures:** verify the gateway/provider credentials and inspect Logfire or application logs.

## Security Notes

- Treat all API keys and tracing tokens as secrets. Use deployment secret management rather than committing `.env`.
- If credentials have ever been shared, committed, or exposed, revoke and rotate them before deployment.
- Restrict the production API behind authentication, TLS, and an appropriate network boundary. The current FastAPI app does not implement user authentication.

