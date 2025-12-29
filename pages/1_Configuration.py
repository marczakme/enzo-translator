import streamlit as st

st.set_page_config(page_title="Configuration", layout="wide")

st.header("1) Configuration")

# Inicjalizacja stanu
if "target_language" not in st.session_state:
    st.session_state.target_language = "de"
if "style_hint" not in st.session_state:
    st.session_state.style_hint = "Branża: profesjonalne wyposażenie fryzjerskie i kosmetyczne. Ton: ekspercki, naturalny."

lang = st.selectbox(
    "Język docelowy",
    options=[
        ("de", "Niemiecki (DE)"),
        ("ro", "Rumuński (RO)"),
        ("el", "Grecki (GR)"),
        ("cs", "Czeski (CZ)"),
        ("sk", "Słowacki (SK)"),
        ("nl", "Niderlandzki (NL)"),
    ],
    format_func=lambda x: x[1],
    index=[x[0] for x in [("de",""),("ro",""),("el",""),("cs",""),("sk",""),("nl","")]].index(st.session_state.target_language)
    if st.session_state.target_language in ["de","ro","el","cs","sk","nl"] else 0
)

st.session_state.target_language = lang[0]

st.session_state.style_hint = st.text_area(
    "Wskazówki stylu / rynku (kontekst dla tłumaczenia)",
    value=st.session_state.style_hint,
    height=140
)

st.success(f"Zapisano w sesji: język={st.session_state.target_language}")
