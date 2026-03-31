import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUTPUT_FILE = os.path.join(BASE_DIR, "outputs", "wedding_report.md")


def build_prompt(state, retrieved_docs, conflict_summary):
    guest_count = state.get("guest_count", "Not provided")
    budget = state.get("budget", "Not provided")
    theme = state.get("theme", "Not provided")
    date = state.get("date", "Not provided")
    venue_type = state.get("venue_type", "Not provided")
    dietary = state.get("dietary", "Not provided")

    context_block = "\n\n".join(
        f"[Source: {doc['source']}]\n{doc['text']}" for doc in retrieved_docs
    )

    prompt = f"""You are a professional wedding planner assistant. Using the event details and retrieved guidance below, generate a structured wedding planning report in Markdown.

## Event Details
- Guest Count: {guest_count}
- Budget: ${budget}
- Theme: {theme}
- Event Date: {date}
- Venue Type: {venue_type}
- Dietary Requirements: {dietary}

## Conflict Summary
{conflict_summary}

## Retrieved Guidance (cite these sources in your recommendations)
{context_block}

## Instructions
Write a Markdown report with the following sections:
1. **Event Summary** — restate the key event details
2. **Conflict Summary** — explain any conflicts detected and what they mean for planning
3. **Planning Recommendations** — 4 to 6 specific recommendations grounded in the retrieved guidance. After each recommendation, cite the source document it came from in parentheses like this: *(Source: filename.txt)*
4. **Suggested Next Actions** — a short checklist of 3 to 5 concrete next steps the couple should take

Keep the tone helpful and professional. Be specific — reference actual numbers from the event details."""

    return prompt


def generate_with_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error generating report with Gemini: {str(e)}"


def fallback_report(state, retrieved_docs, conflict_summary):
    guest_count = state.get("guest_count", "Not provided")
    budget = state.get("budget", "Not provided")
    theme = state.get("theme", "Not provided")
    date = state.get("date", "Not provided")
    venue_type = state.get("venue_type", "Not provided")
    dietary = state.get("dietary", "Not provided")

    report = f"""# Wedding Planning Report

## Event Details
- Guest Count: {guest_count}
- Budget: ${budget}
- Theme: {theme}
- Event Date: {date}
- Venue Type: {venue_type}
- Dietary Requirements: {dietary}

## Conflict Summary
{conflict_summary}

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
    return report


def generate_markdown_report(state, retrieved_docs, conflict_summary):
    prompt = build_prompt(state, retrieved_docs, conflict_summary)
    report_body = generate_with_gemini(prompt)

    if report_body:
        report = f"# Wedding Planning Report\n\n{report_body}"
    else:
        report = fallback_report(state, retrieved_docs, conflict_summary)

    os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    return report
