import streamlit as st

st.set_page_config(page_title="Configuration", layout="wide")
st.header("1) Configuration")

# Inicjalizacja stanu
if "target_language" not in st.session_state:
    st.session_state.target_language = "de"
if "target_market_label" not in st.session_state:
    st.session_state.target_market_label = "Niemiecki (DE)"
if "style_hint" not in st.session_state:
    st.session_state.style_hint = (
        "Branża: profesjonalne wyposażenie fryzjerskie i kosmetyczne. "
        "Ton: ekspercki, naturalny, bez marketingowego nadęcia."
    )

# Lista języków/rynków (BE jako rynek, nie „język”)
LANG_OPTIONS = [
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
    ("nl", "Niderlandzki (BE) — Flandria"),
    ("fr", "Francuski (BE) — Walonia/Bruksela"),
    ("de", "Niemiecki (BE) — wspólnota niemieckojęzyczna"),
]

# wyznacz index z session_state (po labelu, żeby działało też dla BE)
labels = [x[1] for x in LANG_OPTIONS]
default_label = st.session_state.get("target_market_label", "Niemiecki (DE)")
default_index = labels.index(default_label) if default_label in labels else 0

choice = st.selectbox("Język / rynek docelowy", options=LANG_OPTIONS, format_func=lambda x: x[1], index=default_index)

st.session_state.target_language = choice[0]      # kod języka (ISO)
st.session_state.target_market_label = choice[1]  # label rynku do wyświetlania

st.session_state.style_hint = st.text_area(
    "Wskazówki stylu / rynku (kontekst dla tłumaczenia)",
    value=st.session_state.style_hint,
    height=140
)

st.success(f"Zapisano w sesji: {st.session_state.target_market_label} (lang={st.session_state.target_language})")
