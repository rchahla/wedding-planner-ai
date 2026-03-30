from state import update_state
from rag import ingest_documents, retrieve_relevant_docs
from artifact_generator import generate_markdown_report


def detect_conflicts(state):
    """
    Step 3: Check state against known constraints and retrieved document guidance.
    Returns a list of conflict strings. Empty list means no conflicts.
    """
    conflicts = []

    guest_count = state.get("guest_count", 0)
    budget = state.get("budget", 0)
    venue_type = state.get("venue_type", "")
    dietary = state.get("dietary", "")
    date = state.get("date", "")

    # Conflict 1: budget too low for guest count (grounded in budget_guide.txt)
    if guest_count > 80 and budget < 8000:
        conflicts.append(
            f"Budget conflict: Your budget is ${budget} for {guest_count} guests. "
            "Retrieved guidance indicates a minimum of $8,000 to $15,000 is typical for 80+ guests. "
            "Would you like to increase your budget or reduce the guest count?"
        )

    # Conflict 2: outdoor venue with no weather backup mentioned
    if "outdoor" in venue_type.lower() and not date:
        conflicts.append(
            "Outdoor venue risk: You selected an outdoor venue but did not provide an event date. "
            "Seasonal weather risks cannot be assessed without a date. "
            "Please provide your event date so weather and backup planning can be evaluated."
        )

    # Conflict 3: outdoor venue in a risky month (grounded in outdoor_guide.txt)
    if "outdoor" in venue_type.lower() and date:
        try:
            month = int(date.split("-")[1])
            if month in [11, 12, 1, 2]:
                conflicts.append(
                    f"Seasonal risk: Your outdoor event is in month {month}, which falls in a cold or winter period. "
                    "Retrieved guidance recommends weather backup planning such as tent rentals and covered seating. "
                    "Do you have a backup indoor option or tent rental arranged?"
                )
        except (IndexError, ValueError):
            pass

    # Conflict 4: dietary restrictions with no catering note
    if dietary and budget > 0 and guest_count > 0:
        per_head = budget / guest_count if guest_count else 0
        if per_head < 50:
            conflicts.append(
                f"Catering risk: Your per-head budget is approximately ${per_head:.0f}. "
                f"Accommodating dietary requirements ({dietary}) typically requires more flexible and higher-cost catering. "
                "Consider allocating more budget to catering or confirming your caterer can meet these needs."
            )

    return conflicts


def run_workflow(user_input):
    acknowledged = user_input.pop("acknowledged", False)

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

    # Step 3: Detect conflicts against retrieved guidance
    print("[Step 3] Checking for conflicts against retrieved guidance...")
    conflicts = detect_conflicts(state)

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
        return response

    # Step 5: Generate structured artifact
    print("[Step 5] Generating structured planning artifact...")
    conflict_summary = "; ".join(conflicts) if conflicts else "No conflicts detected."
    report = generate_markdown_report(state, retrieved_docs, conflict_summary)
    return report
