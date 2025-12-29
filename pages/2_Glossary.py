import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Glossary", layout="wide")
st.header("2) Glossary (PL → język docelowy)")

target_lang = st.session_state.get("target_language")
target_label = st.session_state.get("target_market_label")

if not target_lang or not target_label:
    st.warning("Najpierw wybierz język/rynek w zakładce Configuration.")
    st.stop()

st.subheader(f"Edytujesz glossary dla: {target_label} (lang={target_lang})")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
glossary_path = os.path.join(DATA_DIR, f"glossary_{target_lang}.csv")

DEFAULT_ROWS = [
    {"term_pl": "fotel fryzjerski", "term_target": "", "locked": True, "notes": ""},
    {"term_pl": "myjnia fryzjerska", "term_target": "", "locked": True, "notes": ""},
]

def load_glossary(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path)
        # upewnij się, że są wszystkie kolumny
        for col in ["term_pl", "term_target", "locked", "notes"]:
            if col not in df.columns:
                df[col] = "" if col != "locked" else False
        df["locked"] = df["locked"].astype(bool)
        return df[["term_pl", "term_target", "locked", "notes"]]
    return pd.DataFrame(DEFAULT_ROWS)

def save_glossary(df: pd.DataFrame, path: str) -> None:
    df = df.copy()
    df["term_pl"] = df["term_pl"].astype(str).str.strip()
    df["term_target"] = df["term_target"].astype(str).str.strip()
    df["notes"] = df["notes"].astype(str)
    df["locked"] = df["locked"].astype(bool)
    df.to_csv(path, index=False)

# klucz w session_state per język
state_key = f"glossary_df_{target_lang}"
if state_key not in st.session_state:
    st.session_state[state_key] = load_glossary(glossary_path)

st.caption("Uzupełnij term_target. Zaznacz locked dla terminów, które muszą być konsekwentne.")

edited = st.data_editor(
    st.session_state[state_key],
    use_container_width=True,
    num_rows="dynamic",
    column_config={"locked": st.column_config.CheckboxColumn("locked")}
)

col1, col2 = st.columns([1, 2])

with col1:
    if st.button("💾 Save glossary", type="primary"):
        save_glossary(edited, glossary_path)
        st.session_state[state_key] = edited
        st.success(f"Zapisano na stałe do: {glossary_path}")

with col2:
    st.info("Tip: zmień język w Configuration → wróć tu → zobaczysz inny zapisany plik glossary dla tego języka.")

st.divider()
st.write("Podgląd (pierwsze 20):")
st.dataframe(edited.head(20), use_container_width=True)
