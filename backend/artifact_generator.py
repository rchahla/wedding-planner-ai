import os

OUTPUT_FILE = "outputs/wedding_report.md"

def generate_markdown_report(state, retrieved_docs, conflict_message):
    guest_count = state.get("guest_count", "Not provided")
    budget = state.get("budget", "Not provided")

    report = f"""# Wedding Planning Report

## Event Details
- Guest Count: {guest_count}
- Budget: ${budget}

## Conflict Summary
- {conflict_message}

## Retrieved Guidance
"""

    if retrieved_docs:
        for i, doc in enumerate(retrieved_docs, start=1):
            source = doc.get("source", "Unknown source")
            text = doc.get("text", "")
            report += f"\n### Source {i}: {source}\n{text}\n"
    else:
        report += "\nNo relevant guidance was retrieved.\n"

    report += """
## Suggested Next Actions
- Review whether the current budget is realistic for the guest count
- Adjust the guest count or budget if needed
- Review vendor and venue requirements before finalizing the plan
"""

    os.makedirs("outputs", exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    return report