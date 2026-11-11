# Enterprise RBAC Chatbot

An enterprise knowledge assistant built with **Streamlit, LangChain, Groq, Qdrant, Hugging Face embeddings, and document-level Role-Based Access Control (RBAC)**.

The application authenticates employees, retrieves only documents permitted for their effective roles, and uses a large language model to generate answers from the authorized context. The Kubernetes deployment is maintained separately in the [Enterprise-RBAC-Chatbot-GitOps](https://github.com/shaikh4git/Enterprise-RBAC-Chatbot-GitOps) repository.

## Project overview

The chatbot follows a Retrieval-Augmented Generation (RAG) workflow:

1. An employee signs in with a username and password.
2. The application validates the password against a bcrypt hash in the user directory.
3. The user's effective roles are calculated from their assigned roles and department.
4. The question is embedded and searched against the Qdrant vector collection.
5. A Qdrant metadata filter restricts retrieval to documents whose `allowed_roles` match the user's effective roles.
6. Retrieved content is sent to the Groq-hosted language model with instructions to answer only from the supplied context.
7. Output guardrails check for selected sensitive identifiers before the answer and source names are displayed.

**Authorization is enforced during retrieval, not just by the LLM prompt.** The application also performs a second document-level access check after retrieval.

## Architecture

```text
                         Employee
                            |
                            v
                    Streamlit Web UI
                       (port 8505)
                            |
                            v
                  Authentication (bcrypt)
                            |
                            v
                   Effective User Roles
                            |
                            v
                     User Question
                            |
                            v
                 Hugging Face Embeddings
                            |
                            v
                    Qdrant Vector DB
                 (role-filtered retrieval)
                            |
                            v
                 Authorized Document Chunks
                            |
                            v
                     Groq LLM API
                            |
                            v
                   Output Guardrails
                            |
                            v
                 Answer + Source References
```

### Technology stack

| Component | Technology | Purpose |
|---|---|---|
| User interface | Streamlit | Employee login and conversational interface |
| Authentication | Python, bcrypt | Password-hash verification |
| Authorization | Custom Python RBAC | Department and role-based document access |
| Document extraction | Docling | Extract content from supported office and PDF files |
| Text processing | LangChain text splitters | Split documents into overlapping chunks |
| Embeddings | Hugging Face Sentence Transformers | Convert text into vectors |
| Vector database | Qdrant | Store and search document vectors and metadata |
| LLM integration | LangChain Groq | Generate context-grounded answers |
| Containerization | Docker | Package the application |
| Orchestration / GitOps | Kubernetes, Argo CD | Deploy and reconcile application resources |
| Progressive delivery | Argo Rollouts | Canary release strategy in the GitOps repository |

## Repository structure

The application repository is organized around the following components:

```text
Enterprise-RBAC-Chatbot/
├── app/
│   ├── app.py              # Streamlit frontend and employee session
│   ├── auth.py             # bcrypt authentication and user loading
│   ├── rbac.py             # Effective roles and document authorization
│   ├── chatbot.py          # Qdrant retrieval and Groq response generation
│   ├── guardrails.py       # Sensitive-identifier output checks
│   └── ingest_docs.py      # Document extraction, chunking and indexing
├── documents/
│   ├── General/            # General employee documents
│   ├── Finance/            # Finance-authorized documents
│   ├── HR/                 # HR-authorized documents
│   └── ...                 # Add folders for other departments/roles
├── Dockerfile
├── requirements.txt
└── README.md
```

The document folders are expected under the repository root. Keep confidential source documents and user credential files out of public Git history.

## Role-Based Access Control

The current RBAC implementation derives effective roles from:

- Roles explicitly assigned to the authenticated user.
- The user's department.
- The baseline `Employee` role, which is automatically included.

The ingestion script assigns document access metadata based on the document's parent folder:

| Document folder | Allowed roles assigned by ingestion |
|---|---|
| `General/` | `Employee`, `C-Level` |
| `Finance/` | `Finance`, `C-Level` |
| `HR/` | `HR`, `C-Level` |
| Any other department folder | Folder name as role, `C-Level` |

Documents without explicit `allowed_roles` metadata are denied by the application-level authorization check.

### Example user-directory structure

The application currently reads the user directory as JSON from the `CHATBOT_USERS_JSON` environment variable. Each password must be a bcrypt hash; do not store plaintext passwords.

```json
{
  "finance.alice": {
    "password_hash": "$2b$12$REPLACE_WITH_A_REAL_BCRYPT_HASH",
    "department": "Finance",
    "roles": ["Finance"]
  },
  "hr.bob": {
    "password_hash": "$2b$12$REPLACE_WITH_A_REAL_BCRYPT_HASH",
    "department": "HR",
    "roles": ["HR"]
  }
}
```

This is a schema example only. Replace the placeholder hashes with real bcrypt hashes and provide the JSON through a protected secret.

## Document ingestion

The ingestion script is `app/ingest_docs.py`. It scans the root `documents/` directory recursively and currently supports:

- PDF
- DOCX
- PPTX
- Markdown (`.md`)
- Plain text (`.txt`)

Docling extracts content from PDF and office documents. Markdown and text files are read directly. The text splitter uses a chunk size of 900 characters and an overlap of 120 characters. Each chunk retains metadata including its relative source path, department, and `allowed_roles`.

### Ingest documents into Qdrant

1. Start a Qdrant instance. For local development:

   ```bash
   docker run -d \
     --name qdrant \
     -p 6333:6333 \
     -p 6334:6334 \
     qdrant/qdrant
   ```

2. Place documents under their corresponding department folders in `documents/`.

3. Install the Python dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   ```

4. Configure the Qdrant connection if it is not using the local default:

   ```bash
   export QDRANT_URL="http://localhost:6333"
   export QDRANT_COLLECTION="company_docs"
   ```

5. Run ingestion from the repository root:

   ```bash
   python app/ingest_docs.py
   ```

The script prints the number of chunks ingested when it completes successfully.

> **Important:** The current ingestion implementation uses Qdrant's `force_recreate=True`. This recreates the target collection and replaces its existing contents. Treat this as a development workflow; do not run it against a production collection without a deliberate backup and re-indexing plan.

## Run the chatbot locally

Start Qdrant as described above, then configure the required environment variables.

| Variable | Purpose | Default / requirement |
|---|---|---|
| `GROQ_API_KEY` | Authenticates requests to Groq | Required |
| `CHATBOT_USERS_JSON` | JSON user directory with bcrypt password hashes | Required |
| `QDRANT_URL` | Qdrant endpoint | `http://localhost:6333` |
| `QDRANT_COLLECTION` | Vector collection name | `company_docs` |
| `EMBEDDING_MODEL` | Hugging Face embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `GROQ_MODEL` | Groq model identifier | `openai/gpt-oss-20b` |

Example for a local development session:

```bash
export GROQ_API_KEY="your-groq-api-key"
export CHATBOT_USERS_JSON="$(cat users.json)"
export QDRANT_URL="http://localhost:6333"
export QDRANT_COLLECTION="company_docs"

streamlit run app/app.py \
  --server.address=0.0.0.0 \
  --server.port=8505
```

Open [http://localhost:8505](http://localhost:8505) in your browser.

Do not commit `users.json`, API keys, passwords, or other secret material. Use a local environment file excluded by Git or a secrets manager for development, and Kubernetes Secrets for cluster deployments.

## Build and run with Docker

The repository includes a Dockerfile that:

- Uses Python 3.11 slim as its base image.
- Installs CPU-only PyTorch and the Python requirements.
- Runs Streamlit on port 8505.
- Creates and runs as a non-root user (UID 10001).

Build the image:

```bash
docker build -t enterprise-rbac-chatbot:local .
```

Run it (assuming Qdrant is reachable from the container and the required secrets are supplied):

```bash
docker run --rm -p 8505:8505 \
  -e GROQ_API_KEY="$GROQ_API_KEY" \
  -e CHATBOT_USERS_JSON="$CHATBOT_USERS_JSON" \
  -e QDRANT_URL="http://host.docker.internal:6333" \
  enterprise-rbac-chatbot:local
```

The container listens on port `8505`.

## Kubernetes and GitOps deployment

Deployment manifests and Argo CD configuration are maintained in the separate [Enterprise-RBAC-Chatbot-GitOps](https://github.com/shaikh4git/Enterprise-RBAC-Chatbot-GitOps) repository.

The current GitOps configuration includes:

- An Argo CD Application named `enterprise-rbac-chatbot`.
- Deployment resources in the `enterprise-chatbot` namespace.
- Qdrant deployment, service, and persistent-volume claim resources.
- A ConfigMap for non-sensitive application configuration.
- A Kubernetes Secret reference named `chatbot-secrets`.
- An Argo Rollouts canary strategy with a 50% traffic step, a manual pause, and then 100%.

The Argo CD Application watches the GitOps repository's `app/` path and targets the in-cluster Kubernetes API. Automated sync, pruning, and self-healing are enabled in its current manifest.

### Repository responsibilities

| Repository | Responsibility |
|---|---|
| [Enterprise-RBAC-Chatbot](https://github.com/shaikh4git/Enterprise-RBAC-Chatbot) | Application source code, dependencies, Docker image build |
| [Enterprise-RBAC-Chatbot-GitOps](https://github.com/shaikh4git/Enterprise-RBAC-Chatbot-GitOps) | Kubernetes manifests, Argo CD application, rollout and deployment configuration |

The GitOps repository references the application image `shaikhdocker/enterprise-rbac-chatbot`. Update its image tag in the GitOps Kustomize configuration when promoting a newly built application image.

Create the Kubernetes Secret separately; do not store secret values in a ConfigMap or commit a populated Secret manifest:

```bash
kubectl create secret generic chatbot-secrets \
  -n enterprise-chatbot \
  --from-literal=GROQ_API_KEY="$GROQ_API_KEY" \
  --from-file=CHATBOT_USERS_JSON=./users.json \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Security considerations and limitations

This repository demonstrates enterprise-style access control, but it should be security-reviewed before handling real confidential or regulated data.

- Use TLS and appropriate network policies for application-to-Qdrant communication.
- Restrict access to Qdrant and its administrative endpoints.
- Store API keys and user directories in a secrets manager or Kubernetes Secret; restrict who can read those secrets.
- Use strong, unique passwords and securely generated bcrypt hashes.
- Review department-to-role mappings and document metadata whenever new departments or roles are introduced.
- The current sensitive-identifier checks are basic pattern matching for US Social Security Number-like values and credit-card-like numbers. They are not comprehensive DLP or PII protection.
- The LLM prompt is a behavioral instruction, not an authorization boundary. Continue enforcing access before context reaches the model.
- Retrieved documents are untrusted input. Test against prompt injection, data exfiltration, and cross-department retrieval attempts.
- The ingestion script currently recreates the Qdrant collection; implement safe incremental indexing and backup/restore before production use.
- Add automated tests for authentication, role inheritance, document filtering, and output guardrails before production rollout.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Login fails | Confirm `CHATBOT_USERS_JSON` is valid JSON, usernames match, and password hashes are valid bcrypt hashes. |
| Qdrant connection error | Check that Qdrant is running and `QDRANT_URL` is reachable from the application/container. |
| No authorized documents found | Check ingestion completion, collection name, folder names, and each chunk's `allowed_roles` metadata. |
| Groq request fails | Confirm `GROQ_API_KEY`, model availability, and outbound connectivity. |
| Model downloads are slow | The Hugging Face embedding model may need to be downloaded and cached on first use. |

## License

No license is currently specified in this repository. All rights remain with the repository owner unless a license is added.
