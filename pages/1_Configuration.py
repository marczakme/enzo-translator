import streamlit as st

st.set_page_config(page_title="Configuration", layout="wide")
st.header("1) Configuration")

LANGS = [
    ("ro", "Rumuński (RO)"),
    ("hu", "Węgierski (HU)"),
    ("el", "Grecki (GR)"),
    ("de", "Niemiecki (DE)"),
    ("cs", "Czeski (CZ)"),
    ("sk", "Słowacki (SK)"),
    ("nl", "Niderlandzki (NL)"),
    ("it", "Włoski (IT)"),
    ("fr", "Francuski (FR)"),
    ("hr", "Chorwacki (HR)"),
    ("lt", "Litewski (LT)"),
    ("fi", "Fiński (FI)"),
    ("sv", "Szwedzki (SE)"),
]

lang_labels = [label for _, label in LANGS]
lang_codes = {label: code for code, label in LANGS}

chosen_lang = st.selectbox("Język / rynek docelowy", lang_labels)
st.session_state.target_language = lang_codes[chosen_lang]
st.session_state.target_market_label = chosen_lang

st.subheader("Model językowy")

llm_translate = st.selectbox(
    "Model do tłumaczenia (Translate)",
    ["OpenAI", "Gemini", "Qwen"],
    index=0,
)

st.session_state.translate_provider = llm_translate.lower()

st.caption("Review językowe jest zawsze wykonywane przez **Gemini** (stały benchmark jakości).")

style_hint = st.text_area(
    "Kontekst / styl (opcjonalnie)",
    placeholder="np. sprzęt fryzjerski, ton profesjonalny, bez marketingowego lania wody",
)

st.session_state.style_hint = style_hint
