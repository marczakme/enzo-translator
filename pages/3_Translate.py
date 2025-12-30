import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from llm_providers import chat_llm

st.set_page_config(page_title="Translate", layout="wide")
st.header("3) Translate — multi-LLM + Claude Review")

# ======================================================
# Helpers
# ======================================================

def load_glossary(lang):
    path = f"data/glossary_{lang}.csv"
    if not os.path.exists(path):
        return pd.DataFrame(columns=["term_pl", "term_target", "locked"])
    df = pd.read_csv(path)
    df["locked"] = df["locked"].astype(str).str.lower().isin(["true", "1", "yes"])
    return df


def glossary_text(df):
    rows = []
    for _, r in df.iterrows():
        if r["term_pl"] and r["term_target"]:
            rows.append(f"- {r['term_pl']} => {r['term_target']}")
    return "\n".join(rows)


# ======================================================
# Config
# ======================================================

lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
provider = st.session_state.get("translate_provider", "openai")
style_hint = st.session_state.get("style_hint", "")

if not lang:
    st.warning("Najpierw wybierz język w Configuration.")
    st.stop()

st.subheader(f"Rynek: {label}")
st.caption(f"Model do tłumaczenia: **{provider.upper()}** | Review: **CLAUDE**")

# ======================================================
# Input
# ======================================================

title_pl = st.text_input("Nazwa (PL)")
body_pl = st.text_area("Dalsza treść (PL)", height=220)

glossary_df = load_glossary(lang)
glossary = glossary_text(glossary_df)

temperature = st.slider("Temperature", 0.0, 0.8, 0.2, 0.05)

# ======================================================
# Translate + Review
# ======================================================

if st.button("Translate (auto-review)", type="primary"):
    source = f"NAME:\n{title_pl}\n\nBODY:\n{body_pl}"

    # -------- TRANSLATE --------
    translated = chat_llm(
        provider=provider,
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

    # -------- REVIEW (CLAUDE) --------
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
Check translation quality and terminology.

Return format:
VERDICT: OK / FIX
ISSUES:
- ...
SUGGESTED FIXES:
- ...
CONFIDENCE: 0-100

SOURCE:
{source}

TRANSLATION:
{translated}
""",
            },
        ],
    )

    st.session_state.translated = translated
    st.session_state.review = review

    # -------- SAVE TXT --------
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(f"data/translations/{lang}", exist_ok=True)

    with open(f"data/translations/{lang}/{ts}.txt", "w", encoding="utf-8") as f:
        f.write(
            f"DATE: {datetime.now()}\nLANGUAGE: {label}\nMODEL: {provider}\n\n"
            f"SOURCE:\n{source}\n\nTRANSLATION:\n{translated}\n\nREVIEW:\n{review}"
        )

# ======================================================
# Output
# ======================================================

if "translated" in st.session_state:
    st.subheader("Tłumaczenie")
    st.code(st.session_state.translated)

    st.subheader("Review (Claude)")
    st.code(st.session_state.review)
