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

def nacti_fotbalova_data():
    """Načte data ze všech tří listů přes veřejný odkaz a bezpečně ošetří prázdné tabulky"""
    # 1. NAČTENÍ ZÁPASŮ
    try:
        df_zapasy = conn.read(worksheet="zapasy")
        zapasy = df_zapasy.to_dict(orient="records") if not df_zapasy.empty else []
    except Exception as e:
        zapasy = []
        
    # 2. NAČTENÍ TIPŮ
    try:
        df_tipy = conn.read(worksheet="tipy")
        tipy = df_tipy.to_dict(orient="records") if not df_tipy.empty else []
    except Exception as e:
        tipy = []
        
    # 3. NAČTENÍ ADMIN NASTAVENÍ
    admin_data = {}
    try:
        df_admin = conn.read(worksheet="admin")
        if not df_admin.empty:
            for _, row in df_admin.iterrows():
                if "klic" in row and pd.notna(row["klic"]):
                    admin_data[str(row["klic"]).strip()] = row.get("hodnota", "")
    except Exception as e:
        admin_data = {}
                    
    return {
        "zapasy": zapasy,
        "tipy": tipy,
        "admin": admin_data
    }

# =========================================================================
# 📤 FUNKCE PRO UKLÁDÁNÍ DAT (Zapisuje přesně do konkrétního listu)
# =========================================================================

def uloz_tip_hrace(hrac, zapas_id, tip_d, tip_h, zolik):
    """
    Uloží nebo aktualizuje jeden konkrétní tip hráče.
    Díky nové struktuře nemusíme přepisovat celou tabulku, stačí aktualizovat řádek.
    """
    # Načteme aktuální tipy
    df_tipy = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="tipy")
    
    # Vyčistíme případné prázdné hodnoty
    if df_tipy.empty:
        df_tipy = pd.DataFrame(columns=["hrac", "zapas_id", "tip_d", "tip_h", "zolik", "cas_ulozeni"])
        
    # Podíváme se, zda už hráč na tento zápas netipoval (pokud ano, řádek přepíšeme)
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
        # Aktualizace stávajícího tipu
        idx = df_tipy[mask].index[0]
        for k, v in novy_radek.items():
            df_tipy.at[idx, k] = v
    else:
        # Přidání nového tipu na konec
        df_tipy = pd.concat([df_tipy, pd.DataFrame([novy_radek])], ignore_index=True)
        
    # Zápis zpět do Google Sheets
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
LEAGUE_ID = 1      # MS ve fotbale v API-Football
SEASON = 2026      # Sezóna MS

# 🔐 HESLA PRO ZABEZPEČENÍ APLIKACE
GLOBALNI_HESLO = "d3105tr31ci"  # Společné heslo pro přístup do aplikace
ADMIN_HESLO = "F0tbal3k26"              # Heslo pouze pro správce 👑
HRACI = ["Flesi", "Honza", "Jirka", "Karel", "Petr"]             # Tvoje parta (Admina jsme dali zvlášť do menu)

# Slovník pro překlad států do češtiny
PREKLAD_TYMU = {
    "Germany": "Německo",
    "Argentina": "Argentina",
    "France": "Francie",
    "Brazil": "Brazílie",
    "Spain": "Španělsko",
    "Czech Republic": "Česko"
}

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

