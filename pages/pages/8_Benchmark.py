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

➡️ Idealne do wyboru najlepszego modelu **per język / rynek**.
"""
)

# ======================================================
# Config
# ======================================================

lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
style_hint = st.session_state.get("style_hint", "")

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

title_pl = st.text_input("Nazwa (PL)", placeholder="np. Fotel fryzjerski Enzo X1")
body_pl = st.text_area("Dalsza treść (PL)", height=220)

temperature = st.slider("Temperature (dla wszystkich modeli)", 0.0, 0.8, 0.2, 0.05)

# ======================================================
# Benchmark
# ======================================================

if st.button("Run benchmark", type="primary"):
    if not (title_pl or body_pl).strip():
        st.warning("Uzupełnij nazwę lub treść.")
        st.stop()

    source = f"NAME:\n{title_pl}\n\nBODY:\n{body_pl}"

    providers = ["openai", "claude", "gemini"]
    results = {}

    with st.spinner("Tłumaczenie (3 modele)…"):
        for p in providers:
            translated = chat_llm(
                provider=p,
                temperature=temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate precisely. Output plain text only.",
                    },
                    {
                        "role": "user",
                        "content": f"""
Target language: {label}

Context:
{style_hint}

Mandatory terminology:
{glossary if glossary else "None"}

Translate and keep structure:

{source}
""",
                    },
                ],
            )
            results[p] = {"translation": translated}

    with st.spinner("Review (Claude)…"):
        for p in providers:
            review = chat_llm(
                provider="claude",
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior linguistic reviewer.",
                    },
                    {
                        "role": "user",
                        "content": f"""
Compare translation quality objectively.

Return format:
VERDICT: OK / FIX
ISSUES:
- ...
SUGGESTED FIXES:
- ...
CONFIDENCE: 0-100

SOURCE:
{source}

TRANSLATION ({p.upper()}):
{results[p]["translation"]}
""",
                    },
                ],
            )
            results[p]["review"] = review

    st.session_state.benchmark = results

# ======================================================
# Output
# ======================================================

if "benchmark" in st.session_state:
    st.divider()
    st.subheader("Wyniki benchmarku")

    tabs = st.tabs(["OpenAI", "Claude", "Gemini"])

    for tab, provider in zip(tabs, ["openai", "claude", "gemini"]):
        with tab:
            st.markdown(f"### Translation — {provider.upper()}")
            st.code(st.session_state.benchmark[provider]["translation"])

            st.markdown("### Review (Claude)")
            st.code(st.session_state.benchmark[provider]["review"])
