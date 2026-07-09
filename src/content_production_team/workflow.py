import json
import re
from typing import Any, Callable, TypedDict

import streamlit as st

try:
    from langchain_openai import ChatOpenAI
except Exception as exc:  # pragma: no cover - protects deployment startup
    ChatOpenAI = None
    LLM_IMPORT_ERROR = exc
else:
    LLM_IMPORT_ERROR = None

from .config import DEFAULT_MAX_ATTEMPTS, DEFAULT_MIN_SCORE, DEFAULT_MODEL, get_openai_api_key


class AgentState(TypedDict, total=False):
    """Central state object shared across the workflow nodes."""

    topic: str
    research_notes: str
    content: str
    score: int
    feedback: str
    attempts: int


def _coerce_text(response: Any) -> str:
    """Normalize LLM output into a string for downstream parsing."""

    if response is None:
        return ""
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, list):
            return "\n".join(str(item) for item in content)
        return str(content)
    return str(response)


def _extract_json_payload(text: str) -> dict[str, Any]:
    """Extract a JSON object from model output, even when wrapped in Markdown fences."""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _build_fallback_research(topic: str) -> str:
    """Used when the LLM is unavailable or the API call fails."""

    return (
        f"Fallback research notes for '{topic}':\n"
        "- Define the audience, intent, and primary benefit of the article.\n"
        "- Identify three supporting ideas, examples, or facts that strengthen the argument.\n"
        "- Plan a strong introduction, middle section, and conclusion that encourage action."
    )


def _build_fallback_content(topic: str, research_notes: str, feedback: str, attempts: int) -> str:
    """Produces a reasonable draft even when the AI call fails."""

    feedback_hint = feedback or "Focus on clarity, structure, and a compelling conclusion."
    return (
        f"# {topic}\n\n"
        f"This article explores {topic} with a practical, reader-first approach.\n\n"
        "The opening explains why the topic matters today, followed by a concise breakdown of the most important points.\n\n"
        f"{research_notes}\n\n"
        f"Feedback from the previous pass: {feedback_hint}\n\n"
        f"This draft is iteration {attempts} and is designed to be polished further if needed."
    )


