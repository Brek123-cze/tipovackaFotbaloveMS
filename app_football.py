import streamlit as st
import requests
import pandas as pd
import time

from streamlit_gsheets import GSheetsConnection

# Konstanta pro tvoje ID tabulky
SPREADSHEET_ID = "1usapXQgXcDN3NDgkZz8HPHkNomCbo2sQzzXrPvjMR7U"

# Vytvoření spojení s Google Sheets (přístupové údaje konfigurujeme ve Streamlit Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

# =========================================================================
# 📥 FUNKCE PRO NAČÍTÁNÍ DAT (Čte každý list zvlášť)
# =========================================================================

@st.cache_data(ttl=300)
def nacti_fotbalova_data():
    """Načte data a v případě problému okamžitě nahlásí přesný důvod selhání"""
    URL_API = "https://script.google.com/macros/s/AKfycbypVyn-7dy9KRAvlTmRkZ7R9d66Ux9LraaSDeC0A8m0C1LGvcRmuq2lh-jlPSgbL9y1/exec"

    try:
        response = requests.get(URL_API, timeout=15)
        
        # Pokud Google vrátil kód 200 (úspěch)
        if response.status_code == 200:
            vystup = response.json()
            # Pokud nám sám Google posílá v balíčku text chyby
            if "error" in vystup:
                st.sidebar.error(f"🔴 Google skript hlásí chybu: {vystup['error']}")
            return vystup
        else:
            st.sidebar.error(f"🔴 Google server odpověděl kódem: {response.status_code}")
            return {"zapasy": [], "tipy": [], "admin": {}}
            
    except Exception as e:
        st.sidebar.error(f"🔴 Streamlit se vůbec nespojil s URL: {e}")
        return {"zapasy": [], "tipy": [], "admin": {}}


# =========================================================================
# 📤 FUNKCE PRO UKLÁDÁNÍ DAT (Zapisuje přesně do konkrétního listu)
# =========================================================================

def uloz_tip_hrace(hrac, zapas_id, tip_d, tip_h, zolik):
    """Uloží nebo aktualizuje jeden konkrétní tip hráče."""
    df_tipy = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="tipy")
    
    if df_tipy.empty:
        df_tipy = pd.DataFrame(columns=["hrac", "zapas_id", "tip_d", "tip_h", "zolik", "cas_ulozeni"])
        
    mask = (df_tipy["hrac"] == hrac) & (df_tipy["zapas_id"] == int(zapas_id))
    
    novy_radek = {
        "hrac": hrac,
        "zapas_id": int(zapas_id),
        "tip_d": int(tip_d),
        "tip_h": int(tip_h),
        "zolik": bool(zolik),
        "cas_ulozeni": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if mask.any():
        idx = df_tipy[mask].index[0]
        for k, v in novy_radek.items():
            df_tipy.at[idx, k] = v
    else:
        df_tipy = pd.concat([df_tipy, pd.DataFrame([novy_radek])], ignore_index=True)
        
    conn.update(spreadsheet=SPREADSHEET_ID, worksheet="tipy", data=df_tipy)
    st.cache_data.clear()

def uloz_admin_hodnotu(klic, hodnota):
    """Uloží nebo aktualizuje jakýkoli konfigurační klíč do listu 'admin'"""
    df_admin = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="admin")
    
    if df_admin.empty:
        df_admin = pd.DataFrame(columns=["klic", "hodnota"])
        
    mask = df_admin["klic"] == klic
    
    if mask.any():
        idx = df_admin[mask].index[0]
        df_admin.at[idx, "hodnota"] = str(hodnota)
    else:
        df_admin = pd.concat([df_admin, pd.DataFrame([{"klic": klic, "hodnota": str(hodnota)}])], ignore_index=True)
        
    conn.update(spreadsheet=SPREADSHEET_ID, worksheet="admin", data=df_admin)
    st.cache_data.clear()


# =========================================================================
# ⚙️ KONFIGURACE A KONSTANTY
# =========================================================================
st.set_page_config(page_title="⚽ Fotbalová Tipovačka MS 2026", layout="wide")

API_KEY = "8dba0719363f714de5da38bceda0759c"
BASE_URL = "https://v3.football.api-sports.io"
LEAGUE_ID = 1      
SEASON = 2026      

GLOBALNI_HESLO = "d3105tr31ci"  
ADMIN_HESLO = "F0tbal3k26"          
HRACI = ["Flesi", "Honza", "Jirka", "Karel", "Petr"]

