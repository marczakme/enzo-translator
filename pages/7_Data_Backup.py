import streamlit as st
import os
import io
import zipfile
from datetime import datetime

st.set_page_config(page_title="Data Backup (ZIP)", layout="wide")
st.header("⚠️ 7) Data Backup — eksport danych (ZIP)")

st.markdown(
    """
Ta zakładka umożliwia **ręczny eksport wszystkich danych roboczych**
(glossary, tłumaczenia, archiwa, backupy) do **jednego pliku ZIP**.

⚠️ **Zalecenie:**  
Pobierz ZIP **zawsze po zakończeniu pracy**, zanim zamkniesz aplikację.
"""
)

DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    st.warning("Brak katalogu `data/` — nie ma czego eksportować.")
    st.stop()

def build_zip():
    buffer = io.BytesIO()
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_name = f"enzo-translator-backup-{ts}.zip"

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(DATA_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, DATA_DIR)
                zipf.write(full_path, arcname)

    buffer.seek(0)
    return zip_name, buffer

st.divider()

if st.button("⬇️ Pobierz backup ZIP", type="primary"):
    zip_name, zip_buffer = build_zip()

    st.download_button(
        label="📦 Download ZIP",
        data=zip_buffer,
        file_name=zip_name,
        mime="application/zip"
    )

    st.success("Backup ZIP wygenerowany. Zapisz go lokalnie lub dodaj do repozytorium.")

st.divider()

st.info(
    """
### Co zawiera backup?
- wszystkie `glossary_*.csv`
- wszystkie zapisane tłumaczenia `.txt`
- pliki indeksów tłumaczeń
- backupy glossary

### Czego backup NIE robi
- nie zapisuje danych automatycznie do GitHuba
- nie zastępuje commitów (ZIP to kopia bezpieczeństwa)

➡️ **Najlepsza praktyka:**  
ZIP + commit do repo = pełne bezpieczeństwo.
"""
)