def _build_fallback_grading(content: str) -> tuple[int, str]:
    """A simple deterministic fallback when the grader cannot return structured JSON."""

    words = len(re.findall(r"\w+", content))
    score = min(100, max(0, 70 + min(20, words // 100)))
    feedback = (
        "- Strengthen the introduction with a sharper hook.\n"
        "- Add one concrete example or statistic to support the main claim.\n"
        "- Improve the conclusion with a clear takeaway or call to action."
    )
    return score, feedback


def _get_llm(api_key: str, temperature: float) -> Any | None:
    """Create an LLM client when credentials are available."""

    if not api_key or ChatOpenAI is None:
        return None

    try:
        return ChatOpenAI(model=DEFAULT_MODEL, temperature=temperature, api_key=api_key)
    except Exception:
        return None


def researcher_agent(state: AgentState, api_key: str) -> AgentState:
    """Collects research notes for the given topic and stores them in state."""

    topic = state.get("topic", "")
    llm = _get_llm(api_key, temperature=0.2)

    if llm is None:
        state["research_notes"] = _build_fallback_research(topic)
        return state

    prompt = (
        f"You are a senior research analyst. Produce a detailed set of research notes for the following topic: {topic}.\n"
        "Include observations, useful facts, supporting angles, and a concise plan for a compelling article."
    )

    try:
        response = llm.invoke(prompt)
        notes = _coerce_text(response).strip()
        state["research_notes"] = notes or _build_fallback_research(topic)
    except Exception as exc:  # pragma: no cover - exercised during runtime failures
        state["research_notes"] = _build_fallback_research(topic) + f"\n\nModel error: {exc}"

    return state


def content_creator_agent(state: AgentState, api_key: str) -> AgentState:
    """Writes or rewrites the blog post using the research notes and any prior feedback."""

    topic = state.get("topic", "")
    research_notes = state.get("research_notes", "")
    feedback = state.get("feedback", "")
    attempts = int(state.get("attempts", 0)) + 1

    llm = _get_llm(api_key, temperature=0.3)

    if llm is None:
        state["content"] = _build_fallback_content(topic, research_notes, feedback, attempts)
        state["attempts"] = attempts
        return state

    feedback_context = (
        "There is no prior feedback yet. Write a strong first draft."
        if not feedback
        else f"Improve the draft using the following feedback from the previous pass: {feedback}"
    )

    prompt = (
        f"You are an expert content creator. Write an engaging blog post about '{topic}'.\n"
        f"Use the following research notes as your source of truth:\n{research_notes}\n\n"
        f"{feedback_context}\n\n"
        "Write a polished article with a clear title, an engaging introduction, several supporting sections, and a strong conclusion."
    )

    try:
        response = llm.invoke(prompt)
        content = _coerce_text(response).strip()
        state["content"] = content or _build_fallback_content(topic, research_notes, feedback, attempts)
    except Exception as exc:  # pragma: no cover - exercised during runtime failures
        state["content"] = _build_fallback_content(topic, research_notes, feedback, attempts) + f"\n\nModel error: {exc}"

    state["attempts"] = attempts
    return state


def grader_agent(state: AgentState, api_key: str) -> AgentState:
    """Scores the content and returns actionable feedback in a structured way."""

    topic = state.get("topic", "")
    content = state.get("content", "")

    llm = _get_llm(api_key, temperature=0.1)

    if llm is None:
        score, feedback = _build_fallback_grading(content)
        state["score"] = score
        state["feedback"] = feedback
        return state

    prompt = (
        f"You are a strict editorial grader evaluating a blog post about '{topic}'.\n"
        "Return valid JSON with exactly two keys: 'score' as an integer between 0 and 100 and 'feedback' as a single string containing bullet points.\n"
        f"Draft content:\n{content}"
    )

    try:
        response = llm.invoke(prompt)
        text = _coerce_text(response).strip()
        payload = _extract_json_payload(text)
        score = int(payload.get("score", 0))
        feedback = str(payload.get("feedback", "No feedback provided."))
    except Exception:
        # The UI should remain stable even if the model returns malformed content.
        score, feedback = _build_fallback_grading(content)

    try:
        state["score"] = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        state["score"] = 0

    state["feedback"] = feedback or "- Add a stronger hook and clearer conclusion."
    return state


def should_continue(state: AgentState, min_score: int = DEFAULT_MIN_SCORE, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> str:
    """Route the workflow based on score and attempt count."""

    score = int(state.get("score", 0))
    attempts = int(state.get("attempts", 0))

    if score >= min_score:
        return "end"
    if attempts < max_attempts:
        return "retry"
    return "max_out"


def run_content_workflow(
    api_key: str | None = None,
    topic: str = "",
    render_in_ui: bool = False,
    progress_callback: Callable[[str, str], None] | None = None,
    min_score: int = DEFAULT_MIN_SCORE,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> AgentState:
    """Execute the cyclical content workflow and optionally render progress in Streamlit."""

    resolved_api_key = api_key if api_key is not None else get_openai_api_key()
    state: AgentState = {
        "topic": topic.strip(),
        "research_notes": "",
        "content": "",
        "score": 0,
        "feedback": "",
        "attempts": 0,
    }

    # Step 1: Researcher agent gathers background notes before the drafting loop begins.
    state = researcher_agent(state, resolved_api_key)
    if progress_callback:
        progress_callback("Researcher Agent", state["research_notes"])
    if render_in_ui:
        with st.expander("Researcher Agent", expanded=True):
            st.write(state["research_notes"] or "No research notes were generated.")

    while True:
        # Step 2: The Content Creator uses the research notes and prior feedback (if any).
        state = content_creator_agent(state, resolved_api_key)
        if progress_callback:
            progress_callback(f"Content Creator Agent - Attempt {state['attempts']}", state["content"])
        if render_in_ui:
            with st.expander(f"Content Creator Agent - Attempt {state['attempts']}", expanded=True):
                st.write(state["content"] or "No content was generated.")

        # Step 3: The Grader evaluates the draft and stores a score and bullet-point feedback.
        state = grader_agent(state, resolved_api_key)
        if progress_callback:
            progress_callback(
                f"Grader Agent - Attempt {state['attempts']}",
                f"Score: {state['score']}/100\n\nFeedback:\n{state['feedback']}",
            )
        if render_in_ui:
            with st.expander(f"Grader Agent - Attempt {state['attempts']}", expanded=True):
                st.metric("Score", f"{state['score']}/100")
                st.write(state["feedback"] or "No feedback was returned.")

        decision = should_continue(state, min_score=min_score, max_attempts=max_attempts)
        if decision in {"end", "max_out"}:
            break
        if render_in_ui:
            st.info("The draft needs another pass. The workflow is routing it back to the Content Creator Agent.")

    return state
