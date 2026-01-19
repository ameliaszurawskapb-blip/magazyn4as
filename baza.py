import os
import base64

import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client


# =========================
# Helpers (pliki/obrazy)
# =========================
def safe_path(rel_path: str) -> str:
    """Ścieżka względna do katalogu z tym plikiem .py (działa na Streamlit Cloud)."""
    return os.path.join(os.path.dirname(__file__), rel_path)


def sidebar_image_fixed_height(path: str, height_px: int = 260):
    """Wyświetl obrazek w sidebarze w stałej wysokości (bez 'skakania')."""
    with open(safe_path(path), "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    ext = path.split(".")[-1].lower()
    if ext in ("jpg", "jpeg"):
        mime = "jpeg"
    elif ext in ("png", "webp", "gif"):
        mime = ext
    else:
        mime = "png"

    st.sidebar.markdown(
        f"""
        <div style="width:100%; height:{height_px}px; display:flex; align-items:center; justify-content:center;">
          <img src="data:image/{mime};base64,{data}"
               style="max-width:100%; max-height:100%; object-fit:contain;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# Supabase init
# =========================
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase = get_supabase()


# =========================
# DB functions
# =========================
@st.cache_data(ttl=10)
def fetch_kategorie():
    resp = supabase.table("kategorie").select("id,nazwa,opis").order("id").execute()
    return resp.data or []


@st.cache_data(ttl=10)
def fetch_produkty_raw():
    resp = supabase.table("produkty").select("id,nazwa,liczba,cena,kategoria_id").order("id").execute()
    return resp.data or []


@st.cache_data(ttl=10)
def fetch_produkty_join():
    prods = fetch_produkty_raw()
    kats = fetch_kategorie()

    kat_map = {k["id"]: k.get("nazwa") for k in kats}

    rows = []
    for p in prods:
        liczba = p.get("liczba") or 0
        cena = p.get("cena") or 0.0
        rows.append(
            {
                "id": p.get("id"),
                "nazwa": p.get("nazwa"),
                "liczba": int(liczba),
                "cena": float(cena),
                "kategoria": kat_map.get(p.get("kategoria_id")),
                "wartosc": float(liczba) * float(cena),
            }
        )
    return rows


def add_kategoria(nazwa, opis):
    supabase.table("kategorie").insert({"nazwa": nazwa, "opis": opis}).execute()


def add_produkt(nazwa, liczba, cena, kategoria_id):
    supabase.table("produkty").insert(
        {
            "nazwa": nazwa,
            "liczba": int(liczba),
            "cena": float(cena),
            "kategoria_id": int(kategoria_id) if kategoria_id is not None else None,
        }
    ).execute()


def update_produkt(prod_id, nazwa, liczba, cena, kategoria_id):
    supabase.table("produkty").update(
        {
            "nazwa": nazwa,
            "liczba": int(liczba),
            "cena": float(cena),
            "kategoria_id": int(kategoria_id) if kategoria_id is not None else None,
        }
    ).eq("id", int(prod_id)).execute()


def delete_produkt(prod_id):
    supabase.table("produkty").delete().eq("id", int(prod_id)).execute()


def delete_kategoria(kat_id):
    supabase.table("kategorie").delete().eq("id", int(kat_id)).execute()


def refresh():
    st.cache_data.clear()
    st.rerun()


# =========================
# UI
# =========================
st.set_page_config(page_title="Magazyn Pro", layout="wide")

st.sidebar.title("⚙️ Ustawienia")
limit_niskiego_stanu = st.sidebar.number_input("Próg niskiego stanu", value=5, min_value=0)

menu = [
    "🏠 Dashboard",
    "📋 Podgląd Danych",
    "✏️ Edytuj produkt",
    "➕ Dodaj Kategorię",
    "➕ Dodaj Produkt",
    "🗑️ Usuń Element",
]
choice = st.sidebar.selectbox("Menu", menu)

# Tryb świąteczny (tylko obrazek w sidebarze)
if "tryb_swiateczny" not in st.session_state:
    st.session_state.tryb_swiateczny = False

st.sidebar.markdown("---")
st.session_state.tryb_swiateczny = st.sidebar.checkbox("🎄 Tryb świąteczny", value=st.session_state.tryb_swiateczny)

# Obrazek pod menu
# Jeśli trzymasz obrazki w root, użyj: "obrazek1.png"/"obrazek2.png"
img_path = "assets/obrazek2.png" if st.session_state.tryb_swiateczny else "assets/obrazek1.png"
sidebar_image_fixed_height(img_path, height_px=260)

# Dane do DF (dla dashboardu i podglądu)
df = pd.DataFrame(fetch_produkty_join())


# =========================
# Views
# =========================
if choice == "🏠 Dashboard":
    st.title("📊 Analityka Magazynowa")

    col1, col2, col3 = st.columns(3)
    if df.empty:
        total_value = 0.0
        total_items = 0
        low_stock_count = 0
    else:
        total_value = float(df["wartosc"].sum())
        total_items = int(df["liczba"].sum())
        low_stock_count = int(df[df["liczba"] <= limit_niskiego_stanu].shape[0])

    col1.metric("Całkowita wartość", f"{total_value:,.2f} zł")
    col2.metric("Liczba produktów (szt.)", total_items)
    col3.metric("Niski stan (alerty)", low_stock_count, delta_color="inverse")

    st.divider()

    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("Udział wartości w kategoriach")
        if not df.empty and df["wartosc"].sum() > 0:
            df_plot = df.copy()
            df_plot["kategoria"] = df_plot["kategoria"].fillna("Brak kategorii")
            fig = px.pie(df_plot, values="wartosc", names="kategoria", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych do wyświetlenia wykresu.")

    with right_col:
        st.subheader("⚠️ Alerty niskiego stanu")
        if not df.empty:
            low_stock_df = df[df["liczba"] <= limit_niskiego_stanu][["nazwa", "liczba"]]
        else:
            low_stock_df = pd.DataFrame(columns=["nazwa", "liczba"])

        if not low_stock_df.empty:
            st.error(f"Poniżej progu ({limit_niskiego_stanu} szt.):")
            st.table(low_stock_df)
        else:
            st.success("Wszystkie stany w normie.")

elif choice == "📋 Podgląd Danych":
    st.header("Lista produktów")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Pobierz CSV",
        data=csv,
        file_name="produkty.csv",
        mime="text/csv",
    )

elif choice == "✏️ Edytuj produkt":
    st.header("✏️ Edytuj produkt")

    prods = fetch_produkty_raw()
    if not prods:
        st.info("Brak produktów do edycji.")
    else:
        prod_labels = {f'{p["id"]} — {p["nazwa"]}': p for p in prods}
        selected_label = st.selectbox("Wybierz produkt", list(prod_labels.keys()))
        p = prod_labels[selected_label]

        kategorie = fetch_kategorie()
        kat_options = {k["nazwa"]: k["id"] for k in kategorie} if kategorie else {}
        kat_names = list(kat_options.keys()) if kat_options else ["(brak kategorii)"]

        default_kat_name = None
        if kat_options and p.get("kategoria_id") is not None:
            for name, kid in kat_options.items():
                if kid == p.get("kategoria_id"):
                    default_kat_name = name
                    break

        default_index = kat_names.index(default_kat_name) if default_kat_name in kat_names else 0

        with st.form("edit_prod_form"):
            nazwa = st.text_input("Nazwa produktu", value=p.get("nazwa") or "")
            liczba = st.number_input("Liczba (szt.)", min_value=0, step=1, value=int(p.get("liczba") or 0))
            cena = st.number_input("Cena", min_value=0.0, format="%.2f", value=float(p.get("cena") or 0.0))
            kat_name = st.selectbox("Kategoria", kat_names, index=default_index)
            submit = st.form_submit_button("Zapisz zmiany")

        if submit:
            if not nazwa.strip():
                st.warning("Podaj nazwę produktu.")
            else:
                new_kat_id = kat_options.get(kat_name) if kat_options else None
                update_produkt(p["id"], nazwa.strip(), liczba, cena, new_kat_id)
                st.success("Zapisano zmiany.")
                refresh()

elif choice == "➕ Dodaj Kategorię":
    st.header("Dodawanie nowej kategorii")

    with st.form("form_kat"):
        nazwa = st.text_input("Nazwa kategorii")
        opis = st.text_area("Opis")
        submit = st.form_submit_button("Zapisz kategorię")

    if submit:
        if not nazwa.strip():
            st.warning("Podaj nazwę kategorii.")
        else:
            add_kategoria(nazwa.strip(), opis.strip() if opis else None)
            st.success(f"Dodano kategorię: {nazwa.strip()}")
            refresh()

elif choice == "➕ Dodaj Produkt":
    st.header("Dodawanie nowego produktu")

    kategorie = fetch_kategorie()
    if not kategorie:
        st.warning("Najpierw dodaj kategorię!")
    else:
        kat_options = {k["nazwa"]: k["id"] for k in kategorie}

        with st.form("form_prod"):
            nazwa = st.text_input("Nazwa produktu")
            liczba = st.number_input("Liczba (szt.)", min_value=0, step=1, value=0)
            cena = st.number_input("Cena", min_value=0.0, format="%.2f", value=0.0)
            kat_name = st.selectbox("Kategoria", list(kat_options.keys()))
            submit = st.form_submit_button("Zapisz produkt")

        if submit:
            if not nazwa.strip():
                st.warning("Podaj nazwę produktu.")
            else:
                add_produkt(nazwa.strip(), liczba, cena, kat_options[kat_name])
                st.success(f"Dodano produkt: {nazwa.strip()}")
                refresh()

elif choice == "🗑️ Usuń Element":
    st.header("Usuwanie")
    st.info("Wybierz odpowiednią zakładkę poniżej")

    t1, t2 = st.tabs(["Produkt", "Kategoria"])

    with t1:
        prods_rows = fetch_produkty_raw()
        if not prods_rows:
            st.info("Brak produktów do usunięcia.")
        else:
            prod_map = {f'{p["id"]} — {p["nazwa"]}': p["id"] for p in prods_rows}
            prod_label = st.selectbox("Wybierz produkt", list(prod_map.keys()))
            if st.button("Usuń produkt", type="primary"):
                delete_produkt(prod_map[prod_label])
                st.success("Produkt usunięty.")
                refresh()

    with t2:
        kats_rows = fetch_kategorie()
        if not kats_rows:
            st.info("Brak kategorii do usunięcia.")
        else:
            kat_map = {f'{k["id"]} — {k["nazwa"]}': k["id"] for k in kats_rows}
            kat_label = st.selectbox("Wybierz kategorię", list(kat_map.keys()))
            if st.button("Usuń kategorię", type="primary"):
                try:
                    delete_kategoria(kat_map[kat_label])
                    st.success("Kategoria usunięta.")
                    refresh()
                except Exception as e:
                    st.error("Nie udało się usunąć kategorii. Jeśli są produkty przypisane do tej kategorii, usuń je najpierw.")
                    st.caption(str(e))
