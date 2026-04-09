# Reliability and Evaluation Report

**Wedding Planner AI — SE4471 Course Project, Deliverable 3**

---

## 1. System Overview

Wedding Planner AI is an end-to-end, AI-powered wedding planning assistant that generates personalized planning reports. The system implements a 6-step agentic workflow backed by a RAG pipeline (ChromaDB + SentenceTransformers), Google Gemini 2.5 Flash for LLM reasoning, live weather data from OpenWeatherMap, and email delivery via SendGrid.

**Core Pipeline:**
1. **State Persistence** — User inputs (guest count, budget, theme, date, venue type, dietary) are persisted to `event_state.json`
2. **RAG Retrieval** — A contextual query is built from the state and matched against 10 embedded wedding-planning documents using `all-MiniLM-L6-v2` embeddings in ChromaDB (top-k=3)
3. **Weather Fetch** — For outdoor venues, live weather and historical climate data for London, Ontario are fetched from OpenWeatherMap
4. **LLM-Grounded Conflict Detection** — Gemini evaluates the event state against retrieved documents and weather context to identify hard conflicts
5. **Conditional Branching & Artifact Generation** — If conflicts exist and are unacknowledged, the pipeline halts and returns clarification. Otherwise, Gemini generates a structured Markdown report with source citations
6. **Email Delivery** — The report is optionally emailed as styled HTML via SendGrid

---

## 2. Testing Strategy

### 2.1 Manual End-to-End Testing

We tested the system through **scenario-based manual testing** covering the full pipeline from form input to report output. Key test scenarios:

| # | Scenario | Expected Behavior | Result |
|---|----------|--------------------|--------|
| 1 | 60 guests, $6,000 budget, outdoor, August | No conflicts; full report generated | Pass |
| 2 | 120 guests, $5,000 budget, outdoor, January | Budget conflict + seasonal risk flagged | Pass |
| 3 | 50 guests, $10,000, indoor, no dietary | No conflicts; report generated without weather section | Pass |
| 4 | 80 guests, $7,500, outdoor, no date | Outdoor risk: missing date conflict | Pass |
| 5 | 40 guests, $1,500, Halal dietary | Per-head budget < $50 conflict flagged | Pass |
| 6 | Conflicts acknowledged via checkbox | Pipeline proceeds to artifact generation despite conflicts | Pass |
| 7 | Follow-up chat after report | Chat references actual event numbers and report content | Pass |
| 8 | Email delivery with valid SendGrid key | Report emailed as styled HTML | Pass |
| 9 | No Gemini API key set | Fallback to rule-based conflicts + static report template | Pass |

### 2.2 Component-Level Testing

- **RAG Retrieval**: Verified that queries mentioning "outdoor" retrieve `outdoor_guide.txt`; budget-related queries retrieve `budget_guide.txt`; dietary queries retrieve `catering_guide.txt`. Incremental ingestion was verified by adding a new `.txt` file and confirming it was embedded without re-indexing existing documents.
- **State Persistence**: Verified `event_state.json` updates correctly across sequential requests and retains prior fields when only partial updates are submitted.
- **Weather Module**: Tested with valid and missing API keys — confirmed graceful fallback when the key is absent. Verified monthly climate lookup for all 12 months.
- **Conflict Detection Fallback**: Disabled Gemini API key and confirmed all four rule-based checks trigger correctly (budget threshold, missing date for outdoor, winter seasonal risk, per-head catering cost).

### 2.3 Failure Injection Tests

| Failure | System Behavior |
|---------|-----------------|
| Gemini API key missing | Rule-based conflict fallback + static report template |
| Gemini returns overly verbose response (>4 conflicts) | Falls back to rule-based detection (over-flagging guard) |
| OpenWeatherMap API key missing | Weather section omitted; pipeline continues |
| SendGrid API key missing | Email step skipped silently; report still returned |
| Malformed event date | Date-dependent logic (weather, seasonal risk) skipped gracefully via try/except |
| Empty knowledge base | RAG returns no documents; report proceeds with available info |

