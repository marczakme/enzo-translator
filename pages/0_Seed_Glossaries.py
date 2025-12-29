import streamlit as st
import pandas as pd
import os
import re

st.set_page_config(page_title="Seed Glossaries", layout="wide")
st.header("0) Seed glossaries — baza PL terminów dla wszystkich języków")

st.markdown(
    """
Ta strona służy do jednorazowego (lub okresowego) **uzupełniania wszystkich glossary** o bazową listę polskich terminów.

✅ Co robi:
- dla każdego języka dopisuje brakujące `term_pl` z pliku
- nie kasuje istniejących tłumaczeń

❌ Czego nie robi:
- nie wypełnia `term_target` automatycznie
- nie zmienia istniejących wpisów
"""
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

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

REQUIRED_COLS = ["term_pl", "term_target", "locked", "notes"]

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # mapowanie nazw (gdyby plik był w innym formacie)
    rename_map = {
        "pl": "term_pl",
        "source": "term_pl",
        "term": "term_pl",
        "target": "term_target",
        "translation": "term_target",
        "is_locked": "locked",
    }
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = "" if col != "locked" else False

    df = df[REQUIRED_COLS]
    df["term_pl"] = df["term_pl"].astype(str).str.strip()
    df["term_target"] = df["term_target"].astype(str).str.strip()
    df["notes"] = df["notes"].astype(str)
    df["locked"] = df["locked"].apply(lambda x: str(x).strip().lower() in ["true", "1", "yes", "y", "t"])

    df = df[df["term_pl"].str.len() > 0].copy()
    df = df.drop_duplicates(subset=["term_pl"], keep="last").reset_index(drop=True)
    return df

def load_glossary(lang_code: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"glossary_{lang_code}.csv")
    if os.path.exists(path):
        return normalize_df(pd.read_csv(path))
    return pd.DataFrame(columns=REQUIRED_COLS)

def save_glossary(lang_code: str, df: pd.DataFrame):
    path = os.path.join(DATA_DIR, f"glossary_{lang_code}.csv")
    df = normalize_df(df)
    df.to_csv(path, index=False)

def parse_terms_csv(uploaded_file) -> list[str]:
    # Wspieramy najprostszy format: 1 kolumna, z nagłówkiem lub bez
    df = pd.read_csv(uploaded_file, header=None)
    raw = df.iloc[:, 0].astype(str).tolist()

    terms = []
    for t in raw:
        t = t.strip()
        t = re.sub(r"\s+", " ", t)
        t = t.rstrip(",;")
        if t and t not in terms:
            terms.append(t)

    return terms

uploaded = st.file_uploader(
    "Wgraj CSV z bazą polskich terminów (1 kolumna, po jednym terminie na wiersz)",
    type=["csv"]
)

mode = st.radio(
    "Tryb działania",
    [
        "Dopisz brakujące term_pl (bezpieczne, zalecane)",
        "Resetuj term_target i dopisz bazę (UWAGA: czyści tłumaczenia!)"
    ],
    index=0
)

if uploaded is not None:
    try:
        terms = parse_terms_csv(uploaded)
        st.success(f"Wczytano {len(terms)} terminów.")
        st.write("Podgląd (pierwsze 25):")
        st.write(terms[:25])

        if st.button("Seed ALL languages", type="primary"):
            report_rows = []

            for code, label in LANGS:
                existing = load_glossary(code)

                if mode.startswith("Resetuj"):
                    # czyścimy tłumaczenia, ale zachowujemy strukturę term_pl
                    existing["term_target"] = ""
                    existing["locked"] = False
                    existing["notes"] = ""

                existing_pl = set(existing["term_pl"].astype(str).str.strip().tolist())

                add_rows = []
                for t in terms:
                    if t not in existing_pl:
                        add_rows.append({"term_pl": t, "term_target": "", "locked": False, "notes": ""})

                new_df = pd.concat([existing, pd.DataFrame(add_rows)], ignore_index=True)
                save_glossary(code, new_df)

                report_rows.append({
                    "Język": label,
                    "Kod": code,
                    "Istniało": int(len(existing)),
                    "Dodano (bazowe terminy)": int(len(add_rows)),
                    "Po zapisie": int(len(new_df)),
                })

            st.success("Zrobione ✅ Zasiano glossary dla wszystkich języków.")
            st.dataframe(pd.DataFrame(report_rows), use_container_width=True)

    except Exception as e:
        st.error(f"Błąd parsowania CSV: {e}")
else:
    st.info("Wgraj CSV, żeby rozpocząć.")
