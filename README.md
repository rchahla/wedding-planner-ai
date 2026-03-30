# Wedding Planner AI — SE4471 Deliverable 2

An end-to-end AI wedding planning assistant built with a RAG pipeline, multi-step agentic workflow, structured state tracking, and Markdown artifact generation.

---

## System Requirements

- Python 3.10 or higher
- A Gemini API key (free at https://aistudio.google.com)

---

## Project Structure

```
wedding-planner-ai/
├── backend/
│   ├── app.py                  # Flask app and routes
│   ├── workflow.py             # Multi-step pipeline logic
│   ├── rag.py                  # ChromaDB ingestion and retrieval
│   ├── state.py                # Event state persistence
│   ├── artifact_generator.py   # Gemini LLM report generation
│   └── templates/
│       └── index.html          # Web UI form
├── data/
│   ├── source_docs/            # 10 knowledge base documents (.txt)
│   ├── chroma_db/              # ChromaDB vector store (auto-created)
│   └── event_state.json        # Persisted event state (auto-created)
├── outputs/
│   └── wedding_report.md       # Generated artifact (auto-created)
├── .env                        # Your API key (you create this)
├── .env.example                # Template showing required variables
└── requirements.txt
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd wedding-planner-ai
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scriptsctivate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install flask==3.1.3 chromadb==1.5.5 sentence-transformers==5.3.0 google-genai==1.69.0 python-dotenv==1.2.2
```

### 4. Create your .env file

In the project root, create a file named `.env`:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Get a free Gemini API key at https://aistudio.google.com

### 5. Run the application

```bash
cd backend
python app.py
```

### 6. Open the web UI

Navigate to http://localhost:5000 in your browser.

---

## How to Use

Fill in the form with event details (guest count, budget, theme, date, venue type, dietary requirements) and click **Generate Plan**.

- If conflicts are detected, the system returns a clarification response listing each issue before generating a report.
- Tick **"I have reviewed any conflicts..."** and resubmit to proceed to the full planning report.
- The Markdown report is also saved to `outputs/wedding_report.md`.

---

## How the Pipeline Works

```
[Form submission]
      |
[Step 1] Save structured event state -> data/event_state.json
      |
[Step 2] Build contextual query from state -> retrieve top 3 docs from ChromaDB
      |
[Step 3] Detect conflicts (budget, seasonal risk, catering per-head)
      |
[Step 4] Conflicts found -> return clarification response (stop here)
         No conflicts   -> continue
      |
[Step 5] Generate Markdown artifact via Gemini (grounded in retrieved docs)
```

---

## Core Components

| Component | Implementation |
|---|---|
| **RAG Pipeline** | 10 .txt documents ingested into ChromaDB using all-MiniLM-L6-v2 embeddings. Retrieved at query time via semantic search. |
| **Multi-Step Workflow** | 5 explicit steps in workflow.py. Branches conditionally on conflict detection before artifact generation. |
| **State Tracking** | 6 event fields persisted to data/event_state.json. State drives retrieval query, conflict checks, and LLM prompt. |
| **Structured Artifact** | Gemini generates a Markdown report with Event Summary, Conflict Summary, Planning Recommendations (with source citations), and Next Actions. |

---

## Knowledge Base (10 Documents)

| File | Content |
|---|---|
| budget_guide.txt | Budget ranges by guest count |
| catering_guide.txt | Dietary requirements and catering planning |
| outdoor_guide.txt | Weather backup and seasonal risks |
| venue_guide.txt | Venue types, capacity, booking timelines |
| photography_guide.txt | Photographer packages and pricing |
| music_entertainment_guide.txt | DJ vs band costs and logistics |
| flowers_decor_guide.txt | Floral budgets and seasonal pricing |
| timeline_guide.txt | Day-of schedule structure |
| vendor_checklist.txt | Core vendors and contract guidance |
| guest_management_guide.txt | RSVP timelines and guest count impact |

---

## Troubleshooting

**ModuleNotFoundError** — Ensure your virtual environment is activated before running python app.py.

**GEMINI_API_KEY not found** — Ensure .env is in the project root (wedding-planner-ai/), not inside backend/.

**Report falls back to static template** — The Gemini API call failed. Check your API key and internet connection.

**ChromaDB only has old documents** — New .txt files added to source_docs/ are ingested incrementally on the next request.