---

## 3. Failure Cases and Limitations

### 3.1 Known Limitations

1. **Single-City Weather**: Weather data is hardcoded to London, Ontario. Events in other locations will receive irrelevant weather context for outdoor risk assessment.

2. **No User Authentication or Session Management**: The system uses a single shared `event_state.json` file. Concurrent users would overwrite each other's state. This is acceptable for a single-user demo but not production-ready.

3. **LLM Hallucination Risk**: While conflict detection prompts instruct Gemini to flag only "hard conflicts" backed by retrieved documents, the LLM may occasionally fabricate conflicts not grounded in the corpus. The over-flagging guard (>4 conflicts triggers fallback) mitigates this partially.

4. **Static Budget Chart**: The frontend budget breakdown doughnut chart uses hardcoded allocation percentages (52% food/venue, 12% photography, etc.) rather than deriving them from the LLM's report. This means the chart is illustrative, not dynamically tied to the generated recommendations.

5. **No Streaming**: The Gemini API call blocks until the full response is generated. For large reports, this can take 5-15 seconds with no intermediate feedback beyond the skeleton loader.

6. **Corpus Scope**: The 10-document knowledge base covers common wedding planning topics but lacks coverage for niche scenarios (e.g., destination weddings, multi-day events, cultural-specific traditions beyond dietary needs).

7. **Chat Context Window**: The follow-up chat endpoint loads the entire report + event state into the prompt each time. For very long reports, this could approach Gemini's context limits, though in practice our reports are well within bounds.

### 3.2 Edge Cases Handled

- **Empty or missing fields**: All state fields default gracefully (`"Not provided"` or `0`). The pipeline does not crash on partial input.
- **LLM failure**: Both conflict detection and artifact generation have deterministic fallbacks.
- **API timeout**: OpenWeatherMap requests have a 5-second timeout; failures are caught and logged.

---

## 4. Prompt and Workflow Design Decisions

### 4.1 Conflict Detection Prompt Design

The conflict detection prompt was iteratively refined to minimize false positives. Key design choices:

- **"Hard conflicts only" instruction**: The prompt explicitly lists what NOT to flag (missing optional info, style choices, speculative risks). This was added after early testing revealed Gemini flagged nearly every input with 5-8 "conflicts," most of which were subjective or ungrounded.
- **Structured output format**: The prompt requests one paragraph per conflict with (1) conflict name, (2) source citation, (3) specific numbers, (4) clarifying question. This makes conflicts actionable rather than vague.
- **Over-flagging guard**: If Gemini returns more than 4 conflicts, the system falls back to rule-based checks. This was a pragmatic safeguard against prompt injection or LLM over-enthusiasm.
- **NO_CONFLICTS sentinel**: The prompt instructs the LLM to respond with exactly `NO_CONFLICTS` when no issues are found, making parsing deterministic.

### 4.2 Report Generation Prompt Design

- **Source citation enforcement**: The prompt explicitly requires `*(Source: filename.txt)*` citations after each recommendation. This ensures the output is grounded in the retrieved documents rather than the LLM's general training data.
- **Structured sections**: The prompt specifies exactly 4 sections (Event Summary, Conflict Summary, Planning Recommendations, Suggested Next Actions) to ensure consistent, parseable output.
- **Tone control**: "Helpful and professional" with "specific numbers" instructions prevent generic or overly casual responses.

### 4.3 Workflow Branching

The conditional branch at Step 4 was a deliberate design choice. Rather than generating a report with unresolved conflicts buried inside it, the system **halts and surfaces conflicts** to the user, requiring explicit acknowledgment before proceeding. This prevents the common UX anti-pattern of delivering a report the user can't trust.

### 4.4 RAG Query Construction

