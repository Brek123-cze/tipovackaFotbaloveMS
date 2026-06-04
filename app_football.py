import streamlit as st
import requests
import pandas as pd
import time

# =========================================================================
# ⚙️ KONFIGURACE A KONSTANTY
# =========================================================================
st.set_page_config(page_title="⚽ Fotbalová Tipovačka MS 2026", layout="wide")

API_KEY = "8dba0719363f714de5da38bceda0759c"
BASE_URL = "https://v3.football.api-sports.io"
LEAGUE_ID = 1      # MS ve fotbale v API-Football
SEASON = 2026      # Sezóna MS

ADMIN_HESLO = "tvoje_admin_heslo"  # Změň podle potřeby
HRACI = ["Honza", "Jirka", "Petr", "Admin"]  # Tvoje hokejová parta

# Slovník pro překlad států do češtiny (postupně doplníme podle losu)
PREKLAD_TYMU = {
    "Germany": "Německo",
    "Argentina": "Argentina",
    "France": "Francie",
    "Brazil": "Brazílie",
    "Spain": "Španělsko",
    "Czech Republic": "Česko"
}

# Headers pro komunikaci s API
headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

# =========================================================================
# 📥 FUNKCE PRO NAČÍTÁNÍ DAT Z API-FOOTBALL
# =========================================================================
@st.cache_data(ttl=900)  # Data se uloží do paměti na 15 minut (šetříme limit 100 dotazů/den)
def nacti_aktualni_zapasy_z_api():
    """Tato funkce stáhne z API zápasy pro včerejšek, dnešek a zítřek"""
    url = f"{BASE_URL}/fixtures?league={LEAGUE_ID}&season={SEASON}"
    # V ostré verzi zde přidáme filtr pro aktuální dny kvůli Free plánu
    try:
        response = requests.get(url, headers=headers, timeout=10)
        res_data = response.json()
        if response.status_code == 200 and not res_data.get("errors"):
            return res_data.get("response", [])
        return []
    except:
        return []

# =========================================================================
# 🔑 PŘIHLAŠOVACÍ SYSTÉM (Tvoje osvědčená klasika)
# =========================================================================
if "uzivatel" not in st.session_state:
    st.title("⚽ MS ve fotbale 2026 - Tipovačka")
    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        vybrany = st.selectbox("Vyber své jméno:", ["-- Vyber --"] + HRACI)
        if vybrany != "-- Vyber --":
            if vybrany == "Admin":
                heslo = st.text_input("Heslo správce:", type="password")
                if st.button("Vstoupit jako správce") and heslo == ADMIN_HESLO:
                    st.session_state["uzivatel"] = "admin"
                    st.rerun()
            else:
                if st.button(f"Vstoupit jako {vybrany}"):
                    st.session_state["uzivatel"] = vybrany
                    st.rerun()
    st.stop()

current_user = st.session_state["uzivatel"]

# =========================================================================
# 🧭 HLAVNÍ MENU A NAVIGACE
# =========================================================================
st.sidebar.header(f"👤 Uživatel: {current_user.capitalize()}")
if current_user == "admin":
    volba = st.sidebar.radio("Navigace:", ["Žebříček hráčů 🏆", "Moje tipy 📝", "Celoturnajové tipy 🔮", "Správa API a zápasů ⚙️"])
else:
    volba = st.sidebar.radio("Navigace:", ["Žebříček hráčů 🏆", "Moje tipy 📝", "Celoturnajové tipy 🔮"])

if st.sidebar.button("Odhlásit se 🚪"):
    del st.session_state["uzivatel"]
    st.rerun()

# =========================================================================
# 🏠 JEDNOTLIVÉ SEKCE APLIKACE
# =========================================================================
if volba == "Žebříček hráčů 🏆":
    st.title("🏆 Průběžný žebříček fotbalové tipovačky")
    st.info("Zde bude tabulka s body, medailemi a rozbalovací matice zápas po zápase.")

elif volba == "Moje tipy 📝":
    st.title("📝 Zadávání fotbalových tipů")
    st.write("Základní hrací čas (90 min). U každého zápasu uvidíš oficiální vlajku z API.")
    
    # Ukázka, jak Streamlit jednoduše vykreslí vlajku z odkazu v API:
    st.write("### Ukázka zobrazení zápasu s vlajkami:")
    col1, col2, col3, col4, col5 = st.columns([2,1,1,1,2])
    with col1:
        st.image("https://media.api-sports.io/football/teams/25.png", width=30) # Vlajka Německa z API
        st.write("Německo")
    with col2:
        st.number_input("Tip Domácí", min_value=0, value=0, step=1, label_visibility="collapsed", key="test_d")
    with col3:
        st.write("<h3 style='text-align: center; margin: 0;'>:</h3>", unsafe_allow_html=True)
    with col4:
        st.number_input("Tip Hosté", min_value=0, value=0, step=1, label_visibility="collapsed", key="test_h")
    with col5:
        st.image("https://media.api-sports.io/football/teams/26.png", width=30) # Vlajka Argentiny z API
        st.write("Argentina")

elif volba == "Celoturnajové tipy 🔮":
    st.title("🔮 Celoturnajové dlouhodobé tipy")
    st.write("Tipy na Mistra světa, semifinalisty a celkový počet gólů před výkopem prvního zápasu.")

elif volba == "Správa API a zápasů ⚙️" and current_user == "admin":
    st.title("⚙️ Administrace: Správa API-Football")
    
    if st.button("🔄 Otestovat spojení a stáhnout dnešní zápasy"):
        with st.spinner("Komunikuji s v3.football.api-sports.io..."):
            zapasy = nacti_aktualni_zapasy_z_api()
            if zapasy:
                st.success(f"Úspěšně načteno {len(zapasy)} zápasů z API!")
                # Zde v budoucnu naprogramujeme uložení do Google Sheets
            else:
                st.warning("Z API se nevrátily žádné zápasy. Turnaj buď ještě nezačal, nebo jsou schované kvůli Free plánu.")