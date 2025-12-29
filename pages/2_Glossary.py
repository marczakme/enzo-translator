import streamlit as st
import pandas as pd
import os
from datetime import datetime
import shutil

st.set_page_config(page_title="Glossary", layout="wide")
st.header("2) Glossary (PL → język docelowy)")

# -------------------------
# Wymagamy języka/rynku
# -------------------------
target_lang = st.session_state.get("target_language")
target_label = st.session_state.get("target_market_label")

if not target_lang or not target_label:
    st.warning("Najpierw wybierz język/rynek w zakładce Configuration.")
    st.stop()

st.subheader(f"Edytujesz glossary dla: {target_label} (lang={target_lang})")

# -------------------------
# Ścieżki plików
# -------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BACKUP_DIR = os.path.join(DATA_DIR, "backup")
os.makedirs(BACKUP_DIR, exist_ok=True)

glossary_path = os.path.join(DATA_DIR, f"glossary_{target_lang}.csv")

DEFAULT_ROWS = [
    {"term_pl": "fotel fryzjerski", "term_target": "", "locked": True, "notes": ""},
    {"term_pl": "myjnia fryzjerska", "term_target": "", "locked": True, "notes": ""},
]

REQUIRED_COLS = ["term_pl", "term_target", "locked", "notes"]

# -------------------------
# Helpers
# -------------------------
def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ujednolica kolumny, typy, trim, usuwa puste i deduplikuje po term_pl."""
    df = df.copy()

    # ujednolicenie nazw kolumn
    df.columns = [str(c).strip().lower() for c in df.columns]

    # mapowanie alternatywnych nazw (importy z różnych źródeł)
    rename_map = {
        "pl": "term_pl",
        "source": "term_pl",
        "term_source": "term_pl",
        "term": "term_pl",
        "target": "term_target",
        "translation": "term_target",
        "is_locked": "locked",
    }
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # uzupełnij brakujące kolumny
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = "" if col != "locked" else False

    df = df[REQUIRED_COLS]

    # typy i czyszczenie
    df["term_pl"] = df["term_pl"].astype(str).str.strip()
    df["term_target"] = df["term_target"].astype(str).str.strip()
    df["notes"] = df["notes"].astype(str)
    # locked bywa "TRUE"/"FALSE" albo 1/0; bool() na stringu nie zadziała jak chcesz,
    # więc robimy mapowanie bezpieczne:
    df["locked"] = df["locked"].apply(lambda x: str(x).strip().lower() in ["true", "1", "yes", "y", "t"])

    # usuń puste term_pl
    df = df[df["term_pl"].str.len() > 0].copy()

    # deduplikacja po term_pl: zostaw ostatni (import ma priorytet)
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
    """MERGE: łączy po term_pl, import ma priorytet (nadpisuje duplikaty)."""
    ex = normalize_df(existing)
    im = normalize_df(imported)
    merged = pd.concat([ex, im], ignore_index=True)
    merged = merged.drop_duplicates(subset=["term_pl"], keep="last").reset_index(drop=True)
    return merged


def backup_glossary(path: str, lang: str):
    """Backup obecnego glossary przed overwrite."""
    if not os.path.exists(path):
        return None
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"glossary_{lang}_{ts}.csv"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(path, backup_path)
    return backup_path


# -------------------------
# Session state per język
# -------------------------
state_key = f"glossary_df_{target_lang}"
if state_key not in st.session_state:
    st.session_state[state_key] = load_glossary(glossary_path)

# -------------------------
# Instrukcja dla użytkowników (UI)
# -------------------------
st.info(
    """
### Jak wybrać tryb importu?

**Scal (merge) — ZALECANE (najbezpieczniejsze)**
- dodajesz nowe frazy
- poprawiasz istniejące tłumaczenia
- chcesz zachować wcześniejszą pracę  
➡️ nic nie ginie; jeśli `term_pl` się powtarza, import **nadpisze** jego tłumaczenie

**Nadpisz (overwrite) — OSTROŻNIE**
- zastępuje CAŁE glossary dla tego języka
- używaj tylko przy pełnym resecie lub gdy CSV ma kompletną, finalną wersję  
➡️ aplikacja automatycznie robi **backup** poprzedniej wersji do `/data/backup`
"""
)

# -------------------------
# Import / Export
# -------------------------
st.markdown("### Import / Export")

c1, c2, c3 = st.columns([2, 3, 3])

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
        help="CSV powinien mieć kolumny: term_pl, term_target, locked, notes (locked: True/False lub 1/0)."
    )

with c3:
    import_mode = st.radio(
        "Tryb importu",
        options=[
            "Scal (merge) — nadpisuj te same term_pl",
            "Nadpisz (overwrite) — zastąp cały glossary",
        ],
        index=0
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
                st.info("Zastosowano MERGE: zachowano istniejące terminy, a duplikaty zaktualizowano.")
            else:
                backup_path = backup_glossary(glossary_path, target_lang)
                new_df = imported_df
                if backup_path:
                    st.warning(f"OVERWRITE: wykonano backup poprzedniego glossary → {backup_path}")
                else:
                    st.warning("OVERWRITE: nie było wcześniejszego pliku do zbackupowania (to pierwszy zapis).")

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
