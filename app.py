import html
import re
import streamlit as st
import time

from src.agents.agents import critic_chain, writer_chain
from src.pipeline.pipeline import (
    _invoke_with_rate_limit_retry,
    _is_failed_scrape,
    _urls_from_search_results,
)
from src.tools.tools import scrape_url, web_search

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #edf3ff;
}

.stApp {
    background: #07111f;
    background-image:
        radial-gradient(circle at top left, rgba(0,191,255,0.14), transparent 32%),
        radial-gradient(circle at bottom right, rgba(124,58,237,0.12), transparent 30%),
        linear-gradient(180deg, #07111f 0%, #0a1729 100%);
}

/* ── Hide default streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1200px; }

/* ── Hero header ── */
.hero {
    text-align: center;
    padding: 3.5rem 0 2.5rem;
    position: relative;
}
.hero-eyebrow {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: #38bdf8;
    margin-bottom: 1rem;
    opacity: 0.9;
}
.hero h1 {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.8rem, 6vw, 5rem);
    font-weight: 800;
    line-height: 1.0;
    letter-spacing: -0.03em;
    color: #f8fbff;
    margin: 0 0 1rem;
}
.hero h1 span {
    background: linear-gradient(135deg, #38bdf8, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-sub {
    font-size: 1.05rem;
    font-weight: 300;
    color: #b5c3d9;
    max-width: 520px;
    margin: 0 auto;
    line-height: 1.65;
}

/* ── Divider ── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(56,189,248,0.35), transparent);
    margin: 2rem 0;
}

/* ── Input card ── */
.input-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(56,189,248,0.18);
    border-radius: 22px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 40px rgba(0,0,0,0.28);
}

/* ── Streamlit input overrides ── */
.stTextInput > div,
.stTextInput > div > div,
div[data-testid="stTextInput"] > div,
div[data-testid="stTextInput"] [data-baseweb="input"] {
    background: #0b1728 !important;
    background-color: #0b1728 !important;
    border-radius: 12px !important;
}
.stTextInput > div > div > input {
    background: #0b1728 !important;
    background-color: #0b1728 !important;
    border: 1px solid rgba(56,189,248,0.25) !important;
    border-radius: 12px !important;
    color: #f8fbff !important;
    -webkit-text-fill-color: #f8fbff !important;
    caret-color: #38bdf8 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    padding: 0.8rem 1rem !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stTextInput"] input,
input[data-testid="stTextInputInput"] {
    color: #f8fbff !important;
    -webkit-text-fill-color: #f8fbff !important;
    caret-color: #38bdf8 !important;
    background: #0b1728 !important;
    background-color: #0b1728 !important;
}
div[data-testid="stTextInput"] input::placeholder,
input[data-testid="stTextInputInput"]::placeholder {
    color: #7f93ad !important;
    -webkit-text-fill-color: #7f93ad !important;
    opacity: 1 !important;
}
div[data-testid="stTextInput"] [data-baseweb="input"] div {
    background: transparent !important;
    color: #94a3b8 !important;
}
.stTextInput > div > div > input:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 4px rgba(56,189,248,0.14) !important;
}
.stTextInput > label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: #38bdf8 !important;
    font-weight: 500 !important;
}

