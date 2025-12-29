import streamlit as st

st.set_page_config(page_title="Instructions", layout="wide")
st.header("5) Instrukcja korzystania z narzędzia tłumaczeń")

st.markdown(
    """
## Cel narzędzia
To narzędzie służy do **precyzyjnego tłumaczenia treści z języka polskiego** na wybrane języki,
z zachowaniem **spójnej terminologii branżowej**, naturalnej gramatyki oraz automatycznej
**kontroli jakości (review)**.

Zostało zaprojektowane tak, aby można było **bezpiecznie publikować tłumaczenia**,
nawet jeśli nie znasz języka docelowego.

---

## Zalecany proces pracy (skrót)
1. **Seed glossaries (0)** – wgraj bazową listę polskich terminów (punkt wyjścia).
2. **Configuration (1)** – wybierz język / rynek i kontekst.
3. **Glossary (2)** – uzupełnij `term_target` i `locked`.
4. **Translate (3)** – wykonaj tłumaczenie + review.
5. **Monitoring (4)** – kontroluj stan glossary.
6. **Archive (6)** – pobierz zapisane pliki TXT.

---

## 0) Seed glossaries — baza startowa terminów PL
Ta zakładka służy do **jednorazowego lub okresowego zasiewania glossary**
tą samą listą **polskich terminów bazowych** dla **wszystkich języków**.

### Co robi Seed glossaries
- ✅ dodaje brakujące `term_pl` do każdego `glossary_{lang}.csv`,
- ✅ **nie usuwa** istniejących tłumaczeń,
- ✅ pozwala mieć **wspólny punkt wyjścia** dla wszystkich języków.

### Czego NIE robi
- ❌ nie tłumaczy automatycznie terminów,
- ❌ nie ustawia `locked`,
- ❌ nie zmienia istniejących `term_target` (w trybie domyślnym).

### Dostępne tryby
**Dopisz brakujące term_pl (zalecane)**  
- bezpieczny tryb codziennej pracy,
- dopisuje tylko brakujące polskie terminy,
- idealny jako punkt wyjścia do dalszej pracy.

**Resetuj term_target i dopisz bazę (UWAGA)**  
- czyści wszystkie tłumaczenia (`term_target`) dla danego języka,
- używaj tylko, gdy **świadomie zaczynasz od zera**.

---

## 1) Configuration — ustawienia języka i kontekstu
W tej zakładce:
- wybierasz **język / rynek docelowy**,
- (opcjonalnie) podajesz **kontekst stylistyczny**
  (np. „sprzęt fryzjerski, ton profesjonalny, bez marketingowego lania wody”).

⚠️ Zawsze zaczynaj od Configuration — wszystkie kolejne zakładki działają **per wybrany język**.

---

## 2) Glossary — kluczowy element jakości
Glossary to Twoja **baza wiedzy terminologicznej** (PL → język docelowy).

Każdy wpis zawiera:
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
- wybierasz termin **realnie używany w branży** na danym rynku,
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
1. Zrozum **znaczenie po polsku** (do czego służy termin).
2. Sprawdź **jak nazywają go lokalne sklepy branżowe**.
3. Wybierz **jedno, najczęściej stosowane określenie**.
4. Stosuj je **konsekwentnie**.

---

## Jak używać `locked` razem z `term_target`

### Kiedy ustawić `locked = True`
Ustaw `locked = True`, gdy termin:
- ✅ jest **kluczowy dla produktu lub kategorii**,
- ✅ ma **konkretne znaczenie techniczne lub branżowe**,
- ✅ **nie powinien być zastępowany synonimami**.

**Typowe przykłady:**
- fotel fryzjerski
- myjnia fryzjerska
- regulacja wysokości
- tapicerka
- dezynfekcja / sterylizacja (istotna różnica znaczeniowa)

### Co dokładnie robi `locked`
- system **zawsze używa tego samego pojęcia** (`term_target`),
- **nie zastępuje go synonimami**,
- **pozwala na naturalną odmianę gramatyczną**.

> **`locked` nie blokuje odmiany — blokuje tylko wybór pojęcia.**

---

## 3) Translate — tłumaczenie + review + zapis
W tej zakładce:
- wprowadzasz:
  - **Nazwa (PL)**,
  - **Dalsza treść (PL)**.
- klikasz **Translate (auto-review + save TXT)**.

System:
1. wykonuje tłumaczenie z Glossary,
2. przeprowadza **review językowe** (OK / FIX),
3. sprawdza:
   - brak terminów `locked`,
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
  - liczbę tłumaczeń,
  - datę ostatniego tłumaczenia,
- możesz pobrać **plik TXT** zawierający:
  - treść PL,
  - tłumaczenie,
  - raport review,
  - datę wykonania.

---

## Dobre praktyki (polecane)
- Zacznij od Seed glossaries (wspólny punkt wyjścia).
- Uzupełnij min. **30–80 kluczowych terminów `locked`** na język.
- Przy nowym języku wykonaj kilka tłumaczeń testowych.
- Jeśli widzisz powtarzalny błąd — **dodaj termin do Glossary**, zamiast poprawiać ręcznie.
"""
)

st.info(
    "Im lepiej uzupełnione Glossary, tym większa spójność i mniejsza potrzeba ręcznych poprawek. "
    "Glossary to fundament jakości całego procesu."
)
