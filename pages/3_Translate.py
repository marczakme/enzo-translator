import streamlit as st
import pandas as pd
import os

from openai import OpenAI

st.set_page_config(page_title="Translate", layout="wide")
st.header("3) Translate (plain text) — OpenAI + glossary")

# --------------------
# Helpers
# --------------------

def load_glossary(lang_code: str) -> pd.DataFrame:
    path = os.path.join("data", f"glossary_{lang_code}.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        for col in ["term_pl", "term_target", "locked", "notes"]:
            if col not in df.columns:
                df[col] = "" if col != "locked" else False
        df["locked"] = df["locked"].astype(bool)
        return df
    return pd.DataFrame(columns=["term_pl", "term_target", "locked", "notes"])


def glossary_to_text(df: pd.DataFrame) -> str:
    lines = []
    for _, r in df.iterrows():
        pl = str(r["term_pl"]).strip()
        tgt = str(r["term_target"]).strip()
        if pl and tgt:
            lines.append(f"- {pl} => {tgt}")
    return "\n".join(lines)


def check_locked_terms(source: str, translated: str, df: pd.DataFrame):
    src = source.lower()
    tgt = translated.lower()
    missing = []

    locked_df = df[df["locked"] == True]
    for _, r in locked_df.iterrows():
        pl = str(r["term_pl"]).strip()
        tt = str(r["term_target"]).strip()
        if pl and tt and pl.lower() in src and tt.lower() not in tgt:
            missing.append({"term_pl": pl, "term_target": tt})

    return missing


# --------------------
# Configuration
# --------------------

lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
style_hint = st.session_state.get("style_hint", "")

if not lang or not label:
    st.warning("Najpierw wybierz język/rynek w Configuration.")
    st.stop()

st.subheader(f"Rynek: {label}")

# --------------------
# OpenAI
# --------------------

if "openai" not in st.secrets:
    st.error("Brak OpenAI API key w Secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["openai"]["api_key"])
model = st.secrets["openai"].get("model", "gpt-4.1-mini")

# --------------------
# UI
# --------------------

source_text = st.text_area(
    "Tekst po polsku (plain text)",
    height=220,
    placeholder="Wklej tekst po polsku…"
)

glossary_df = load_glossary(lang)

with st.expander("Glossary dla tego języka"):
    st.dataframe(glossary_df, use_container_width=True)

temperature = st.slider("Temperature", 0.0, 0.8, 0.2, 0.05)

# --------------------
# Translate
# --------------------

if st.button("Translate", type="primary"):
    if not source_text.strip():
        st.warning("Wklej tekst do tłumaczenia.")
        st.stop()

    glossary_text = glossary_to_text(glossary_df)

    system_prompt = (
        "You are a senior professional translator and localization expert. "
        "Translate precisely for native speakers. "
        "Use natural, expert tone. Do not add explanations."
    )

    user_prompt = (
        "Source language: Polish\n"
        f"Target language: {label}\n\n"
        "Industry / style context:\n"
        f"{style_hint}\n\n"
        "Mandatory terminology (Polish => Target):\n"
        f"{glossary_text if glossary_text else 'None'}\n\n"
        "Rules:\n"
        "- Do not translate numbers, units, product codes\n"
        "- Do not shorten content\n"
        "- Output plain text only\n\n"
        "Text to translate:\n"
        f"{source_text}"
    )

    with st.spinner("Tłumaczę…"):
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

    translated = response.choices[0].message.content.strip()
    st.session_state.translated_text = translated

# --------------------
# Output + QA
# --------------------

translated_text = st.session_state.get("translated_text", "")

st.text_area(
    "Wynik tłumaczenia",
    value=translated_text,
    height=260
)

if translated_text:
    missing = check_locked_terms(source_text, translated_text, glossary_df)

    st.subheader("QA — spójność terminologii (locked)")
    if not missing:
        st.success("OK — wszystkie locked terminy użyte ✅")
    else:
        st.error("Brakuje locked terminów:")
        st.dataframe(pd.DataFrame(missing), use_container_width=True)