PREKLAD_TYMU = {
    "Algeria": "Alžírsko", "Argentina": "Argentina", "Australia": "Austrálie", "Austria": "Rakousko",
    "Belgium": "Belgie", "Bosnia-Herzegovina": "Bosna a Herc.", "Brazil": "Brazílie", "Canada": "Kanada",
    "Cape Verde Islands": "Kapverdy", "Colombia": "Kolumbie", "Congo DR": "DR Kongo", "Curaçao": "Curaçao",
    "Czechia": "Česko", "Croatia": "Chorvatsko", "Egypt": "Egypt", "Ecuador": "Ekvádor", "England": "Anglie",
    "France": "Francie", "Germany": "Německo", "Ghana": "Ghana", "Haiti": "Haiti", "Ivory Coast": "Pobřeží slonoviny",
    "Iran": "Írán", "Iraq": "Írák", "Japan": "Japonsko", "Jordan": "Jordánsko", "Mexico": "Mexiko",
    "Morocco": "Maroko", "Netherlands": "Nizozemsko", "New Zealand": "Nový Zéland", "Norway": "Norsko",
    "Panama": "Panama", "Paraguay": "Paraguay", "Portugal": "Portugalsko", "Qatar": "Katar", "Saudi Arabia": "Saúdská Arábie",
    "Scotland": "Skotsko", "Senegal": "Senegal", "South Africa": "Jihoafrická rep.", "South Korea": "Jižní Korea",
    "Spain": "Španělsko", "Sweden": "Švédsko", "Switzerland": "Švýcarsko", "Tunisia": "Tunisko", "Turkey": "Turecko",
    "United States": "USA", "Uruguay": "Uruguay", "Uzbekistan": "Uzbekistán"
}

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

# =========================================================================
# 🔑 ZABEZPEČENÝ PŘIHLAŠOVACÍ SYSTÉM
# =========================================================================
if "globalne_overeno" not in st.session_state:
    st.session_state["globalne_overeno"] = False

if "uzivatel" not in st.session_state:
    st.session_state["uzivatel"] = None

# KROK 1: Globální heslo
if not st.session_state["globalne_overeno"]:
    st.title("⚽ MS ve fotbale 2026 - Tipovačka")
    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        st.subheader("Zabezpečený přístup")
        vstupni_heslo = st.text_input("Zadej přístupové heslo k tipovačce:", type="password")
        if vstupni_heslo == GLOBALNI_HESLO:
            st.session_state["globalne_overeno"] = True
            st.rerun()
        elif vstupni_heslo != "":
            st.error("Nesprávné přístupové heslo!")
    st.stop()

# KROK 2: Výběr uživatele
if st.session_state["uzivatel"] is None:
    st.title("⚽ MS ve fotbale 2026 - Tipovačka")
    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        st.subheader("Přihlášení uživatele")
        vybrany = st.selectbox("Vyber své jméno:", ["-- Vyber --"] + HRACI + ["Správce 👑"])
        if vybrany != "-- Vyber --":
            if vybrany == "Správce 👑":
                a_heslo = st.text_input("Zadej heslo správce:", type="password")
                if st.button("Vstoupit do administrace 👑"):
                    if a_heslo == ADMIN_HESLO:
                        st.session_state["uzivatel"] = "admin"
                        st.rerun()
                    else:
                        st.error("Nesprávné heslo správce!")
            else:
                if st.button(f"Vstoupit jako {vybrany} 🏃‍♂️", use_container_width=True):
                    st.session_state["uzivatel"] = vybrany
                    st.rerun()
    st.stop()

current_user = st.session_state["uzivatel"]

# --- OSTRÉ NAČTENÍ DAT NA STARTU ---
data = nacti_fotbalova_data()

# =========================================================================
# 🧭 HLAVNÍ MENU A NAVIGACE
# =========================================================================
st.sidebar.header(f"👤 Uživatel: {current_user.capitalize()}")
if current_user == "admin":
    volba = st.sidebar.radio("Navigace:", ["Žebříček hráčů 🏆", "Moje tipy 📝", "Celoturnajové tipy 🔮", "Správa API a zápasů ⚙️"])
else:
    volba = st.sidebar.radio("Navigace:", ["Žebříček hráčů 🏆", "Moje tipy 📝", "Celoturnajové tipy 🔮"])

if st.sidebar.button("Odhlásit se 🚪", use_container_width=True):
    if "uzivatel" in st.session_state:
        st.session_state["uzivatel"] = None
    st.rerun()

if st.sidebar.button
