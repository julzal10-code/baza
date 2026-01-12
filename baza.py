import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
URL = "https://etptopysjuclxdjzvphs.supabase.co"
KEY = "sb_publishable_CJoYEh1-NTpfUYI2Q_gd1g_Jprvos28"

@st.cache_resource
def init_connection():
    return create_client(URL, KEY)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Błąd połączenia z Supabase: {e}")
    st.stop()

st.set_page_config(page_title="Zarządzanie Magazynem", layout="wide") # Zmieniono na wide dla lepszej czytelności tabel
st.title("📦 System Zarządzania Produktami")

# --- 1. FILTRY W SIDEBARZE (MUSZĄ BYĆ NA GÓRZE) ---
st.sidebar.header("🔍 Filtrowanie")
search_query = st.sidebar.text_input("Szukaj produktu")

# Pobranie nazw kategorii do filtra (potrzebne do mapowania w zakładkach)
try:
    kat_data_res = supabase.table("Kategorie").select("id, nazwa").execute()
    kat_data = kat_data_res.data
    kat_map = {item['id']: item['nazwa'] for item in kat_data}
    selected_kat = st.sidebar.selectbox("Kategoria", ["Wszystkie"] + list(kat_map.values()))
except Exception:
    kat_map = {}
    selected_kat = "Wszystkie"

max_price = st.sidebar.slider("Cena do (zł)", 0, 10000, 5000)

# --- 2. ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs(["Dodaj Produkt", "➕ Dodaj Kategorię", "📊 Podgląd Bazy"])

# --- DODAWANIE KATEGORII ---
with tab2:
    st.header("Nowa Kategoria")
    with st.form("category_form", clear_on_submit=True):
        kat_nazwa = st.text_input("Nazwa kategorii")
        kat_opis = st.text_area("Opis")
        submit_kat = st.form_submit_button("Zapisz kategorię")

        if submit_kat:
            if kat_nazwa:
                try:
                    data = {"nazwa": kat_nazwa, "opis": kat_opis}
                    supabase.table("Kategorie").insert(data).execute()
                    st.success(f"Dodano kategorię: {kat_nazwa}")
                    st.rerun() # Odśwież, aby kategoria pojawiła się w filtrach
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")
            else:
                st.error("Nazwa kategorii jest wymagana!")

# --- DODAWANIE PRODUKTU ---
with tab1:
    st.header("Nowy Produkt")
    
    if not kat_map:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię w zakładce obok!")
    else:
        # Odwracamy mapowanie, aby zapisywać ID
        inv_kat_options = {v: k for k, v in kat_map.items()}
        
        with st.form("product_form", clear_on_submit=True):
            prod_nazwa = st.text_input("Nazwa produktu")
            prod_liczba = st.number_input("Liczba (sztuki)", min_value=0, step=1)
            prod_cena = st.number_input("Cena", min_value=0.0, step=0.01, format="%.2f")
            prod_kat_nazwa = st.selectbox("Kategoria", options=list(inv_kat_options.keys()))
            
            submit_prod = st.form_submit_button("Dodaj produkt")
            
            if submit_prod:
                if prod_nazwa:
                    try:
                        product_data = {
                            "nazwa": prod_nazwa,
                            "liczba": prod_liczba,
                            "cena": prod_cena,
                            "kategorie_id": inv_kat_options[prod_kat_nazwa]
                        }
                        supabase.table("Produkty").insert(product_data).execute()
                        st.success(f"Produkt '{prod_nazwa}' został dodany.")
                    except Exception as e:
                        st.error(f"Błąd podczas dodawania produktu: {e}")
                else:
                    st.error("Nazwa produktu jest wymagana!")

# --- PODGLĄD DANYCH ---
with tab3:
    st.header("Aktualny stan bazy")
    col1, col2 = st.columns([1, 2]) # col2 jest szersza dla tabeli produktów
    
    with col1:
        st.subheader("Kategorie")
        try:
            kat_view = supabase.table("Kategorie").select("id, nazwa, opis").execute()
            if kat_view.data:
                st.dataframe(kat_view.data, use_container_width=True)
            else:
                st.info("Brak kategorii.")
        except Exception as e:
            st.error(f"Błąd pobierania kategorii: {e}")
    
    with col2:
        st.subheader("Produkty")
        try:
            prod_res = supabase.table("Produkty").select("*").execute()
            if prod_res.data:
                df = pd.DataFrame(prod_res.data)

                # --- APLIKOWANIE FILTRÓW ---
                if search_query:
                    df = df[df['nazwa'].str.contains(search_query, case=False, na=False)]
                
                if selected_kat != "Wszystkie":
                    inv_kat_map = {v: k for k, v in kat_map.items()}
                    target_id = inv_kat_map.get(selected_kat)
                    df = df[df['kategorie_id'] == target_id]
                
                df = df[df['cena'] <= max_price]

                # Wyświetlanie przefiltrowanej tabeli
                st.dataframe(df, use_container_width=True)
                
                # Sekcja usuwania
                if not df.empty:
                    st.divider()
                    st.subheader("🗑️ Usuń produkt")
                    to_delete_name = st.selectbox("Wybierz produkt do usunięcia:", df['nazwa'].tolist())
                    if st.button("Usuń produkt", type="primary"):
                        id_del = int(df[df['nazwa'] == to_delete_name]['id'].values[0])
                        supabase.table("Produkty").delete().eq("id", id_del).execute()
                        st.success(f"Usunięto: {to_delete_name}")
                        st.rerun()
                else:
                    st.warning("Brak produktów spełniających kryteria filtrów.")
            else:
                st.info("Brak produktów w bazie.")
        except Exception as e:
            st.error(f"Błąd wyświetlania/filtrowania: {e}")
