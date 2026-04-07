from state import update_state
from rag import ingest_documents, retrieve_relevant_docs
from artifact_generator import generate_markdown_report, generate_with_gemini
from weather import get_weather_context
from emailer import send_report_email


def detect_conflicts_llm(state, retrieved_docs, weather_context=None):
    """
    Step 3: Use Gemini to reason over retrieved documents against the event state
    and identify conflicts. Returns a list of conflict strings.
    Falls back to rule-based checks if the LLM call fails.
    """
    guest_count = state.get("guest_count", 0)
    budget = state.get("budget", 0)
    venue_type = state.get("venue_type", "")
    dietary = state.get("dietary", "")
    date = state.get("date", "")

    context_block = "\n\n".join(
        f"[Source: {doc['source']}]\n{doc['text']}" for doc in retrieved_docs
    )

    weather_section = ""
    if weather_context:
        weather_section = f"\n## Live Weather Data (London, Ontario)\n{weather_context}\n"

    prompt = f"""You are a wedding planning advisor. Review the event details below against the retrieved planning documents and identify any conflicts, risks, or constraint violations.

## Event Details
- Guest Count: {guest_count}
- Budget: ${budget}
- Theme: {state.get("theme", "Not provided")}
- Event Date: {date if date else "Not provided"}
- Venue Type: {venue_type if venue_type else "Not provided"}
- Dietary Requirements: {dietary if dietary else "None specified"}
{weather_section}
## Retrieved Planning Documents
{context_block}

## Task
Identify ONLY hard conflicts — situations where the provided event details definitively violate a specific numeric threshold or explicit requirement stated in the retrieved documents.

DO NOT flag:
- Missing optional information (e.g., venue capacity not provided)
- Budget percentages or breakdowns that are guidelines, not hard limits
- Style or aesthetic choices (e.g., theme vs venue type compatibility)
- Speculative risks about unknowns not present in the event details
- Situations where the event details fall within the stated feasible range

A conflict must meet ALL of these criteria:
1. There is a specific number or rule in the retrieved documents
2. The provided event details explicitly violate that rule
3. The violation cannot be resolved by information the user has not provided

For each hard conflict found, write one short paragraph that:
1. Names the conflict clearly
2. References the specific source document it comes from (e.g., "According to budget_guide.txt...")
3. States the specific numbers involved
4. Asks a focused clarifying question

If there are NO hard conflicts, respond with exactly: NO_CONFLICTS

Respond ONLY with the conflict paragraphs (one per line, separated by blank lines) or NO_CONFLICTS. No headers, no numbering, no extra commentary."""

    llm_response = generate_with_gemini(prompt)

    if not llm_response or llm_response.startswith("Error"):
        return _fallback_rule_conflicts(state)

    llm_response = llm_response.strip()
    if llm_response == "NO_CONFLICTS":
        return []

    conflicts = [p.strip() for p in llm_response.split("\n\n") if p.strip()]
    if len(conflicts) > 4:
        # LLM is over-flagging — fall back to rule-based checks
        return _fallback_rule_conflicts(state)
    return conflicts


def _fallback_rule_conflicts(state):
    """Hardcoded rule-based fallback if the LLM is unavailable."""
    conflicts = []
    guest_count = state.get("guest_count", 0)
    budget = state.get("budget", 0)
    venue_type = state.get("venue_type", "")
    dietary = state.get("dietary", "")
    date = state.get("date", "")

    if guest_count > 80 and budget < 8000:
        conflicts.append(
            f"Budget conflict: Your budget is ${budget} for {guest_count} guests. "
            "According to budget_guide.txt, a minimum of $8,000 to $15,000 is typical for 80+ guests. "
            "Would you like to increase your budget or reduce the guest count?"
        )
    if "outdoor" in venue_type.lower() and not date:
        conflicts.append(
            "Outdoor venue risk: You selected an outdoor venue but did not provide an event date. "
            "According to outdoor_guide.txt, seasonal weather risks cannot be assessed without a date. "
            "Please provide your event date so weather and backup planning can be evaluated."
        )
    if "outdoor" in venue_type.lower() and date:
        try:
            month = int(date.split("-")[1])
            if month in [11, 12, 1, 2]:
                conflicts.append(
                    f"Seasonal risk: Your outdoor event is in month {month}, which falls in a cold or winter period. "
                    "According to outdoor_guide.txt, weather backup planning such as tent rentals and covered seating is recommended. "
                    "Do you have a backup indoor option or tent rental arranged?"
                )
        except (IndexError, ValueError):
            pass
    if dietary and budget > 0 and guest_count > 0:
        per_head = budget / guest_count if guest_count else 0
        if per_head < 50:
            conflicts.append(
                f"Catering risk: Your per-head budget is approximately ${per_head:.0f}. "
                f"According to catering_guide.txt, accommodating dietary requirements ({dietary}) typically requires higher-cost catering. "
                "Consider allocating more budget to catering or confirming your caterer can meet these needs."
            )
    return conflicts


def run_workflow(user_input):
    acknowledged = user_input.pop("acknowledged", False)
    email = user_input.pop("email", "")

    # Step 1: Save state
    print("[Step 1] Saving event state...")
    state = update_state(user_input)

    guest_count = state.get("guest_count", 0)
    budget = state.get("budget", 0)
    theme = state.get("theme", "")
    date = state.get("date", "")
    venue_type = state.get("venue_type", "")
    dietary = state.get("dietary", "")

    # Step 2: Retrieve relevant documents using full context
    print("[Step 2] Retrieving relevant documents from knowledge base...")
    ingest_documents()
    query_parts = [f"wedding planning for {guest_count} guests with budget {budget}"]
    if theme:
        query_parts.append(f"theme: {theme}")
    if venue_type:
        query_parts.append(f"venue type: {venue_type}")
    if dietary:
        query_parts.append(f"dietary requirements: {dietary}")
    if date:
        query_parts.append(f"event date: {date}")
    query = " ".join(query_parts)
    retrieved_docs = retrieve_relevant_docs(query, top_k=3)

    # Step 2b: Fetch live weather context for outdoor venues
    weather_context = None
    if "outdoor" in venue_type.lower():
        print("[Step 2b] Fetching live weather data for London, Ontario...")
        weather_context = get_weather_context(date)
        if weather_context:
            print(f"[Step 2b] Weather context acquired.")

    # Step 3: Detect conflicts against retrieved guidance using LLM + RAG
    print("[Step 3] Checking for conflicts against retrieved guidance (LLM-grounded)...")
    conflicts = detect_conflicts_llm(state, retrieved_docs, weather_context)

    # Step 4: Branch — if conflicts exist and not yet acknowledged, return clarification
    if conflicts and not acknowledged:
        print("[Step 4] Conflicts detected — returning clarification request.")
        response = "# Action Required: Please Resolve the Following Before Planning\n\n"
        for i, conflict in enumerate(conflicts, start=1):
            response += f"**Issue {i}:** {conflict}\n\n"
        response += (
            "---\n"
            "Once you have resolved these issues, resubmit with the updated values "
            "or add `&acknowledged=true` to your request to proceed with the current inputs.\n"
        )
        return response, False

    # Step 5: Generate structured artifact
    print("[Step 5] Generating structured planning artifact...")
    conflict_summary = "; ".join(conflicts) if conflicts else "No conflicts detected."
    report = generate_markdown_report(state, retrieved_docs, conflict_summary, weather_context)

    # Step 6: Email the report if an address was provided
    emailed = False
    if email:
        print(f"[Step 6] Sending report to {email}...")
        emailed = send_report_email(email, report, event_date=date)

    return report, emailed
