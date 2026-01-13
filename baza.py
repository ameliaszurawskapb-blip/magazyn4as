import streamlit as st
import sqlite3
import pandas as pd

# --- KONFIGURACJA BAZY DANYCH ---
def init_db():
    conn = sqlite3.connect('magazyn.db', check_same_thread=False)
    c = conn.cursor()
    # Tabela Kategorie: id, nazwa, opis
    c.execute('''CREATE TABLE IF NOT EXISTS kategorie 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nazwa TEXT NOT NULL, 
                  opis TEXT)''')
    
    # Tabela Produkty: id, nazwa, liczba, cena, kategoria_id
    c.execute('''CREATE TABLE IF NOT EXISTS produkty 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nazwa TEXT NOT NULL, 
                  liczba INTEGER DEFAULT 0, 
                  cena REAL DEFAULT 0.0, 
                  kategoria_id INTEGER, 
                  FOREIGN KEY(kategoria_id) REFERENCES kategorie(id))''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- INTERFEJS STREAMLIT ---
st.set_page_config(page_title="Zarządzanie Magazynem", layout="wide")
st.title("📦 System Zarządzania Produktami")

menu = ["Podgląd Danych", "Dodaj Kategorię", "Dodaj Produkt", "Usuń Element"]
choice = st.sidebar.selectbox("Menu Operacji", menu)

# --- 1. PODGLĄD DANYCH ---
if choice == "Podgląd Danych":
    st.header("Aktualny stan magazynu")
    
    query = '''
        SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria
        FROM produkty p
        LEFT JOIN kategorie k ON p.kategoria_id = k.id
    '''
    df = pd.read_sql_query(query, conn)
    st.dataframe(df, use_container_width=True)

# --- 2. DODAJ KATEGORIĘ ---
elif choice == "Dodaj Kategorię":
    st.header("Dodawanie nowej kategorii")
    with st.form("form_kat"):
        nazwa = st.text_input("Nazwa kategorii")
        opis = st.text_area("Opis")
        submit = st.form_submit_button("Zapisz kategorię")
        
        if submit and nazwa:
            cursor.execute("INSERT INTO kategorie (nazwa, opis) VALUES (?, ?)", (nazwa, opis))
            conn.commit()
            st.success(f"Dodano kategorię: {nazwa}")

# --- 3. DODAJ PRODUKT ---
elif choice == "Dodaj Produkt":
    st.header("Dodawanie nowego produktu")
    
    # Pobranie list kategorii do selectboxa
    kategorie = cursor.execute("SELECT id, nazwa FROM kategorie").fetchall()
    kat_options = {k[1]: k[0] for k in kategorie}

    if not kat_options:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię!")
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

# --- 4. USUŃ ELEMENT ---
elif choice == "Usuń Element":
    st.header("Usuwanie z bazy danych")
    tab1, tab2 = st.tabs(["Usuń Produkt", "Usuń Kategorię"])
    
    with tab1:
        prods = cursor.execute("SELECT id, nazwa FROM produkty").fetchall()
        prod_to_del = st.selectbox("Wybierz produkt", prods, format_func=lambda x: x[1])
        if st.button("Usuń wybrany produkt"):
            cursor.execute("DELETE FROM produkty WHERE id = ?", (prod_to_del[0],))
            conn.commit()
            st.warning(f"Usunięto produkt: {prod_to_del[1]}")
            st.rerun()

    with tab2:
        kats = cursor.execute("SELECT id, nazwa FROM kategorie").fetchall()
        kat_to_del = st.selectbox("Wybierz kategorię", kats, format_func=lambda x: x[1])
        st.error("Uwaga: Usunięcie kategorii może pozostawić produkty bez przypisania!")
        if st.button("Usuń wybraną kategorię"):
            cursor.execute("DELETE FROM kategorie WHERE id = ?", (kat_to_del[0],))
            conn.commit()
            st.warning(f"Usunięto kategorię: {kat_to_del[1]}")
            st.rerun()