Instead of using the raw user input as the query, the system constructs a composite query string from all state fields (e.g., `"wedding planning for 60 guests with budget 6000, theme: Garden, venue type: outdoor..."`). This multi-faceted query improves retrieval recall by matching across multiple document topics simultaneously.

---

## 5. Evidence of Retrieval Grounding

### 5.1 RAG Pipeline Architecture

- **Corpus**: 10 domain-specific `.txt` documents covering budget, catering, venues, photography, entertainment, flowers/decor, outdoor planning, timelines, vendor management, and guest management
- **Embedding Model**: `all-MiniLM-L6-v2` (384-dimensional sentence embeddings)
- **Vector Store**: ChromaDB with persistent storage; incremental ingestion skips already-embedded documents
- **Retrieval**: Top-3 documents by cosine similarity to the composite query

### 5.2 Grounding in Conflict Detection

The conflict detection prompt includes the full text of retrieved documents in a `## Retrieved Planning Documents` section. Each document is tagged with `[Source: filename.txt]`. The prompt instructs Gemini to reference "specific numeric thresholds or explicit requirements stated in the retrieved documents" — grounding conflict identification in the corpus rather than general knowledge.

**Example**: When a user enters 120 guests with a $5,000 budget, the system retrieves `budget_guide.txt` (which states "$8,000–$15,000 for 80–120 guests") and Gemini flags: *"Budget conflict: According to budget_guide.txt, a minimum of $8,000–$15,000 is typical for 80+ guests. Your budget of $5,000 for 120 guests falls significantly below this threshold."*

### 5.3 Grounding in Report Generation

The report generation prompt includes retrieved documents in a `## Retrieved Guidance` section and explicitly instructs: *"cite these sources in your recommendations."* Generated reports include citations like `*(Source: venue_guide.txt)*` after each recommendation, directly linking advice to the knowledge base.

### 5.4 Grounding in Follow-Up Chat

The chat endpoint loads both the persisted event state and the full generated report into the prompt context. This ensures follow-up answers reference the couple's actual numbers (e.g., "With your $6,000 budget for 60 guests...") rather than providing generic wedding advice.

### 5.5 Fallback Grounding

When the LLM is unavailable, the rule-based conflict checks use thresholds derived directly from the knowledge base documents (e.g., $8,000 minimum for 80+ guests from `budget_guide.txt`, $50/head from `catering_guide.txt`). The static fallback report includes raw retrieved document text, maintaining transparency about what the system knows.

---

## 6. External Tool Integration

| Tool | Purpose | Integration Point |
|------|---------|-------------------|
| **Google Gemini 2.5 Flash** | LLM reasoning for conflict detection, report generation, and follow-up chat | Steps 3, 5, and `/chat` endpoint |
| **ChromaDB** | Persistent vector database for semantic document retrieval | Step 2 (RAG pipeline) |
| **SentenceTransformers** | `all-MiniLM-L6-v2` embedding model for document and query encoding | Step 2 (RAG pipeline) |
| **OpenWeatherMap API** | Live current weather + historical climate data for outdoor venue risk | Step 2b |
| **SendGrid API** | HTML email delivery of the planning report | Step 6 |
| **Chart.js** | Budget breakdown doughnut chart visualization in the frontend | UI output panel |

---

## 7. Summary

Wedding Planner AI achieves **Tier 3 (Advanced System)** by implementing:
- A complete RAG pipeline with semantic retrieval over a 10-document corpus
- A 6-step agentic workflow with conditional branching and state tracking
- Multi-tool orchestration (Gemini LLM + ChromaDB + OpenWeatherMap + SendGrid)
- LLM-grounded conflict detection with deterministic fallbacks
- Structured Markdown artifact generation with source citations
- Follow-up conversational Q&A grounded in event context
- A polished, responsive single-page frontend with real-time feedback

The system demonstrates graceful degradation at every step, ensuring functionality even when external APIs are unavailable. Prompt engineering decisions were driven by iterative testing to minimize hallucination and maximize grounded, actionable output.
