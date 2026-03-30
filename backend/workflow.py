from state import update_state
from rag import ingest_documents, retrieve_relevant_docs
from artifact_generator import generate_markdown_report

def run_workflow(user_input):
    state = update_state(user_input)

    guest_count = state.get("guest_count", 0)
    budget = state.get("budget", 0)

    query = f"wedding budget for {guest_count} guests with budget {budget}"
    ingest_documents()
    retrieved_docs = retrieve_relevant_docs(query)

    if guest_count > 80 and budget < 8000:
        conflict_message = "Budget may be too low for the current guest count."
    else:
        conflict_message = "No major budget conflict detected."

    report = generate_markdown_report(state, retrieved_docs, conflict_message)
    return report