/* ── Button ── */
.stButton > button {
    background: linear-gradient(135deg, #38bdf8 0%, #8b5cf6 100%) !important;
    color: white !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.04em !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.8rem 2.2rem !important;
    cursor: pointer !important;
    transition: all 0.18s ease !important;
    box-shadow: 0 8px 30px rgba(56,189,248,0.22) !important;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 12px 35px rgba(56,189,248,0.32) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ── Pipeline step cards ── */
.step-card {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
    transition: all 0.25s ease;
    backdrop-filter: blur(10px);
}
.step-card:hover {
    transform: translateY(-2px);
    border-color: rgba(56,189,248,0.18);
}
.step-card.active {
    border-color: rgba(56,189,248,0.45);
    background: rgba(56,189,248,0.06);
}
.step-card.done {
    border-color: rgba(34,197,94,0.28);
    background: rgba(34,197,94,0.05);
}
.step-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    border-radius: 18px 0 0 18px;
    background: rgba(255,255,255,0.06);
    transition: background 0.3s;
}
.step-card.active::before { background: #38bdf8; }
.step-card.done::before   { background: #22c55e; }

.step-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 0.3rem;
}
.step-num {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.15em;
    color: #38bdf8;
    opacity: 0.85;
}
.step-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #f8fbff;
}
.step-status {
    margin-left: auto;
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
}
.status-waiting  { color: #64748b; }
.status-running  { color: #38bdf8; }
.status-done     { color: #22c55e; }

/* ── Result panels ── */
.result-panel {
    background: rgba(8, 19, 34, 0.96);
    border: 1px solid rgba(56,189,248,0.16);
    border-radius: 18px;
    padding: 1.8rem 2rem;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(12px);
    box-shadow: 0 14px 34px rgba(0,0,0,0.22);
}
.result-panel-title {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #38bdf8;
    margin-bottom: 1rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid rgba(56,189,248,0.15);
}
.result-content {
    font-size: 0.92rem;
    line-height: 1.8;
    color: #e3ecf8;
    white-space: pre-wrap;
    font-family: 'DM Sans', sans-serif;
    overflow-wrap: anywhere;
}
.result-content a {
    color: #38bdf8;
}

/* ── Report & feedback panels ── */
.report-panel {
    background: rgba(8, 19, 34, 0.96);
    border: 1px solid rgba(56,189,248,0.2);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(14px);
    box-shadow: 0 18px 45px rgba(0,0,0,0.26);
}
.feedback-panel {
    background: rgba(8, 22, 31, 0.96);
    border: 1px solid rgba(34,197,94,0.2);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(14px);
    box-shadow: 0 18px 45px rgba(0,0,0,0.26);
}
.panel-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 1.2rem;
    padding-bottom: 0.7rem;
}
.panel-label.orange {
    color: #38bdf8;
    border-bottom: 1px solid rgba(56,189,248,0.15);
}
.panel-label.green {
    color: #22c55e;
    border-bottom: 1px solid rgba(34,197,94,0.15);
}
.report-content,
.feedback-content {
    color: #e6edf7;
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    line-height: 1.85;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}
.report-content {
    padding-top: 0.4rem;
}
.report-content h2,
.feedback-content h2 {
    color: #f8fbff;
    font-family: 'Syne', sans-serif;
    font-size: 1.65rem;
    margin: 1.3rem 0 0.65rem;
}
.report-content h3,
.feedback-content h3 {
    color: #eaf2ff;
    font-family: 'Syne', sans-serif;
    font-size: 1.25rem;
    margin: 1rem 0 0.45rem;
}
.report-content p,
.feedback-content p {
    margin: 0.55rem 0;
}
.report-content .bullet,
.feedback-content .bullet {
    margin: 0.35rem 0 0.35rem 1rem;
}
.report-content strong,
.feedback-content strong {
    color: #f8fbff;
}

/* ── Progress text ── */
.stSpinner > div { color: #38bdf8 !important; }

/* ── Expander ── */
details {
    background: rgba(255,255,255,0.02);
    border-radius: 14px;
    padding: 0.3rem 0.8rem;
    border: 1px solid rgba(255,255,255,0.06);
}
details summary {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
    color: #b5c3d9 !important;
    letter-spacing: 0.1em !important;
    cursor: pointer;
}

/* ── Section heading ── */
.section-heading {
    font-family: 'Syne', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: #f8fbff;
    margin: 2rem 0 1rem;
}

/* ── Toast-style notice ── */
.notice {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #7f93ad;
    text-align: center;
    margin-top: 3rem;
    letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)


# ── Helper: render a step card ────────────────────────────────────────────────
def step_card(num: str, title: str, state: str, desc: str = ""):
    status_map = {
        "waiting": ("WAITING", "status-waiting"),
        "running": ("● RUNNING", "status-running"),
        "done":    ("✓ DONE",   "status-done"),
    }

    label, cls = status_map.get(state, ("", ""))
    card_cls = {"running": "active", "done": "done"}.get(state, "")

    st.markdown(f"""
    <div class="step-card {card_cls}">
        <div class="step-header">
            <span class="step-num">{num}</span>
            <span class="step-title">{title}</span>
            <span class="step-status {cls}">{label}</span>
        </div>
        {"<div style='font-size:0.82rem;color:#94a3b8;margin-top:0.3rem;'>"+desc+"</div>" if desc else ""}
    </div>
    """, unsafe_allow_html=True)


def clean_panel_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def format_panel_text(text: str) -> str:
    lines = clean_panel_text(text).split("\n")
    formatted = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        escaped = html.escape(stripped)
        escaped = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)

        if escaped.startswith("### "):
            formatted.append(f"<h3>{escaped[4:]}</h3>")
        elif escaped.startswith("## "):
            formatted.append(f"<h2>{escaped[3:]}</h2>")
        elif escaped.startswith("# "):
            formatted.append(f"<h2>{escaped[2:]}</h2>")
        elif escaped.startswith("- "):
            formatted.append(f'<p class="bullet">• {escaped[2:]}</p>')
        else:
            formatted.append(f"<p>{escaped}</p>")

    return "\n".join(formatted)


# ── Session state init ────────────────────────────────────────────────────────
for key in ("results", "running", "done"):
    if key not in st.session_state:
        st.session_state[key] = {} if key == "results" else False


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">Multi-Agent AI System</div>
    <h1>Researcher<span>Agent</span></h1>
    <p class="hero-sub">
        Four specialized AI agents collaborate — searching, scraping, writing,
        and critiquing — to deliver a polished research report on any topic.
    </p>
</div>

<div class="divider"></div>
""", unsafe_allow_html=True)


# ── Layout: input left, pipeline right ───────────────────────────────────────
col_input, col_spacer, col_pipeline = st.columns([5, 0.5, 4])

with col_input:

    st.markdown('<div class="input-card">', unsafe_allow_html=True)

    topic = st.text_input(
        "Research Topic",
        placeholder="e.g. Roadmap for AGI development in next 5 years",
        key="topic_input",
        label_visibility="visible",
    )

    run_btn = st.button(
        "⚡ Run Research Pipeline",
        use_container_width=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Example chips
    st.markdown("""
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1.5rem;">
        <span style="font-family:'DM Mono',monospace;font-size:0.68rem;color:#7f93ad;letter-spacing:0.1em;">
            TRY →
        </span>
    """, unsafe_allow_html=True)

    examples = [
        "Future of LLM in Tech Industry",
        "All Lastest AI Agents in 2026",
        "Roadmap for AGI development in next 5 years",
    ]

    for ex in examples:
        st.markdown(f"""
        <span style="
            background:rgba(255,255,255,0.05);
            border:1px solid rgba(255,255,255,0.08);
            border-radius:8px;
            padding:0.35rem 0.8rem;
            font-size:0.75rem;
            color:#d8e2f0;
            font-family:'DM Sans',sans-serif;
            cursor:default;
        ">
            {ex}
        </span>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with col_pipeline:

    st.markdown(
        '<div class="section-heading">Pipeline</div>',
        unsafe_allow_html=True
    )

    r = st.session_state.results
    done = st.session_state.done

    def s(step):

        if not r:
            return "waiting"

        steps = ["search", "reader", "writer", "critic"]

        if step in r:
            return "done"

        if st.session_state.running:
            for k in steps:
                if k not in r:
                    return "running" if k == step else "waiting"

        return "waiting"

    step_card(
        "01",
        "Search Agent",
        s("search"),
        "Gathers recent web information"
    )

    step_card(
        "02",
        "Reader Agent",
        s("reader"),
        "Scrapes & extracts deep content"
    )

    step_card(
        "03",
        "Writer Chain",
        s("writer"),
        "Drafts the full research report"
    )

    step_card(
        "04",
        "Critic Chain",
        s("critic"),
        "Reviews & scores the report"
    )


# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn:

    if not topic.strip():
        st.warning("Please enter a research topic first.")

    else:
        st.session_state.results = {}
        st.session_state.running = True
        st.session_state.done = False
        st.rerun()


if st.session_state.running and not st.session_state.done:

    results = {}
    topic_val = st.session_state.topic_input

    # ── Step 1: Search ──
    with st.spinner("🔍 Search Agent is working…"):

        results["search"] = web_search.invoke(
            f"Find recent, reliable and detailed information about: {topic_val}"
        )
        st.session_state.results = dict(results)

    # ── Step 2: Reader ──
    with st.spinner("📄 Reader Agent is scraping top resources…"):

        scrape_errors = []

        for url in _urls_from_search_results(results["search"]):
            scraped_content = scrape_url.invoke(url)

            if not _is_failed_scrape(scraped_content):
                results["reader_url"] = url
                results["reader"] = scraped_content
                break

            scrape_errors.append(f"{url} -> {scraped_content}")
        else:
            results["reader"] = (
                "Could not scrape the search results directly. "
                "Using the search result snippets as the research source instead."
            )

        if scrape_errors:
            results["reader_errors"] = "\n\n".join(scrape_errors)

        st.session_state.results = dict(results)

    # ── Step 3: Writer ──
    with st.spinner("✍️ Writer is drafting the report…"):

        research_combined = (
            f"SEARCH RESULTS:\n{results['search'][:2500]}\n\n"
            f"DETAILED SCRAPED CONTENT:\n{results['reader'][:2500]}"
        )

        results["writer"] = _invoke_with_rate_limit_retry(writer_chain, {
            "topic": topic_val,
            "research": research_combined
        })

        st.session_state.results = dict(results)

    # ── Step 4: Critic ──
    with st.spinner("🧐 Critic is reviewing the report…"):

        results["critic"] = _invoke_with_rate_limit_retry(critic_chain, {
            "report": results["writer"][:3500]
        })

        st.session_state.results = dict(results)

    st.session_state.running = False
    st.session_state.done = True

    st.rerun()


# ── Results display ───────────────────────────────────────────────────────────
r = st.session_state.results

if r:

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="section-heading">Results</div>',
        unsafe_allow_html=True
    )

    # Raw outputs
    if "search" in r:
        with st.expander("🔍 Search Results (raw)", expanded=False):

            search_html = html.escape(clean_panel_text(r["search"]))

            st.markdown(
                f"""
                <div class="result-panel">
                    <div class="result-panel-title">Search Agent Output</div>
                    <div class="result-content">{search_html}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    if "reader" in r:
        with st.expander("📄 Scraped Content (raw)", expanded=False):

            reader_html = html.escape(clean_panel_text(r["reader"]))

            st.markdown(
                f"""
                <div class="result-panel">
                    <div class="result-panel-title">Reader Agent Output</div>
                    <div class="result-content">{reader_html}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Final report
    if "writer" in r:

        report_html = format_panel_text(r["writer"])

        st.markdown(f"""
        <div class="report-panel">
            <div class="panel-label orange">
                📝 Final Research Report
            </div>
            <div class="report-content">{report_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Download button
        st.download_button(
            label="⬇ Download Report (.md)",
            data=r["writer"],
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
        )

    # Critic feedback
    if "critic" in r:

        critic_html = format_panel_text(r["critic"])

        st.markdown(f"""
        <div class="feedback-panel">
            <div class="panel-label green">
                🧐 Critic Feedback
            </div>
            <div class="feedback-content">{critic_html}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="notice">
    ResearchAgent · Powered by LangChain multi-agent pipeline · Built with Streamlit
</div>
""", unsafe_allow_html=True)
