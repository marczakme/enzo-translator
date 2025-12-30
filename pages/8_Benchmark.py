import streamlit as st
import pandas as pd
import os
from llm_providers import chat_llm

st.set_page_config(page_title="Benchmark", layout="wide")
st.header("🧪 8) Benchmark — porównanie modeli tłumaczeń")

st.markdown(
    """
Ten tryb pozwala **porównać jakość tłumaczeń** wykonanych przez różne modele językowe
dla **tego samego tekstu**, przy **jednym, stałym reviewerze (Claude)**.

✅ Translate: OpenAI / Claude / Gemini  
✅ Review: zawsze Claude  
✅ Ten sam prompt i ten sam kontekst dla wszystkich modeli (porównywalność)
"""
)

# ======================================================
# Config
# ======================================================

lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
style_hint_default = st.session_state.get("style_hint", "")

if not lang:
    st.warning("Najpierw wybierz język w Configuration.")
    st.stop()

st.subheader(f"Rynek: {label}")
st.caption("Translate: OpenAI / Claude / Gemini | Review: Claude")

# ======================================================
# Helpers
# ======================================================

def load_glossary(lang):
    path = f"data/glossary_{lang}.csv"
    if not os.path.exists(path):
        return ""
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        if r.get("term_pl") and r.get("term_target"):
            rows.append(f"- {r['term_pl']} => {r['term_target']}")
    return "\n".join(rows)

glossary = load_glossary(lang)

# ======================================================
# Input
# ======================================================

col1, col2 = st.columns([1, 1])

with col1:
    title_pl = st.text_input("Nazwa (PL)", placeholder="np. Fotel fryzjerski Enzo X1")
    temperature = st.slider("Temperature (dla wszystkich modeli)", 0.0, 0.8, 0.2, 0.05)

with col2:
    # ✅ NOWE: kontekst do benchmarku (domyślnie z Configuration)
    benchmark_context = st.text_area(
        "Kontekst benchmarku (opcjonalnie)",
        value=style_hint_default,
        height=120,
        help="Ten kontekst zostanie użyty identycznie dla OpenAI / Claude / Gemini. "
             "Jeśli puste — prompt działa bez dodatkowego kontekstu."
    )

body_pl = st.text_area("Dalsza treść (PL)", height=220)

st.divider()

# ======================================================
# Prompt templates (IDENTICAL for all providers)
# ======================================================

SYSTEM_TRANSLATE = "You are a professional translator. Translate precisely. Output plain text only."

def build_translate_user_prompt(source_text: str) -> str:
    return f"""
Target language: {label}

Context:
{benchmark_context.strip() if benchmark_context.strip() else "None"}

Mandatory terminology:
{glossary if glossary else "None"}

Rules:
- Output plain text only (no HTML)
- Preserve structure NAME/BODY
- Use mandatory terminology when applicable
- Keep numbers/units consistent

Translate:

{source_text}
""".strip()

SYSTEM_REVIEW = "You are a senior linguistic reviewer."

def build_review_user_prompt(source_text: str, translation: str, provider_name: str) -> str:
    return f"""
Compare translation quality objectively.

Return format:
VERDICT: OK / FIX
ISSUES:
- ...
SUGGESTED FIXES:
- ...
CONFIDENCE: 0-100

SOURCE:
{source_text}

TRANSLATION ({provider_name}):
{translation}
""".strip()

# ======================================================
# Benchmark
# ======================================================

if st.button("Run benchmark", type="primary"):
    if not ((title_pl or "").strip() or (body_pl or "").strip()):
        st.warning("Uzupełnij nazwę lub treść.")
        st.stop()

    source = f"NAME:\n{title_pl.strip()}\n\nBODY:\n{body_pl.strip()}"

    providers = [("openai", "OpenAI"), ("claude", "Claude"), ("gemini", "Gemini")]
    results = {}

    # Translate (3 models)
    with st.spinner("Tłumaczenie (OpenAI / Claude / Gemini)…"):
        for code, label_p in providers:
            translated = chat_llm(
                provider=code,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_TRANSLATE},
                    {"role": "user", "content": build_translate_user_prompt(source)},
                ],
            )
            results[code] = {"translation": translated}

    # Review (always Claude)
    with st.spinner("Review (Claude)…"):
        for code, label_p in providers:
            review = chat_llm(
                provider="claude",
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_REVIEW},
                    {"role": "user", "content": build_review_user_prompt(source, results[code]["translation"], label_p)},
                ],
            )
            results[code]["review"] = review

    # Save in session for display
    st.session_state.benchmark = {
        "context": benchmark_context,
        "source": source,
        "results": results
    }

# ======================================================
# Output
# ======================================================

if "benchmark" in st.session_state:
    st.subheader("Wyniki benchmarku")

    with st.expander("Zastosowany kontekst i źródło (dla porównywalności)", expanded=False):
        st.markdown("**Kontekst:**")
        st.code(st.session_state.benchmark["context"] if st.session_state.benchmark["context"].strip() else "None")
        st.markdown("**Źródło (PL):**")
        st.code(st.session_state.benchmark["source"])

    tabs = st.tabs(["OpenAI", "Claude", "Gemini"])

    mapping = [("openai", "OpenAI"), ("claude", "Claude"), ("gemini", "Gemini")]
    for tab, (code, name) in zip(tabs, mapping):
        with tab:
            st.markdown(f"### Translation — {name}")
            st.code(st.session_state.benchmark["results"][code]["translation"])

            st.markdown("### Review (Claude)")
            st.code(st.session_state.benchmark["results"][code]["review"])
