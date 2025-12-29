import streamlit as st

st.set_page_config(page_title="Translate", layout="wide")
st.header("3) Translate (plain text) — UI")

if "source_text" not in st.session_state:
    st.session_state.source_text = ""
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

st.session_state.source_text = st.text_area(
    "Tekst po polsku (plain text)",
    value=st.session_state.source_text,
    height=220
)

st.info("W następnym kroku podpinamy OpenAI i robimy tłumaczenie z glossary + QA.")

if st.button("Translate (placeholder)", type="primary"):
    st.session_state.translated_text = "[TU pojawi się tłumaczenie — dodamy OpenAI w kolejnym kroku]"

st.text_area(
    "Wynik tłumaczenia",
    value=st.session_state.translated_text,
    height=220
)
