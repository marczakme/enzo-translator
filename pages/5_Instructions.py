import streamlit as st

st.set_page_config(page_title="Instructions", layout="wide")
st.header("5) Instrukcja korzystania z Enzo Translatora")

st.markdown(
    """
## Cel narzędzia
To narzędzie służy do **precyzyjnego tłumaczenia treści z języka polskiego** na wybrane języki,
z zachowaniem **spójnej terminologii branżowej**, naturalnej gramatyki oraz automatycznej
**kontroli jakości (review)**.

Narzędzie zostało zaprojektowane tak, aby można było **bezpiecznie publikować tłumaczenia**,
nawet jeśli nie znasz języka docelowego.

---

## Zalecany proces pracy (skrót)
1. **Configuration** – wybierz język / rynek i kontekst.
2. **Glossary** – uzupełnij kluczowe terminy (`term_target`, `locked`).
3. **Translate** – wykonaj tłumaczenie + review.
4. **QA** – sprawdź alerty i werdykt.
5. **Archive** – pobierz zapisany plik TXT.

---

## 1) Configuration — ustawienia języka i kontekstu
W tej zakładce:
- wybierasz **język / rynek docelowy**,
- (opcjonalnie) podajesz **kontekst stylistyczny** (np. „sprzęt fryzjerski, ton profesjonalny, bez marketingowego lania wody”).

⚠️ Zawsze zaczynaj od Configuration — wszystkie kolejne zakładki działają **per wybrany język**.

---

## 2) Glossary — kluczowy element jakości tłumaczeń
Glossary to Twoja **baza wiedzy terminologicznej** (PL → język docelowy).

Każdy wpis składa się z:
- `term_pl` – termin po polsku,
- `term_target` – odpowiednik w języku docelowym,
- `locked` – wymuszenie konsekwentnego użycia pojęcia,
- `notes` – opcjonalne notatki.

---

## Jak poprawnie uzupełniać `term_target`

### Najważniejsza zasada
> **`term_target` ma być najlepszym możliwym odpowiednikiem branżowym danego pojęcia,  
> a nie jego dosłownym tłumaczeniem językowym.**

Oznacza to, że:
- wybierasz termin **używany realnie w branży** na danym rynku,
- kierujesz się **funkcją i znaczeniem**, a nie literalnym przekładem,
- unikasz określeń zbyt ogólnych lub słownikowych.

### Przykłady
**Dobrze (branżowo):**
- fotel fryzjerski → *Friseurstuhl*
- myjnia fryzjerska → *Friseurwaschplatz*

**Źle (zbyt ogólnie):**
- fotel fryzjerski → *chair*
- myjnia fryzjerska → *wash station*

### Jak wybrać dobry `term_target`
1. Zrozum **znaczenie po polsku** (do czego służy ten element).
2. Sprawdź **jak nazywają go lokalne sklepy branżowe**.
3. Wybierz **jedno, najczęściej używane określenie**.
4. Stosuj je **konsekwentnie**.

---

## Jak używać `locked` razem z `term_target`

### Kiedy ustawić `locked = True`
Ustaw `locked = True`, gdy termin:
- ✅ jest **kluczowy dla produktu lub kategorii**,
- ✅ ma **konkretne znaczenie techniczne lub branżowe**,
- ✅ **nie powinien być zastępowany synonimami**.

**Typowe przykłady terminów „locked”:**
- fotel fryzjerski
- myjnia fryzjerska
- regulacja wysokości
- tapicerka
- dezynfekcja / sterylizacja (ważna różnica znaczeniowa)

---

### Co dokładnie robi `locked`
- system **zawsze używa tego samego pojęcia** (`term_target`),
- **nie zastępuje go synonimami**,
- **pozwala na naturalną odmianę gramatyczną**.

> **`locked` nie blokuje odmiany — blokuje tylko wybór pojęcia.**

Przykład (język fleksyjny):
- `term_target`: *Friseurstuhl*
- poprawne formy w tekście:  
  *Friseurstuhl*, *Friseurstuhls*, *Friseurstühle*

---

### Czego `locked` NIE robi
- ❌ nie wymusza jednej sztywnej formy słowa,
- ❌ nie psuje naturalności języka,
- ❌ nie zastępuje gramatyki.

---

## 3) Translate — tłumaczenie + review + zapis
W zakładce **Translate**:
- wprowadzasz:
  - **Nazwa (PL)** – np. nazwa produktu,
  - **Dalsza treść (PL)** – opis, parametry, informacje techniczne.
- klikasz **Translate (auto-review + save TXT)**.

System automatycznie:
1. wykonuje tłumaczenie z Glossary,
2. przeprowadza **review językowe** (werdykt OK / FIX),
3. sprawdza:
   - brak wymuszonych terminów (`locked`),
   - zgodność liczb i jednostek,
4. zapisuje wynik do **archiwum jako plik TXT z datą**.

---

## Jak interpretować wyniki
- **VERDICT: OK** + brak czerwonych alertów  
  → tłumaczenie zwykle **gotowe do publikacji**.
- **VERDICT: FIX** lub alerty  
  → popraw Glossary lub treść i przetłumacz ponownie.

---

## 6) Translations Archive — archiwum tłumaczeń
W archiwum:
- każda wersja językowa ma **osobną zakładkę**,
- widzisz:
  - liczbę wykonanych tłumaczeń,
  - datę ostatniego tłumaczenia,
- możesz pobrać **plik TXT** zawierający:
  - treść PL,
  - tłumaczenie,
  - raport review,
  - datę wykonania.

---

## Dobre praktyki (bardzo polecane)
- Zacznij od Glossary (min. 30–80 kluczowych terminów `locked` na język).
- Przy nowym języku zrób kilka pierwszych tłumaczeń „testowych”.
- Jeśli widzisz powtarzający się błąd — **dodaj go do Glossary**, zamiast poprawiać ręcznie.
"""
)

st.info(
    "Wskazówka: jakość tłumaczeń rośnie wraz z jakością Glossary. "
    "Dobrze uzupełnione Glossary to mniej poprawek i większe zaufanie do publikacji."
)
