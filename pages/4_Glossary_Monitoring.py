import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Glossary Monitoring", layout="wide")
st.header("4) Glossary — Monitoring")

st.caption("Podgląd stanu glossary per język: liczba fraz + data ostatniej aktualizacji pliku.")

DATA_DIR = "data"

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

def fmt_mtime(ts: float) -> str:
    # ładny format daty; jeśli nie istnieje plik — pusto
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

rows = []

for code, label in LANGS:
    path = os.path.join(DATA_DIR, f"glossary_{code}.csv")

    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            # liczba fraz = liczba unikalnych term_pl (bez pustych)
            if "term_pl" in df.columns:
                term_pl = df["term_pl"].astype(str).str.strip()
                count_phrases = int((term_pl.str.len() > 0).sum())
            else:
                count_phrases = 0

            # bonus metryki (pomocne w kontroli)
            filled = 0
            if "term_target" in df.columns and "term_pl" in df.columns:
                term_target = df["term_target"].astype(str).str.strip()
                filled = int((term_target.str.len() > 0).sum())

            locked = 0
            if "locked" in df.columns:
                # może być True/False albo 1/0
                locked = int(pd.Series(df["locked"]).astype(str).str.lower().isin(["true", "1", "yes", "y", "t"]).sum())

            mtime = os.path.getmtime(path)
            last_update = fmt_mtime(mtime)

            status = "OK"
        except Exception as e:
            count_phrases = 0
            filled = 0
            locked = 0
            last_update = ""
            status = f"ERROR: {e}"
    else:
        count_phrases = 0
        filled = 0
        locked = 0
        last_update = ""
        status = "Brak pliku"

    rows.append({
        "Język": label,
        "Kod": code,
        "Liczba fraz (wierszy)": count_phrases,
        "Uzupełnione tłumaczenia": filled,
        "Locked": locked,
        "Ostatnia aktualizacja": last_update,
        "Status": status,
        "Plik": path,
    })

report = pd.DataFrame(rows)

# sort: najpierw te z plikami i największą liczbą fraz
report["__has_file"] = report["Status"].apply(lambda x: 1 if x == "OK" else 0)
report = report.sort_values(["__has_file", "Liczba fraz (wierszy)"], ascending=[False, False]).drop(columns=["__has_file"])

st.dataframe(report, use_container_width=True)

st.download_button(
    "⬇️ Pobierz raport (CSV)",
    data=report.to_csv(index=False).encode("utf-8"),
    file_name="glossary_monitoring.csv",
    mime="text/csv"
)

st.info("Tip: jeśli Status = 'Brak pliku', oznacza to, że glossary dla danego języka nie zostało jeszcze zapisane (Save glossary lub import).")
