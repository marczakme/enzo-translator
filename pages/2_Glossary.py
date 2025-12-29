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

REQUIRED_COLS = ["term_pl", "term_target", "locked", "notes"]

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    # ujednolicenie kolumn
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # mapowanie alternatywnych nazw (na wypadek importów)
    rename_map = {
        "pl": "term_pl",
        "source": "term_pl",
        "term_source": "term_pl",
        "target": "term_target",
        "term": "term_pl",
        "translation": "term_target",
        "is_locked": "locked",
    }
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # brakujące kolumny
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = "" if col != "locked" else False

    df = df[REQUIRED_COLS]

    # typy + trim
    df["term_pl"] = df["term_pl"].astype(str).str.strip()
    df["term_target"] = df["term_target"].astype(str).str.strip()
    df["notes"] = df["notes"].astype(str)
    df["locked"] = df["locked"].astype(bool)

    # usuń puste wiersze (bez term_pl)
    df = df[df["term_pl"].str.len() > 0].copy()

    # deduplikacja po term_pl (zostaw ostatni)
    df = df.drop_duplicates(subset=["term_pl"], keep="last").reset_index(drop=True)

    return df

def load_glossary(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path)
        return normalize_df(df)
    return pd.DataFrame(DEFAULT_ROWS)

def save_glossary(df: pd.DataFrame, path: str) -> None:
    df = normalize_df(df)
    df.to_csv(path, index=False)

def merge_glossaries(existing: pd.DataFrame, imported: pd.DataFrame) -> pd.DataFrame:
    # imported ma priorytet (nadpisuje term_target/locked/notes)
    ex = normalize_df(existing)
    im = normalize_df(imported)
    merged = pd.concat([ex, im], ignore_index=True)
    merged = merged.drop_duplicates(subset=["term_pl"], keep="last").reset_index(drop=True)
    return merged

# session key per język
state_key = f"glossary_df_{target_lang}"
if state_key not in st.session_state:
    st.session_state[state_key] = load_glossary(glossary_path)

# -------------------------
# Import / Export UI
# -------------------------
st.markdown("### Import / Export")

c1, c2, c3 = st.columns([2, 2, 3])

with c1:
    st.download_button(
        label="⬇️ Pobierz glossary (CSV)",
        data=st.session_state[state_key].to_csv(index=False).encode("utf-8"),
        file_name=f"glossary_{target_lang}.csv",
        mime="text/csv",
    )

with c2:
    uploaded = st.file_uploader(
        "⬆️ Import CSV (dla tego języka)",
        type=["csv"],
        help="CSV powinien mieć kolumny: term_pl, term_target, locked, notes (locked = True/False)."
    )

with c3:
    import_mode = st.radio(
        "Tryb importu",
        options=["Scal (merge) — nadpisuj te same term_pl", "Nadpisz (overwrite) — zastąp cały glossary"],
        horizontal=False
    )

if uploaded is not None:
    try:
        imported_df = pd.read_csv(uploaded)
        imported_df = normalize_df(imported_df)

        st.write("Podgląd importu (pierwsze 20):")
        st.dataframe(imported_df.head(20), use_container_width=True)

        if st.button("Zastosuj import", type="primary"):
            if import_mode.startswith("Scal"):
                new_df = merge_glossaries(st.session_state[state_key], imported_df)
            else:
                new_df = imported_df

            st.session_state[state_key] = new_df
            save_glossary(new_df, glossary_path)
            st.success(f"Import zastosowany i zapisany na stałe do: {glossary_path}")

    except Exception as e:
        st.error(f"Błąd importu CSV: {e}")

st.divider()

# -------------------------
# Edycja ręczna + zapis
# -------------------------
st.caption("Uzupełnij term_target. Zaznacz locked dla terminów, które muszą być konsekwentne.")

edited = st.data_editor(
    st.session_state[state_key],
    use_container_width=True,
    num_rows="dynamic",
    column_config={"locked": st.column_config.CheckboxColumn("locked")}
)

col_save, col_info = st.columns([1, 2])

with col_save:
    if st.button("💾 Save glossary", type="primary"):
        save_glossary(edited, glossary_path)
        st.session_state[state_key] = edited
        st.success(f"Zapisano na stałe do: {glossary_path}")

with col_info:
    st.info("Po zmianie języka w Configuration zobaczysz inny plik glossary (osobny dla każdego języka).")

st.write("Podgląd (pierwsze 30):")
st.dataframe(edited.head(30), use_container_width=True)