# --- OSTRÉ NAČTENÍ DAT NA STARTU ---
data = nacti_fotbalova_data()

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
# 🔑 ZABEZPEČENÝ PŘIHLAŠOVACÍ SYSTÉM
# =========================================================================
if "uzivatel" not in st.session_state:
    st.title("⚽ MS ve fotbale 2026 - Tipovačka")
    
    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        st.subheader("Zabezpečený přístup")
        
        # 1. Krok: Společné heslo pro celou aplikaci
        vstupni_heslo = st.text_input("Zadej přístupové heslo k tipovačce:", type="password")
        
        if vstupni_heslo == GLOBALNI_HESLO:
            st.success("Heslo správné! Nyní se můžeš přihlásit:")
            
            # 2. Krok: Výběr jména hráče nebo správce
            vybrany = st.selectbox("Vyber své jméno:", ["-- Vyber --"] + HRACI + ["Správce 👑"])
            
            if vybrany != "-- Vyber --":
                if vybrany == "Správce 👑":
                    # Pokud se hlásí admin, chceme ještě druhé administrátorské heslo
                    a_heslo = st.text_input("Zadej heslo správce:", type="password")
                    if st.button("Vstoupit do administrace 👑"):
                        if a_heslo == ADMIN_HESLO:
                            st.session_state["uzivatel"] = "admin"
                            st.rerun()
                        else:
                            st.error("Nesprávné heslo správce!")
                else:
                    # Běžný hráč vstupuje rovnou na jedno kliknutí
                    if st.button(f"Vstoupit jako {vybrany} 🏃‍♂️"):
                        st.session_state["uzivatel"] = vybrany
                        st.rerun()
        elif vstupni_heslo != "":
            st.error("Nesprávné přístupové heslo!")
            
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
    st.write("Zde můžeš otestovat stahování zápasů z API a jejich automatické uložení do Google Sheets.")

    # Přidáme výběr ligy pro testování (1 = MS 2026, 10 = Přátelské zápasy)
    test_liga = st.selectbox("Vyber soutěž pro stažení zápasů:", [
        "Mezinárodní přátelské zápasy (ID 10) 🌍",
        "Mistrovství světa 2026 (ID 1) 🏆"
    ])
    
    id_ligy = 10 if "ID 10" in test_liga else 1
    aktualni_rok = time.strftime("%Y") # Automaticky načte aktuální rok (2026)

    if st.button("🔄 Stáhnout zápasy a uložit do Google Sheets"):
        with st.spinner("Komunikuji s API-Football a stahuji dnešní zápasy..."):
            
            # 1. Zavoláme API pro konkrétní ligu a aktuální den
            dnesni_datum = time.strftime("%Y-%m-%d") # Formát: RRRR-MM-DD
            url = f"{BASE_URL}/fixtures?league={id_ligy}&season={aktualni_rok}&date={dnesni_datum}"
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                res_data = response.json()
                
                if response.status_code == 200 and not res_data.get("errors"):
                    api_zapasy = res_data.get("response", [])
                    
                    if not api_zapasy:
                        st.warning(f"API spojení proběhlo, ale pro datum {dnesni_datum} a ligu {id_ligy} nebyly nalezeny žádné zápasy.")
                    else:
                        st.success(f"Z API úspěšně načteno {len(api_zapasy)} zápasů!")
                        
                        # 2. Načteme stávající zápasy z Google Sheets, abychom je nepromazali
                        try:
                            df_stavajici = conn.read(worksheet="zapasy")
                        except:
                            df_stavajici = pd.DataFrame()
                            
                        nove_radky = []
                        
                        # 3. Projdeme zápasy z API a poskládáme je do naší struktury
                        for idx, z in enumerate(api_zapasy):
                            f_id = z["fixture"]["id"]
                            
                            # Kontrola, zda už zápas s tímto api_id v tabulce náhodou nemáme
                            if not df_stavajici.empty and "api_id" in df_stavajici.columns:
                                if f_id in df_stavajici["api_id"].values:
                                    continue # Zápas už existuje, přeskočíme ho
                            
                            # Převedeme UTC čas z API na hezčí formát pro kluky (odřízneme sekundy a časové pásmo)
                            # Příklad z API: "2026-06-04T20:45:00+00:00" -> "2026-06-04 20:45"
                            raw_date = z["fixture"]["date"]
                            hezky_datum = raw_date.replace("T", " ")[:16]
                            
                            novy_zapas = {
                                "id": len(df_stavajici) + len(nove_radky) + 1,
                                "api_id": int(f_id),
                                "datum": hezky_datum,
                                "faze": "Přátelský zápas",
                                "skupina": "",
                                "domaci": z["teams"]["home"]["name"],
                                "hoste": z["teams"]["away"]["name"],
                                "vlajka_d": z["teams"]["home"]["logo"], # Přímý odkaz na vlajku
                                "vlajka_h": z["teams"]["away"]["logo"], # Přímý odkaz na vlajku
                                "goly_d": z["goals"]["home"] if z["goals"]["home"] is not None else "",
                                "goly_h": z["goals"]["away"] if z["goals"]["away"] is not None else "",
                                "status": z["fixture"]["status"]["short"]
                            }
                            nove_radky.append(novy_zapas)
                        
                        if nove_radky:
                            # 4. Spojíme staré zápasy s novými a odešleme do Google Sheets
                            df_nove = pd.DataFrame(nove_radky)
                            df_kompletni = pd.concat([df_stavajici, df_nove], ignore_index=True)
                            
                            conn.update(worksheet="zapasy", data=df_kompletni)
                            st.cache_data.clear()
                            st.success(f"Do Google Sheets úspěšně zapsáno {len(nove_radky)} nových zápasů! Otevři tabulku a zkontroluj list 'zapasy'.")
                        else:
                            st.info("Všechny dnešní zápasy už v Google tabulce máš uloženy.")
                else:
                    st.error(f"Chyba API: {res_data.get('errors')}")
            except Exception as e:
                st.error(f"Selhalo síťové spojení s API nebo zápis do Sheets: {e}")
