import streamlit as st

from .workflow import run_content_workflow


def main() -> None:
    """Streamlit entry point for local use."""

    st.set_page_config(page_title="Content Production Team", page_icon="✍️", layout="wide")
    st.title("Content Production Team Workflow")
    st.caption("A cyclical multi-agent workflow for research, drafting, and grading using a state-driven control loop.")

    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Your API key is used for live model calls.",
            value="",
        )
        topic = st.text_area(
            "Content Topic",
            placeholder="Example: How AI can improve internal knowledge management for remote teams",
            height=150,
        )
        run_button = st.button("Generate & Refine Content", use_container_width=True)

    if run_button:
        if not topic.strip():
            st.warning("Please enter a topic before starting the workflow.")
            return

        if not api_key:
            st.warning("No API key was provided. The workflow will use fallback logic so the app still runs.")

        result = run_content_workflow(api_key=api_key, topic=topic, render_in_ui=True)
        st.subheader("Final Draft")
        st.write(result["content"] or "No final draft was produced.")
        st.divider()
        st.subheader("Workflow Summary")
        st.metric("Attempts", result.get("attempts", 0))
        st.metric("Final Score", f"{result.get('score', 0)}/100")
        st.text_area("Final Feedback", value=result.get("feedback", ""), height=160)


if __name__ == "__main__":
    main()
