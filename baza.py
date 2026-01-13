import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# --- KONFIGURACJA BAZY DANYCH ---
def init_db():
    conn = sqlite3.connect('magazyn.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS kategorie 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT NOT NULL, opis TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS produkty 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT NOT NULL, 
                  liczba INTEGER DEFAULT 0, cena REAL DEFAULT 0.0, kategoria_id INTEGER, 
                  FOREIGN KEY(kategoria_id) REFERENCES kategorie(id))''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- INTERFEJS ---
st.set_page_config(page_title="Magazyn Pro", layout="wide")

# Sidebar - Ustawienia alertów
st.sidebar.title("⚙️ Ustawienia")
limit_niskiego_stanu = st.sidebar.number_input("Próg niskiego stanu", value=5, min_value=0)

menu = ["🏠 Dashboard", "📋 Podgląd Danych", "➕ Dodaj Kategorię", "➕ Dodaj Produkt", "🗑️ Usuń Element"]
choice = st.sidebar.selectbox("Menu", menu)

# Pobieranie danych do DataFrame (potrzebne w wielu miejscach)
query = '''
    SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria, (p.liczba * p.cena) as wartosc
    FROM produkty p
    LEFT JOIN kategorie k ON p.kategoria_id = k.id
'''
df = pd.read_sql_query(query, conn)

# --- 1. DASHBOARD (NOWOŚĆ) ---
if choice == "🏠 Dashboard":
    st.title("📊 Analityka Magazynowa")
    
    # Metryki ogólne
    col1, col2, col3 = st.columns(3)
    total_value = df['wartosc'].sum()
    total_items = df['liczba'].sum()
    low_stock_count = df[df['liczba'] <= limit_niskiego_stanu].shape[0]
    
    col1.metric("Całkowita wartość", f"{total_value:,.2f} zł")
    col2.metric("Liczba produktów (szt.)", int(total_items))
    col3.metric("Niski stan (alerty)", low_stock_count, delta_color="inverse")

    st.divider()

    # Wykresy i Alerty
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("Udział wartości w kategoriach")
        if not df.empty:
            fig = px.pie(df, values='wartosc', names='kategoria', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych do wyświetlenia wykresu.")

    with right_col:
        st.subheader("⚠️ Alerty niskiego stanu")
        low_stock_df = df[df['liczba'] <= limit_niskiego_stanu][['nazwa', 'liczba']]
        if not low_stock_df.empty:
            st.error(f"Poniżej progu ({limit_niskiego_stanu} szt.):")
            st.table(low_stock_df)
        else:
            st.success("Wszystkie stany w normie.")

# --- 2. PODGLĄD DANYCH ---
elif choice == "📋 Podgląd Danych":
    st.header("Lista produktów")
    st.dataframe(df, use_container_width=True)

# --- RESZTA FUNKCJI (DODAWANIE/USUWANIE) ---
# ... (Kod z poprzedniej odpowiedzi dla Dodaj Kategorię / Dodaj Produkt / Usuń Element)
# [Wstaw tutaj sekcje Dodaj Kategorię, Dodaj Produkt i Usuń z poprzedniego kodu]

elif choice == "➕ Dodaj Kategorię":
    st.header("Dodawanie nowej kategorii")
    with st.form("form_kat"):
        nazwa = st.text_input("Nazwa kategorii")
        opis = st.text_area("Opis")
        submit = st.form_submit_button("Zapisz kategorię")
        if submit and nazwa:
            cursor.execute("INSERT INTO kategorie (nazwa, opis) VALUES (?, ?)", (nazwa, opis))
            conn.commit()
            st.success(f"Dodano kategorię: {nazwa}")
            st.rerun()

elif choice == "➕ Dodaj Produkt":
    st.header("Dodawanie nowego produktu")
    kategorie = cursor.execute("SELECT id, nazwa FROM kategorie").fetchall()
    kat_options = {k[1]: k[0] for k in kategorie}
    if not kat_options:
        st.warning("Najpierw dodaj kategorię!")
    else:
        with st.form("form_prod"):
            nazwa = st.text_input("Nazwa produktu")
            liczba = st.number_input("Liczba (szt.)", min_value=0, step=1)
            cena = st.number_input("Cena", min_value=0.0, format="%.2f")
            kat_name = st.selectbox("Kategoria", list(kat_options.keys()))
            submit = st.form_submit_button("Zapisz produkt")
            if submit and nazwa:
                cursor.execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?, ?, ?, ?)",
                               (nazwa, liczba, cena, kat_options[kat_name]))
                conn.commit()
                st.success(f"Dodano produkt: {nazwa}")
                st.rerun()

elif choice == "🗑️ Usuń Element":
    st.header("Usuwanie")
    # Logika usuwania (identyczna jak w poprzednim kroku)
    st.info("Wybierz odpowiednią zakładkę poniżej")
    t1, t2 = st.tabs(["Produkt", "Kategoria"])
    with t1:
        prods = cursor.execute("SELECT id, nazwa FROM produkty").fetchall()
        p_del = st.selectbox("Wybierz produkt", prods, format_func=lambda x: x[1])
        if st.button("Usuń produkt"):
            cursor.execute("DELETE FROM produkty WHERE id=?", (p_del[0],))
            conn.commit()
            st.rerun()
    with t2:
        kats = cursor.execute("SELECT id, nazwa FROM kategorie").fetchall()
        k_del = st.selectbox("Wybierz kategorię", kats, format_func=lambda x: x[1])
        if st.button("Usuń kategorię"):
            cursor.execute("DELETE FROM kategorie WHERE id=?", (k_del[0],))
            conn.commit()
            st.rerun()
