import streamlit as st
import pandas as pd
import os
import re

from openai import OpenAI

st.set_page_config(page_title="Translate", layout="wide")
st.header("3) Translate (plain text) — OpenAI + glossary")

# ---- helpers ----
def load_glossary_for_lang(lang_code: str) -> pd.DataFrame:
    path = os.path.join("data", f"glossary_{lang_code}.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        for col in ["term_pl", "term_target", "locked", "notes"]:
            if col not in df.columns:
                df[col] = "" if col != "locked" else False
        df["locked"] = df["locked"].astype(bool)
        df["term_pl"] = df["term_pl"].astype(str).str.strip()
        df["term_target"] = df["term_target"].astype(str).str.strip()
        return df[["term_pl", "term_target", "locked", "notes"]]
    return pd.DataFrame(columns=["term_pl", "term_target", "locked", "notes"])

def build_glossary_text(df: pd.DataFrame, limit: int = 200) -> str:
    pairs = []
    for _, r in df.iterrows():
        pl = str(r["term_pl"]).strip()
        tgt = str(r["term_target"]).strip()
        if pl and tgt:
            pairs.append(f"- {pl} => {tgt}")
        if len(pairs) >= limit:
            break
    return "\n".join(pairs)

def locked_terms_missing(source_pl: str, translated: str, df: pd.DataFrame):
    src = (source_pl or "").lower()
    tgt = (translated or "").lower()
    misses = []
    for _, r in df[df["locked"] == True].iterrows():
        pl = str(r["term_pl"]).strip()
        tt = str(r["term_target"]).strip()
        if not pl or not tt:
            continue
        if pl.lower() in src and tt.lower() not in tgt:
            misses.append({"term_pl": pl, "term_target": tt})
    return misses

# ---- require configuration ----
target_lang = st.session_state.get("target_language")
target_label = st.session_state.get("target_market_label")
style_hint = st.session_state.get("style_hint", "")

if not target_lang or not target_label:
    st.warning("Najpierw wybierz język/rynek w Configuration.")
    st.stop()

st.subheader(f"Rynek: {target_label} (lang={target_lang})")

# ---- OpenAI secrets ----
if "openai" not in st.secrets or "api_key" not in st.secrets["openai"]:
    st.error("Brak OpenAI API key w Secrets. Dodaj [openai].api_key w Streamlit Cloud.")
    st.stop()

model = st.secrets["openai"].get("model", "gpt-4.1-mini")
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# ---- inputs ----
if "source_text" not in st.session_state:
    st.session_state.source_text = ""
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

source_text = st.text_area(
    "Tekst po polsku (plain text)",
    value=st.session_state.source_text,
    height=220,
    placeholder="Wklej tutaj tekst po polsku..."
)
st.session_state.source_text = source_text

glossary_df = load_glossary_for_lang(target_lang)

with st.expander("Podgląd glossary dla tego języka"):
    st.dataframe(glossary_df, use_container_width=True)

glossary_text = build_glossary_text(glossary_df)

temperature = st.slider("Temperature (niżej = bardziej konsekwentnie)", 0.0, 0.8, 0.2, 0.0
