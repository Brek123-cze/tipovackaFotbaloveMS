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

# Překladový slovník (pokud ho nemáš na začátku souboru, necháme ho i zde)
PREKLAD_TYMU = {
"Algeria": "Alžírsko",
"Argentina": "Argentina",
"Australia": "Austrálie",
"Austria": "Rakousko",
"Belgium": "Belgie",
"Bosnia-Herzegovina": "Bosna a Herc.",
"Brazil": "Brazílie",
"Canada": "Kanada",
"Cape Verde Islands": "Kapverdy",
"Colombia": "Kolumbie",
"Congo DR": "DR Kongo",
"Curaçao": "Curaçao",
"Czechia": "Česko",
"Croatia": "Chorvatsko",
"Egypt": "Egypt",
"Ecuador": "Ekvádor",
"England": "Anglie",
"France": "Francie",
"Germany": "Německo",
"Ghana": "Ghana",
"Haiti": "Haiti",
"Ivory Coast": "Pobřeží slonoviny",
"Iran": "Írán",
"Iraq": "Írák",
"Japan": "Japonsko",
"Jordan": "Jordánsko",
"Mexico": "Mexiko",
"Morocco": "Maroko",
"Netherlands": "Nizozemsko",
"New Zealand": "Nový Zéland",
"Norway": "Norsko",
"Panama": "Panama",
"Paraguay": "Paraguay",
"Portugal": "Portugalsko",
"Qatar": "Katar",
"Saudi Arabia": "Saúdská Arábie",
"Scotland": "Skotsko",
"Senegal": "Senegal",
"South Africa": "Jihoafrická rep.",
"South Korea": "Jižní Korea",
"Spain": "Španělsko",
"Sweden": "Švédsko",
"Switzerland": "Švýcarsko",
"Tunisia": "Tunisko",
"Turkey": "Turecko",
"United States": "USA",
"Uruguay": "Uruguay",
"Uzbekistan": "Uzbekistán"
}

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
# 🔑 ZABEZPEČENÝ PŘIHLAŠOVACÍ SYSTÉM
# =========================================================================
# --- INICIALIZACE STAVU (pokud v paměti ještě nejsou) ---
if "globalne_overeno" not in st.session_state:
    st.session_state["globalne_overeno"] = False

if "uzivatel" not in st.session_state:
    st.session_state["uzivatel"] = None

# =========================================================================
# KROK 1: Globální heslo pro celou aplikaci (Zobrazí se jen, pokud ještě není overeno)
# =========================================================================
if not st.session_state["globalne_overeno"]:
    st.title("⚽ MS ve fotbale 2026 - Tipovačka")
    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        st.subheader("Zabezpečený přístup")
        vstupni_heslo = st.text_input("Zadej přístupové heslo k tipovačce:", type="password")
        
        if vstupni_heslo == GLOBALNI_HESLO:
            st.session_state["globalne_overeno"] = True
            st.rerun()  # Heslo je správně, uložíme do paměti a restartujeme skript do Kroku 2
        elif vstupni_heslo != "":
            st.error("Nesprávné přístupové heslo!")
            
    st.stop()  # Pokud není globálně ověřeno, kód dál nepustíme


# =========================================================================
# KROK 2: Výběr jména hráče nebo správce (Sem to skočí po odhlášení automaticky)
# =========================================================================
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
                # Běžný hráč vstupuje rovnou na jedno kliknutí
                if st.button(f"Vstoupit jako {vybrany} 🏃‍♂️", use_container_width=True):
                    st.session_state["uzivatel"] = vybrany
                    st.rerun()
                    
    st.stop()  # Pokud není vybrán uživatel, nepokračujeme do hlavního menu


# Pokud kód proteče až sem, znamená to, že máme splněné oba kroky
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
    # Smažeme pouze konkrétní přihlášené jméno
    if "uzivatel" in st.session_state:
        st.session_state["uzivatel"] = None

if st.sidebar.button("🔄 Aktualizovat data z tabulky", use_container_width=True):
    st.cache_data.clear()  # Kompletně vymaže pětiminutový zámek
    st.rerun()


# =========================================================================
# ⚽ NOVÁ FOTBALOVÁ LOGIKA BODOVÁNÍ PRO HRÁČE
# =========================================================================
def spocitej_body_hrace(tip_d, tip_h, real_d, real_h, zolik=False):
    if tip_d is None or tip_h is None or real_d is None or real_h is None:
        return 0, False

    # Ve fotbale bereme efektivní výsledek po 90 minutách (základní hrací doba)
    real_d_efektivni = int(real_d)
    real_h_efektivni = int(real_h)

    vitez_tip = "D" if tip_d > tip_h else ("H" if tip_h > tip_d else "R")
    vitez_real = "D" if real_d_efektivni > real_h_efektivni else ("H" if real_h_efektivni > real_d_efektivni else "R")
    
    rozdil_tip = tip_d - tip_h
    rozdil_real = real_d_efektivni - real_h_efektivni
    
    goly_tip = tip_d + tip_h
    goly_real = real_d_efektivni + real_h_efektivni

    body = 0
    presny = False

    # 1. PŘESNÝ VÝSLEDEK -> 10 Bodů
    if tip_d == real_d_efektivni and tip_h == real_h_efektivni:
        body = 10
        presny = True
    # 2. VÍTĚZ + ROZDÍL / VÍTĚZ + CELKEM GÓLŮ / TREFENÁ REMÍZA -> 6 Bodů
    elif (vitez_tip == vitez_real and rozdil_tip == rozdil_real) or \
         (vitez_tip == vitez_real and goly_tip == goly_real) or \
         (vitez_real == "R" and vitez_tip == "R"):
        body = 6
    # 3. POUZE VÍTĚZ (Znak zápasu) -> 3 Body
    elif vitez_tip == vitez_real:
        body = 3
    # 4. OSTATNÍ (staré pravidlo za 2 body zrušeno) -> 0 Bodů
    else:
        body = 0

    # 🃏 VYHODNOCENÍ ŽOLÍKA
    if zolik:
        if body > 0:
            body = body * 2  # Dvojnásobek zisku
        else:
            body = -3        # Tvrdý postih při netrefení

    return body, presny


# =========================================================================
# 🔄 INICIALIZACE A VÝPOČET STATISTIK TIPÉRŮ PRO ŽEBŘÍČEK (NEPRŮSTŘELNÁ VERZE)
# =========================================================================
# Spočítáme celkový počet gólů na turnaji z odehraných zápasů
celkove_goly_ms = 0
if data.get("zapasy"):
    for z in data["zapasy"]:
        if z.get("status") == "FINISHED" and pd.notna(z.get("goly_d")):
            celkove_goly_ms += (int(z["goly_d"]) + int(z["goly_h"]))

# Příprava čistého slovníku pro ukládání výsledků
statistiky_hracu = {h: {"body": 0, "presne": 0} for h in HRACI}

# Převod tipů na DataFrame pro snadné a bezpečné filtrování řádků
df_vsechny_tipy = pd.DataFrame(data.get("tipy", []))

# Projdeme všechny zápasy z databáze
if data.get("zapasy"):
    for z in data["zapasy"]:
        z_id = int(z["id"])
        
        # Zkontrolujeme, zda zápas už reálně skončil a má vyplněné góly
        if z.get("status") == "FINISHED" and pd.notna(z.get("goly_d")) and str(z["goly_d"]) != "":
            real_d = int(z["goly_d"])
            real_h = int(z["goly_h"])
            
            # Projdeme každého hráče a vytáhneme jeho tip z DataFrame
            for hrac in HRACI:
                t_d, t_h, zolik = None, None, False
                
                if not df_vsechny_tipy.empty:
                    # Vyfiltrujeme řádek pro konkrétního hráče a konkrétní zápas
                    filtr = df_vsechny_tipy[(df_vsechny_tipy["hrac"] == hrac) & (df_vsechny_tipy["zapas_id"].astype(int) == z_id)]
                    
                    if not filtr.empty:
                        row_tip = filtr.iloc[0]
                        # Ověříme, zda jsou vyplněné tipované góly
                        if pd.notna(row_tip.get("tip_d")) and pd.notna(row_tip.get("tip_h")):
                            if str(row_tip["tip_d"]) != "" and str(row_tip["tip_h"]) != "":
                                t_d = int(row_tip["tip_d"])
                                t_h = int(row_tip["tip_h"])
                        
                        # Ověříme stav žolíka v daném řádku
                        if "zolik" in row_tip:
                            zolik = bool(row_tip["zolik"])

                # Pokud hráč pro tento odehraný zápas tip vyplnil, spočítáme mu body
                if t_d is not None and t_h is not None:
                    b, p = spocitej_body_hrace(t_d, t_h, real_d, real_h, zolik)
                    statistiky_hracu[hrac]["body"] += b
                    if p: 
                        statistiky_hracu[hrac]["presne"] += 1

# =========================================================================
# 🔮 PŘIČTENÍ BODŮ ZA CELOTURNAJOVÉ DLOUHODOBÉ TIPY
# =========================================================================
# Načítáme z neprůstřelného umístění ve "vysledky" nebo "admin" sekci
real_mistr = data.get("vysledky", {}).get("MS_REAL_MISTR", {}).get("hodnota", "").strip().lower()
real_semi = [
    str(data.get("vysledky", {}).get("MS_REAL_SEMI1", {}).get("hodnota", "")).strip().lower(),
    str(data.get("vysledky", {}).get("MS_REAL_SEMI2", {}).get("hodnota", "")).strip().lower(),
    str(data.get("vysledky", {}).get("MS_REAL_SEMI3", {}).get("hodnota", "")).strip().lower(),
    str(data.get("vysledky", {}).get("MS_REAL_SEMI4", {}).get("hodnota", "")).strip().lower()
]
real_cesko = data.get("vysledky", {}).get("MS_REAL_CESKO", {}).get("hodnota", "Základní skupina")
real_mvp = data.get("vysledky", {}).get("MS_REAL_MVP", {}).get("hodnota", "").strip().lower()
try:
    real_goly = int(data.get("vysledky", {}).get("MS_REAL_GOLY", {}).get("hodnota", 0))
except:
    real_goly = 0

# Porovnáme dlouhodobé předpovědi tipérů s reálným stavem turnaje
for hrac in HRACI:
    ct = data.get("celkove_tipy", {}).get(hrac, {})
    
    # 1. Trefa Celkového Mistra MS (20 bodů)
    if real_mistr and ct.get("mistr", "").strip().lower() == real_mistr:
        statistiky_hracu[hrac]["body"] += 20
        
    # 2. Trefa 4 semifinalistů (10 bodů za každého správného člena)
    hrac_semi = [str(s).strip().lower() for s in ct.get("semifinale", ["", "", "", ""])]
    for tym in hrac_semi:
        if tym and tym in real_semi:
            statistiky_hracu[hrac]["body"] += 10
            
    # 3. Trefa konečné fáze národního týmu ČR (20 bodů)
    if real_cesko and ct.get("cesko") == real_cesko:
        statistiky_hracu[hrac]["body"] += 20
        
    # 4. Trefa nejlepšího hráče / MVP turnaje (20 bodů)
    tip_mvp = ct.get("mvp", "").strip().lower()
    if real_mvp and tip_mvp and (real_mvp in tip_mvp or tip_mvp in real_mvp):
        statistiky_hracu[hrac]["body"] += 20
        
    # 5. Přesný celkový počet gólů na MS (20 bodů), nebo tolerance +- 3 góly (10 bodů)
    try:
        tip_goly = int(ct.get("goly", 0))
    except:
        tip_goly = 0
        
    if real_goly > 0 and tip_goly > 0:
        if tip_goly == real_goly:
            statistiky_hracu[hrac]["body"] += 20
        elif abs(tip_goly - real_goly) <= 3:
            statistiky_hracu[hrac]["body"] += 10


# =========================================================================
# 🏠 JEDNOTLIVÉ SEKCE APLIKACE
# =========================================================================
    
# =========================================================================
# POMOCNÁ FUNKCE PRO FORMÁTOVÁNÍ VÝSLEDKŮ NA HLAVNÍ STRÁNCE
# =========================================================================
def formatuj_vysledek_hlavni_strana(z):
    """
    Sestaví řádek výsledku přesně podle požadovaného formátu:
    Francie 1:1 (0:1) Portugalsko (pr 2:2, pn 5:3)
    """
    if z.get("status") != "FINISHED" or pd.isna(z.get("goly_d")):
        return ""
    
    # Překlad názvů týmů (pokud existuje slovník PREKLAD_TYMU)
    tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"]) if 'PREKLAD_TYMU' in globals() else z["domaci"]
    tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"]) if 'PREKLAD_TYMU' in globals() else z["hoste"]
    
    gd = int(z["goly_d"])
    gh = int(z["goly_h"])
    
    # 1. Základní výsledek (po 90 minutách) a poločas v první závorce
    polocas = ""
    if pd.notna(z.get("halftime_d")) and str(z["halftime_d"]) != "":
        polocas = f" ({int(z['halftime_d'])}:{int(z['halftime_h'])})"
        
    zakladni_cast = f"<b>{tým_d_cz}</b> {gd}:{gh}{polocas} <b>{tým_h_cz}</b>"
    
    # 2. Vyhodnocení prodloužení a penalt ve druhé závorce na konci
    dodatky = []
    dur = str(z.get("duration", "")).upper()
    
    # Kontrola prodloužení (extratime)
    if "EXTRA" in dur or "PENALTY" in dur or (pd.notna(z.get("extratime_d")) and str(z["extratime_d"]) != ""):
        if pd.notna(z.get("extratime_d")) and str(z["extratime_d"]) != "":
            dodatky.append(f"pr {int(z['extratime_d'])}:{int(z['extratime_h'])}")
        else:
            dodatky.append("pr")
            
    # Kontrola penalt (penalties)
    if "PENALTY" in dur or (pd.notna(z.get("penalties_d")) and str(z["penalties_d"]) != ""):
        if pd.notna(z.get("penalties_d")) and str(z["penalties_d"]) != "":
            dodatky.append(f"pn {int(z['penalties_d'])}:{int(z['penalties_h'])}")

    konecny_dodatek = ""
    if dodatky:
        konecny_dodatek = f" <span style='color: #cc0000; font-weight: bold;'>({', '.join(dodatky)})</span>"
        
    return f"<div style='font-size: 0.95rem; line-height: 1.4; padding: 4px 0;'>⚽ {zakladni_cast}{konecny_dodatek}</div>"


# --- 1. ZÁLOŽKA: ŽEBŘÍČEK ---
if volba == "Žebříček hráčů 🏆":
    st.title("🏆 Průběžný žebříček fotbalové tipovačky")
    c_l, c_main, c_r = st.columns([1, 4, 1])
    with c_main:
        st.title("🏆 Průběžný žebříček tipovačky")
        
        # 1. HLAVNÍ GRAFICKÝ ŽEBŘÍČEK (Stále viditelný navrchu)
        zebricek = [{"jmeno": h, "body": v["body"], "presne": v["presne"]} for h, v in statistiky_hracu.items()]
        zebricek = sorted(zebricek, key=lambda x: (x["body"], x["presne"]), reverse=True)
        
        for idx, p in enumerate(zebricek):
            medaile = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "🔵"
            st.markdown(f"<div style='background-color: rgba(30,61,89,0.05); padding: 8px; border-radius: 6px; margin-bottom: 4px; display: flex; justify-content: space-between;'><b>{medaile} {idx+1}. {p['jmeno']}</b><span><b>{p['body']} B</b> (🎯 {p['presne']}x)</span></div>", unsafe_allow_html=True)

        st.info(f"🚨 **Celkový počet gólů vstřelených na celém šampionátu:** {celkove_goly_ms} gólů")
       # st.success(f"🌟 **Nejlepší střelec / lídr bodování:** {nejlepsi_cesi_output}")

        # =========================================================================
        # ⚽ PŘEHLED ZÁPASŮ AKTUÁLNÍHO A PŘEDCHOZÍHO DNE (Nově přidané pod žebříček)
        # =========================================================================
        st.markdown("<br><hr style='margin: 15px 0; border-top: 2px solid #ccc;'>", unsafe_allow_html=True)
        st.subheader("📊 Výsledky a program zápasů")

        # Zjištění dnešního a včerejšího hracího dne (podle nastavení v aplikaci)
        dnesni_den_aplikace = time.strftime("%Y-%m-%d") 
        vcerejsi_den_aplikace = (pd.to_datetime(dnesni_den_aplikace) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        # Vytvoření přehledných záložek pro Dnešek a Včerejšek
        tab_dnes, tab_vcera = st.tabs([f"📅 Dnešní zápasy", f"⏪ Včerejší výsledky"])

        with tab_dnes:
            # Předpokládáme, že df_zapasy je k dispozici a obsahuje sloupec 'hraci_den'
            zapasy_dnes = df_zapasy[df_zapasy["hraci_den"] == dnesni_den_aplikace].sort_values(by="datum")
            if zapasy_dnes.empty:
                st.info("Dnes nejsou v plánu žádné zápasy.")
            else:
                for _, z in zapasy_dnes.iterrows():
                    if z["status"] == "FINISHED":
                        st.markdown(formatuj_vysledek_hlavni_strana(z), unsafe_allow_html=True)
                    else:
                        cas = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
                        tým_d = PREKLAD_TYMU.get(z["domaci"], z["domaci"]) if 'PREKLAD_TYMU' in globals() else z["domaci"]
                        tým_h = PREKLAD_TYMU.get(z["hoste"], z["hoste"]) if 'PREKLAD_TYMU' in globals() else z["hoste"]
                        st.markdown(f"<div style='color: #555; padding: 4px 0;'>🕒 {cas} | {tým_d} vs {tým_h} <i>(neodehráno)</i></div>", unsafe_allow_html=True)

        with tab_vcera:
            zapasy_vcera = df_zapasy[df_zapasy["hraci_den"] == vcerejsi_den_aplikace].sort_values(by="datum")
            if zapasy_vcera.empty:
                st.info("Včera se nehrály žádné zápasy.")
            else:
                for _, z in zapasy_vcera.iterrows():
                    if z["status"] == "FINISHED":
                        st.markdown(formatuj_vysledek_hlavni_strana(z), unsafe_allow_html=True)
                    else:
                        cas = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
                        tým_d = PREKLAD_TYMU.get(z["domaci"], z["domaci"]) if 'PREKLAD_TYMU' in globals() else z["domaci"]
                        tým_h = PREKLAD_TYMU.get(z["hoste"], z["hoste"]) if 'PREKLAD_TYMU' in globals() else z["hoste"]
                        st.markdown(f"<div style='color: #777; padding: 4px 0;'>🕒 {cas} | {tým_d} vs {tým_h} <i>(nedohráno)</i></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # =========================================================================
        # 📦 EXPANDER 1: DETAILNÍ BODOVÁNÍ TIPÉRU (ZÁPAS PO ZÁPASE)
        # =========================================================================
        with st.expander("📊 Rozbalit detailní přehled bodů (zápas po zápase)"):
            real_mistr = data.get("nastaveni", {}).get("real_mistr", "").strip().lower()
            real_semi = [str(s).strip().lower() for s in data.get("nastaveni", {}).get("real_semifinale", ["", "", "", ""])]
            real_cesko = data.get("nastaveni", {}).get("real_cesko", "Základní skupina")
            real_mvp = data.get("nastaveni", {}).get("real_mvp", "").strip().lower()
            try:
                real_goly = int(data.get("nastaveni", {}).get("real_goly", 0))
            except:
                real_goly = 0

            prehled_bodu_data = []

            for hrac in HRACI:
                radek_hrace = {"Hráč": hrac}
                for z in ZAPASY:
                    z_id = z["id"]
                    body_za_zapas = 0
                    
                    res = data["vysledky"].get(str(z_id)) or data["vysledky"].get(int(z_id))
                    tip = data["tipy"][hrac].get(str(z_id)) or data["tipy"][hrac].get(int(z_id))
                    zolik = data["zolici"][hrac].get(str(z_id), False) or data["zolici"][hrac].get(int(z_id), False)
                    
                    if res and tip and tip.get("d") is not None and tip.get("h") is not None:
                        if res.get("d") is not None and res.get("h") is not None:
                            body_za_zapas, _ = spocitej_body_hrace(
                                tip["d"], tip["h"], res["d"], res["h"], zolik, bool(res.get("pp_sn", False))
                            )
                    
                    prefix = f"Z{z_id}"
                    tymy_zkratka = f"{z['domaci'][0:3]}-{z['hoste'][0:3]}"
                    nazev_sloupce = f"{prefix} ({tymy_zkratka})"
                    radek_hrace[nazev_sloupce] = body_za_zapas

                # Spočítá body za celoturnajové tipy z opravené databáze
                body_celkove = 0
                ct = data.get("celkove_tipy", {}).get(hrac, {})
                
                # Načtení čerstvých dat pro kontrolu řádku
                t_mistr = data.get("vysledky", {}).get("MS_REAL_MISTR", {}).get("hodnota", "").strip().lower()
                t_semi = [
                    str(data.get("vysledky", {}).get("MS_REAL_SEMI1", {}).get("hodnota", "")).strip().lower(),
                    str(data.get("vysledky", {}).get("MS_REAL_SEMI2", {}).get("hodnota", "")).strip().lower(),
                    str(data.get("vysledky", {}).get("MS_REAL_SEMI3", {}).get("hodnota", "")).strip().lower(),
                    str(data.get("vysledky", {}).get("MS_REAL_SEMI4", {}).get("hodnota", "")).strip().lower()
                ]
                t_cesko = data.get("vysledky", {}).get("MS_REAL_CESKO", {}).get("hodnota", "Základní skupina")
                t_mvp = data.get("vysledky", {}).get("MS_REAL_MVP", {}).get("hodnota", "").strip().lower()
                try:
                    t_goly = int(data.get("vysledky", {}).get("MS_REAL_GOLY", {}).get("hodnota", 0))
                except:
                    t_goly = 0
    
                # 1. Trefa Mistra
                if t_mistr and ct.get("mistr", "").strip().lower() == t_mistr: 
                    body_celkove += 20
                
                # 2. Trefa semifinalistů
                hrac_semi = [str(s).strip().lower() for s in ct.get("semifinale", ["", "", "", ""])]
                for tym in hrac_semi:
                    if tym and tym in t_semi: 
                        body_celkove += 10
                        
                # 3. Trefa konečné fáze ČR
                if t_cesko and ct.get("cesko") == t_cesko: 
                    body_celkove += 20
                    
                # 4. Trefa MVP turnaje
                tip_mvp = ct.get("mvp", "").strip().lower()
                if t_mvp and tip_mvp and (t_mvp in tip_mvp or tip_mvp in t_mvp): 
                    body_celkove += 20
                    
                # 5. Přesný počet gólů / tolerance
                try:
                    tip_goly = int(ct.get("goly", 0))
                except:
                    tip_goly = 0
                if t_goly > 0 and tip_goly > 0:
                    if tip_goly == t_goly: 
                        body_celkove += 20
                    elif abs(tip_goly - t_goly) <= 3: 
                        body_celkove += 10
                
                # Přidání sloupce s dlouhodobými bonusy na úplný konec řádku
                radek_hrace["🔮 Celoturnajové body"] = body_celkove
                prehled_bodu_data.append(radek_hrace)

            df_kompletni_prehled = pd.DataFrame(prehled_bodu_data)
            st.dataframe(
                df_kompletni_prehled, 
                use_container_width=True, 
                hide_index=True,
                column_config={"Hráč": st.column_config.TextColumn("Hráč", pinned=True)}
            )

elif volba == "Moje tipy 📝":
    # 📊 FUNKCE PRO VÝPOČET AKTUÁLNÍ TABULKY SKUPINY ZA BĚHU
    def spocitej_tabulku_skupiny(df_vsechny_zapasy, pismeno_skupiny):
        # Vyfiltrujeme pouze zápasy dané skupiny, které už skončily a mají výsledky
        df_sk = df_vsechny_zapasy[
            (df_vsechny_zapasy["skupina"] == pismeno_skupiny) & 
            (df_vsechny_zapasy["faze"].str.contains("GROUP", na=False))
        ]
        
        # Inicializace statistik pro týmy v této skupině
        tymy_stats = {}
        
        # Nejdříve zjistíme všechny týmy, které ve skupině vůbec hrají
        vsechny_tymy_skupiny = set(df_sk["domaci"].dropna().unique()).union(set(df_sk["hoste"].dropna().unique()))
        for t in vsechny_tymy_skupiny:
            tymy_stats[t] = {"Z": 0, "V": 0, "R": 0, "P": 0, "Skóre": "0:0", "Skóre_Rozdil": 0, "B": 0}
            
        # Projdeme zápasy a spočítáme body
        # Projdeme zápasy a spočítáme body i góly
        for _, z in df_sk.iterrows():
            # Kontrola, zda je zápas odehraný (góly nesmí být None ani prázdné)
            if pd.notna(z["goly_d"]) and pd.notna(z["goly_h"]) and str(z["goly_d"]) != "" and str(z["goly_h"]) != "":
                gd = int(z["goly_d"])
                gh = int(z["goly_h"])
                td = z["domaci"]
                th = z["hoste"]
                
                # 🛡️ BEZPEČNÁ INICIALIZACE: Pokud týmy ještě nemají založené kolonky pro góly, vytvoříme je
                if "Goly_Vstrelene" not in tymy_stats[td]: tymy_stats[td]["Goly_Vstrelene"] = 0
                if "Goly_Inkasovane" not in tymy_stats[td]: tymy_stats[td]["Goly_Inkasovane"] = 0
                if "Goly_Vstrelene" not in tymy_stats[th]: tymy_stats[th]["Goly_Vstrelene"] = 0
                if "Goly_Inkasovane" not in tymy_stats[th]: tymy_stats[th]["Goly_Inkasovane"] = 0

                # Zápasy (+1 odehraný zápas)
                tymy_stats[td]["Z"] += 1
                tymy_stats[th]["Z"] += 1
                
                # Výhry / Remízy / Prohry & Body
                if gd > gh:
                    tymy_stats[td]["V"] += 1; tymy_stats[td]["B"] += 3
                    tymy_stats[th]["P"] += 1
                elif gd < gh:
                    tymy_stats[th]["V"] += 1; tymy_stats[th]["B"] += 3
                    tymy_stats[td]["P"] += 1
                else:
                    tymy_stats[td]["R"] += 1; tymy_stats[td]["B"] += 1
                    tymy_stats[th]["R"] += 1; tymy_stats[th]["B"] += 1
                    
                # ⚽ SČÍTÁNÍ GÓLŮ DO STATISTIK
                tymy_stats[td]["Goly_Vstrelene"] += gd
                tymy_stats[td]["Goly_Inkasovane"] += gh
                tymy_stats[th]["Goly_Vstrelene"] += gh
                tymy_stats[th]["Goly_Inkasovane"] += gd

                # Pomocný výpočet pro rozdíl skóre (při rovnosti bodů)
                tymy_stats[td]["Skóre_Rozdil"] += (gd - gh)
                tymy_stats[th]["Skóre_Rozdil"] += (gh - gd)

        # Převod na DataFrame pro hezké zobrazení
        # Převod na DataFrame pro hezké zobrazení
        tabulka_data = []
        for t, s in tymy_stats.items():
            tým_cz = PREKLAD_TYMU.get(t, t)
            
            # Načteme nastřílené/inkasované góly, pokud neexistují (zatím se nehrálo), dáme 0
            vstrelene = s.get("Goly_Vstrelene", 0)
            inkasovane = s.get("Goly_Inkasovane", 0)
            
            # Sestavení klasického formátu skóre (např. "3:1")
            textove_skore = f"{vstrelene}:{inkasovane}"
            
            tabulka_data.append({
                "Tým": tým_cz, 
                "Z": s["Z"], 
                "V": s["V"], 
                "R": s["R"], 
                "P": s["P"], 
                "Skóre": textove_skore,  # ✨ Tento sloupec se teď spolehlivě zobrazí vždy
                "B": s["B"], 
                "Rozdil": s.get("Skóre_Rozdil", 0)
            })
            
        df_final = pd.DataFrame(tabulka_data)
        if not df_final.empty:
            # Seřazení: Body -> Rozdíl skóre
            df_final = df_final.sort_values(by=["B", "Rozdil"], ascending=[False, False]).reset_index(drop=True)
            df_final.index += 1  # Indexování od 1. místa
            
            # Pomocný sloupec Rozdil už kluci vidět nemusí, smažeme ho
            df_final = df_final.drop(columns=["Rozdil"])
            
        return df_final
    
    
    st.title("📝 Moje Tipy na zápasy MS 2026")
    st.write(f"Vítej ve svém tipovacím lístku, **{current_user}**.")

    # Skryjeme ošklivé Streamlit orámování tlačítek pomocí CSS
    st.markdown("""
        <style>
        div[data-testid="stButton"] button {
            border: none !important;
            background-color: transparent !important;
            padding: 0 !important;
            font-size: 1.5rem !important;
        }
        div[data-testid="stButton"] button:hover {
            color: #ff4b4b !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 🔤 BEZPEČNÝ PŘEKLADAČ FÁZÍ (Definován hned na začátku záložky)
    PREKLAD_FAZE = {
        "GROUP_STAGE": "Základní skupina",
        "LAST_32": "Šestnáctifinále (1/32)",
        "LAST_16": "Osmifinále (1/16)",
        "QUARTER_FINALS": "Čtvrtfinále",
        "SEMI_FINALS": "Semifinále",
        "THIRD_PLACE": "O 3. místo 🥉",
        "FINAL": "FINÁLE 🏆"
    }

    def preloz_fazi(faze_str):
        if not faze_str or pd.isna(faze_str):
            return "Neznámá fáze"
        
        faze_str = str(faze_str).strip()
        
        # Ošetření těch spojených dlouhých řetězců z API
        if "GROUP_STAGE" in faze_str: return PREKLAD_FAZE["GROUP_STAGE"]
        if "LAST_32" in faze_str: return PREKLAD_FAZE["LAST_32"]
        if "LAST_16" in faze_str: return PREKLAD_FAZE["LAST_16"]
        if "QUARTER_FINALS" in faze_str: return PREKLAD_FAZE["QUARTER_FINALS"]
        if "SEMI_FINALS" in faze_str: return PREKLAD_FAZE["SEMI_FINALS"]
        if "THIRD_PLACE" in faze_str: return PREKLAD_FAZE["THIRD_PLACE"]
        if "FINAL" in faze_str: return PREKLAD_FAZE["FINAL"]
        return faze_str

    # 🛡️ BEZPEČNÁ POJISTKA PROTI PRÁZDNÝM DATŮM
    if not data or "zapasy" not in data or len(data["zapasy"]) == 0:
        st.error("❌ Nepodařilo se načíst data o zápasech z Google tabulky.")
        st.info("💡 Klikni prosím v levém menu na tlačítko: **🔄 Aktualizovat data z tabulky**")
        st.stop()

    # 1. PŘEVOD NAČTENÝCH ZÁPASŮ NA DATAFRAME
    df_zapasy = pd.DataFrame(data["zapasy"])

    # 2. LOGIKA PLOVOUCÍHO DNE (Tvoje vyzkoušené funkční nastavení +4 hodiny)
    hraci_dny_list = []
    ceske_casy_list = []
    for idx, row in df_zapasy.iterrows():
        try:
            gmt_dt = pd.to_datetime(row["datum"])
            cz_dt = gmt_dt + pd.Timedelta(hours=4)  
            ceske_casy_list.append(cz_dt.strftime("%Y-%m-%d %H:%M"))
            virtual_dt = cz_dt - pd.Timedelta(hours=12)
            hraci_den = virtual_dt.strftime("%Y-%m-%d")
        except:
            ceske_casy_list.append(row["datum"])
            hraci_den = "Neznámé datum"
        hraci_dny_list.append(hraci_den)
    
    df_zapasy["hraci_den"] = hraci_dny_list
    df_zapasy["cesky_cas"] = ceske_casy_list

    unikatni_dny = sorted(list(df_zapasy["hraci_den"].unique()))
    if "Neznámé datum" in unikatni_dny: unikatni_dny.remove("Neznámé datum")

    def zformatuj_den(den_str):
        try:
            d = pd.to_datetime(den_str)
            dny_tydne = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
            return f"{dny_tydne[d.weekday()]} {d.strftime('%d.%m.%Y')}"
        except: return den_str

    dnesni_datum_str = time.strftime("%Y-%m-%d")
    index_vychozi = 0
    if dnesni_datum_str in unikatni_dny:
        index_vychozi = unikatni_dny.index(dnesni_datum_str)

    vybrany_den_raw = st.selectbox("📅 Vyber hrací den:", unikatni_dny, index=index_vychozi, format_func=zformatuj_den)
    zapasy_dne = df_zapasy[df_zapasy["hraci_den"] == vybrany_den_raw].sort_values(by="datum")

    if zapasy_dne.empty:
        st.info("🌴 Pro tento den nejsou naplánovány žádné zápasy.")
        st.stop()

    st.write(f"### ⚽ Zápasy pro den: {zformatuj_den(vybrany_den_raw)}")

    # 3. NAČTENÍ DOSAVADNÍCH TIPŮ DO SESSION STATE
    df_tipy = pd.DataFrame(data["tipy"]) if data.get("tipy") else pd.DataFrame()

    # Inicializujeme session state klíče
    for _, z in zapasy_dne.iterrows():
        zapas_id = int(z["id"])
        key_d = f"v_d_{zapas_id}"
        key_h = f"v_h_{zapas_id}"
        key_zol = f"v_zol_{zapas_id}"
        
        if key_d not in st.session_state:
            stajici_d = 0
            stajici_h = 0
            stavajici_zolik = False
            if not df_tipy.empty and "hrac" in df_tipy.columns and "zapas_id" in df_tipy.columns:
                stavy = df_tipy[(df_tipy["hrac"] == current_user) & (df_tipy["zapas_id"] == zapas_id)]
                if not stavy.empty:
                    stajici_d = int(stavy.iloc[0]["tip_d"])
                    stajici_h = int(stavy.iloc[0]["tip_h"])
                    stavajici_zolik = bool(stavy.iloc[0]["zolik"])
            
            st.session_state[key_d] = stajici_d
            st.session_state[key_h] = stajici_h
            st.session_state[key_zol] = stavajici_zolik

    
    # 4. VYKRESLENÍ MATICE ZÁPASŮ (Kompletní stabilní mobilní verze přes HTML inputy)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # JavaScript pro automatické přeskakování mezi políčky při psaní
    st.markdown("""
        <script>
        function skocNaDalsi(currentInput, nextInputId) {
            if (currentInput.value.length >= 1) {
                document.getElementById(nextInputId).focus();
            }
        }
        </script>
    """, unsafe_allow_html=True)
    
    col_vnejsi_vlevo, col_hlavni_obsah, col_vnejsi_vpravo = st.columns([0.1, 5.8, 0.1])
    
    with col_hlavni_obsah:
        for _, z in zapasy_dne.iterrows():
            zapas_id = int(z["id"])
            tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
            tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
            cas_zapasu = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
            
            pismeno_skupiny = str(z["skupina"]).strip() if pd.notna(z["skupina"]) else ""
            faze_cz = preloz_fazi(z["faze"])

            # Načtení stávajících hodnot ze session_state
            val_d = st.session_state[f"v_d_{zapas_id}"]
            val_h = st.session_state[f"v_h_{zapas_id}"]

            # Pouze 2 hlavní sloupce: [ Levý: Info a Tabulka (65%) ]  [ Pravý: Zadání tipu (35%) ]
            c_vlevo, c_vpravo = st.columns([6.5, 3.5])
            
            with c_vlevo:
                # Vlajky s rámečkem a stínem proti bílému pozadí
                vlajka_d_html = f"<img src='{z['vlajka_d']}' width='18' style='border: 1px solid #ccc; box-shadow: 1px 1px 2px rgba(0,0,0,0.1); vertical-align: middle;'> " if z.get("vlajka_d") else ""
                vlajka_h_html = f" <img src='{z['vlajka_h']}' width='18' style='border: 1px solid #ccc; box-shadow: 1px 1px 2px rgba(0,0,0,0.1); vertical-align: middle.'>" if z.get("vlajka_h") else ""
                
                zapas_text = f"<b>{tým_d_cz}</b> {vlajka_d_html}vs{vlajka_h_html} <b>{tým_h_cz}</b>"
                
                st.markdown(f"""
                    <div style='line-height: 1.2; padding-top: 5px; margin-bottom: 5px;'>
                        <span style='font-size: 0.95rem; color: #111;'>{zapas_text}</span><br>
                        <small style='color: #666;'>🕒 {cas_zapasu} | {faze_cz}</small>
                    </div>
                """, unsafe_allow_html=True)
                
                # Popover s tabulkou skupiny zůstává na svém místě
                if pismeno_skupiny and pismeno_skupiny != "None" and pismeno_skupiny != "":
                    with st.popover(f"🏆 Sk. {pismeno_skupiny}", use_container_width=False):
                        st.write(f"### 📊 Aktuální tabulka — Skupina {pismeno_skupiny}")
                        df_tabulka = spocitej_tabulku_skupiny(df_zapasy, pismeno_skupiny)
                        if not df_tabulka.empty:
                            st.dataframe(df_tabulka, use_container_width=False)
                        else:
                            st.info("Tabulka je prázdná, turnaj ještě nezačal.")
            
            with c_vpravo:
                # Vykreslíme ultra-kompaktní zadávací blok vedle sebe: [Input] : [Input] [Žolík]
                # Použijeme standardní Streamlit number_inputy, ale seskládané natěsno bez popisků
                c_in_d, c_sep, c_in_h, c_ch_z = st.columns([1.2, 0.3, 1.2, 1.0])
                
                with c_in_d:
                    # Input pro domácí tým
                    st.session_state[f"v_d_{zapas_id}"] = st.number_input(
                        "D", min_value=0, max_value=20, 
                        value=int(val_d), step=1, 
                        key=f"num_d_{zapas_id}", label_visibility="collapsed"
                    )
                
                with c_sep:
                    st.markdown("<div style='text-align: center; font-weight: bold; padding-top: 6px; color: #888;'>vs</div>", unsafe_allow_html=True)
                
                with c_in_h:
                    # Input pro hostující tým
                    st.session_state[f"v_h_{zapas_id}"] = st.number_input(
                        "H", min_value=0, max_value=20, 
                        value=int(val_h), step=1, 
                        key=f"num_h_{zapas_id}", label_visibility="collapsed"
                    )
                    
                with c_ch_z:
                    # Čistý checkbox pro žolíka
                    st.session_state[f"v_zol_{zapas_id}"] = st.checkbox(
                        "🃏", value=st.session_state[f"v_zol_{zapas_id}"], 
                        key=f"ch_z_{zapas_id}", label_visibility="collapsed"
                    )
            
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

        # 5. JEDINÉ SPOLEČNÉ UKLÁDACÍ TLAČÍTKO NA KONCI
        st.markdown("<br>", unsafe_allow_html=True)
        _, c_btn_m, _ = st.columns([1.5, 2, 1.5])
        
        with c_btn_m:
            if st.button("💾 Uložit všechny tipy pro tento den", key="save_all_day_tips", use_container_width=True):
                # Kontrola žolíků ze session state
                vybrani_zolici = [st.session_state[f"v_zol_{z['id']}"] for _, z in zapasy_dne.iterrows()]
                
                if sum(vybrani_zolici) > 1:
                    st.error("❌ Chyba: Můžeš si vybrat pouze jednoho Žolíka na jeden hrací den!")
                else:
                    with st.spinner("Odesílám balíček dat do Google tabulky..."):
                        seznam_tipu_k_odeslani = []
                        for _, z in zapasy_dne.iterrows():
                            z_id = int(z["id"])
                            seznam_tipu_k_odeslani.append({
                                "zapas_id": z_id,
                                "tip_d": int(st.session_state[f"v_d_{z_id}"]),
                                "tip_h": int(st.session_state[f"v_h_{z_id}"]),
                                "zolik": bool(st.session_state[f"v_zol_{z_id}"])
                            })
                        
                        URL_API = "https://script.google.com/macros/s/AKfycbypVyn-7dy9KRAvlTmRkZ7R9d66Ux9LraaSDeC0A8m0C1LGvcRmuq2lh-jlPSgbL9y1/exec"
                        payload = {
                            "action": "uloz_vsechny_tipy",
                            "hrac": current_user,
                            "tipy": seznam_tipu_k_odeslani
                        }
                        
                        try:
                            res = requests.post(URL_API, json=payload, timeout=15)
                            if res.status_code == 200 and res.json().get("success"):
                                st.success("🎉 Tipy uloženy do Google Sheets!")
                                # 🔥 Klíčové: Smažeme cache stahování, aby si aplikace pro příští vykreslení stáhla čerstvá nová data
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Chyba při hromadném zápisu.")
                        except Exception as e:
                            st.error(f"Spojení selhalo: {e}")
                            
elif volba == "Celoturnajové tipy 🔮":
    st.title("🔮 Celoturnajové dlouhodobé tipy")
    c_l, c_main, c_r = st.columns([1, 4, 1])
    with c_main:
        st.title("🏆 Celoturnajové dlouhodobé tipy")
        
        je_zamknuto_spravcem = data.get("nastaveni", {}).get("dlouhodobe_zamknuto", False)
        if current_user == "admin":
            dlouhodobe_disabled = False
        else:
            dlouhodobe_disabled = je_zamknuto_spravcem
            
        # Načtení starých hodnot ze struktury
        ct = data["celkove_tipy"].get(current_user, {})
        stary_mistr = ct.get("mistr", "")
        semi_list = ct.get("semifinale", ["", "", "", ""])
        while len(semi_list) < 4: semi_list.append("")
        stary_cesko = ct.get("cesko", "Základní skupina")
        stary_mvp = ct.get("mvp", "")
        stary_goly = ct.get("goly", 0)
        
        with st.form("dlouhodobe_tipy_form"):
            st.write("### Vyplň své celoturnajové tipy")
            
            tip_mistr = st.text_input("Celkový vítěz turnaje 🏆", value=stary_mistr, disabled=dlouhodobe_disabled)
            
            st.write("**4 semifinalisté (týmy, které postoupí do bojů o medaile) 🏒**")
            semi1 = st.text_input("Semifinalista 1", value=semi_list[0], disabled=dlouhodobe_disabled)
            semi2 = st.text_input("Semifinalista 2", value=semi_list[1], disabled=dlouhodobe_disabled)
            semi3 = st.text_input("Semifinalista 3", value=semi_list[2], disabled=dlouhodobe_disabled)
            semi4 = st.text_input("Semifinalista 4", value=semi_list[3], disabled=dlouhodobe_disabled)

           
            faze_options = ["Základní skupina", "Šestnáctifinále (1/32)", "Osmifinále (1/16)", "Čtvrtfinále", "Semifinále", "O 3. místo 🥉", "FINÁLE 🏆"]
            if stary_cesko not in faze_options: stary_cesko = "Základní skupina"
            tip_cesko = st.selectbox("Kam až dojde český tým? 🇨🇿", options=faze_options, index=faze_options.index(stary_cesko), disabled=dlouhodobe_disabled)
            
            tip_mvp = st.text_input("Počet bodů MVP 🌟", value=stary_mvp, disabled=dlouhodobe_disabled)
            tip_goly = st.number_input("Celkový počet gólů v celém turnaji 🥅", min_value=0, value=int(stary_goly), step=1, disabled=dlouhodobe_disabled)
            
            uloz_dl_button = st.form_submit_button("Uložit celoturnajové tipy 💾")
            
        if uloz_dl_button:
            data["celkove_tipy"][current_user] = {
                "mistr": tip_mistr,
                "semifinale": [semi1, semi2, semi3, semi4],
                "cesko": tip_cesko,
                "mvp": tip_mvp,
                "goly": int(tip_goly)
            }
            uloz_do_google_sheets(data)
            st.success("Tipy úspěšně uloženy!")
            time.sleep(0.5)
            st.rerun()
            
        if je_zamknuto_spravcem and current_user != "admin":
            st.error("🔒 Dlouhodobé tipy byly uzamčeny správcem, hodnoty již nelze upravovat.")
    st.write("---")
    st.subheader("🇪🇺 Průzkumník živých dat z Ligy mistrů (API)")
    st.write("Pojďme se podívat, co API posílá u velkých odehraných zápasů.")

    #Testování načítání dat z API
    # Zde použijeme tvůj API klíč, který už v aplikaci určitě máš nadefinovaný (např. v nastavení nebo jako konstantu)
    # Pokud ho máš schovaný jinak, uprav proměnnou níže:
    API_KLIC = "24c6237d44e349179857f3ec7e229d00" 
    
    hlavicka = {"X-Auth-Token": API_KLIC}

    # Tlačítko 1: Načíst poslední zápasy Ligy mistrů (abychom našli to správné číslo zápasu)
    if st.button("📅 Načíst poslední zápasy Ligy mistrů (Soutěž CL)"):
        with st.spinner("Tahám zápasy z API..."):
            # Odkaz na zápasy Champions League
            url_cl = "https://api.football-data.org/v4/competitions/ELC/matches?status=FINISHED"
            try:
                res = requests.get(url_cl, headers=hlavicka, timeout=10)
                if res.status_code == 200:
                    data_cl = res.json()
                    matches = data_cl.get("matches", [])
                    
                    if matches:
                        st.success(f"Nalezeno {len(matches)} odehraných zápasů v LM. Zde jsou poslední z nich:")
                        # Ukážeme tabulku s ID zápasů, abychom viděli ta čísla
                        prehled_zapasu = []
                        for m in matches[-5:]:  # Vezmeme posledních 5 (včetně finále)
                            prehled_zapasu.append({
                                "ID zápasu (ČÍSLO)": m["id"],
                                "Datum": m["utcDate"],
                                "Zápas": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}",
                                "Výsledek": f"{m['score']['fullTime']['home']}:{m['score']['fullTime']['away']}"
                            })
                        st.table(prehled_zapasu)
                    else:
                        st.warning("API nevrátilo žádné odehrané zápasy pro kód soutěže 'CL'.")
                else:
                    st.error(f"Chyba komunikace s API: {res.status_code} ({res.text})")
            except Exception as e:
                st.error(f"Selhalo spojení: {e}")

    st.write("---")

    # Tlačítko 2: Detektor konkrétního čísla zápasu
    id_zapasu_vstup = st.text_input("Zadej ČÍSLO zápasu (ID), které tě zajímá:", value="497424") # Výchozí tip na ID

    if st.button("👁️ Stáhnout a zobrazit detail zápasu z API"):
        if id_zapasu_vstup:
            with st.spinner(f"Stahuji detail zápasu ID {id_zapasu_vstup}..."):
                url_detail = f"https://api.football-data.org/v4/matches/{id_zapasu_vstup}"
                try:
                    res = requests.get(url_detail, headers=hlavicka, timeout=10)
                    if res.status_code == 200:
                        st.success("🎉 Data úspěšně stažena!")
                        # Vypíšeme kompletní syrový strom dat
                        st.json(res.json())
                    else:
                        st.error(f"Zápas s ID {id_zapasu_vstup} nebyl nalezen nebo k němu nemáš v bezplatném tarifu přístup. Kód: {res.status_code}")
                except Exception as e:
                    st.error(f"Chyba: {e}")
    st.write("---")

elif volba == "Správa API a zápasů ⚙️" and current_user == "admin":
    st.title("⚙️ Administrace: Import zápasů z Football-Data.org")
    st.write("Tlačítko níže stáhne všech 104 zápasů turnaje 2026 a odešle je přes Google Apps Script do tvé tabulky.")

    # Tvoje definice pro Google Apps Script a Football-Data.org
    URL_API = "https://script.google.com/macros/s/AKfycbzckuQpf_fNckc9R9rrW9b7y9HUqqFHjxuD8Djd8PORtWL7zuU0l7DX1JgC92zw5aN5/exec"
    NEW_API_KEY = "24c6237d44e349179857f3ec7e229d00"
    NEW_BASE_URL = "https://api.football-data.org/v4"
    new_headers = { "X-Auth-Token": NEW_API_KEY }

    if st.button("🚀 Stáhnout a hromadně uložit rozpis turnaje"):
        with st.spinner("Komunikuji s API a připravuji zápasy..."):
            url = f"{NEW_BASE_URL}/competitions/WC/matches"
            try:
                res = requests.get(url, headers=new_headers, timeout=10)
                data_api = res.json()
                
                if res.status_code == 200:
                    matches = data_api.get("matches", [])
                    
                    if not matches:
                        st.warning("API nevrátilo žádné zápasy.")
                    else:
                        nove_zapasy_list = []
                        
                        for idx, m in enumerate(matches):
                            # Očištění skupiny (GROUP_A -> A)
                            raw_group = m.get("group")
                            skupina = raw_group.replace("GROUP_", "") if raw_group else ""
                            
                            # Úprava data na hezký formát (2026-06-15T18:00:00Z -> 2026-06-15 18:00)
                            raw_date = m.get("utcDate", "")
                            hezky_datum = raw_date.replace("T", " ")[:16] if raw_date else ""
                            
                            # Mapování stavu zápasu z API na náš systém
                            api_status = m.get("status")
                            nas_status = "FINISHED" if api_status == "FINISHED" else "NS"
                            
                            novy_zapas = {
                                "id": int(idx + 1),
                                "api_id": int(m.get("id")),
                                "datum": str(hezky_datum),
                                "faze": str(m.get("stage")),
                                "skupina": str(skupina),
                                "domaci": str(m.get("homeTeam", {}).get("name", "TBD")),
                                "hoste": str(m.get("awayTeam", {}).get("name", "TBD")),
                                "vlajka_d": str(m.get("homeTeam", {}).get("crest", "")),
                                "vlajka_h": str(m.get("awayTeam", {}).get("crest", "")),
                                "goly_d": m.get("score", {}).get("fullTime", {}).get("home"),
                                "goly_h": m.get("score", {}).get("fullTime", {}).get("away"),
                                "status": str(nas_status)
                            }
                            # Pokud góly ještě nejsou, dáme prázdný řetězec
                            if novy_zapas["goly_d"] is None: novy_zapas["goly_d"] = ""
                            if novy_zapas["goly_h"] is None: novy_zapas["goly_h"] = ""
                            
                            nove_zapasy_list.append(novy_zapas)
                        
                        st.write("### 📋 Náhled dat odesílaných do Google tabulky:")
                        st.dataframe(pd.DataFrame(nove_zapasy_list).head(5))
                        
                        # 🔥 ODESLÁNÍ PŘES GOOGLE APPS SCRIPT (POST POŽADAVEK)
                        st.write("🔄 Posílám data přes Apps Script...")
                        
                        # Připravíme payload pro tvůj script (předáme akci a samotná data)
                        payload = {
                            "action": "uloz_zapasy",  # Pokud tvůj script rozlišuje akce, případně uprav podle potřeby
                            "data": nove_zapasy_list
                        }
                        
                        # Pošleme data na tvůj Google Script link
                        script_res = requests.post(URL_API, json=payload, timeout=15)
                        
                        if script_res.status_code == 200:
                            st.success(f"🔥 Všech {len(nove_zapasy_list)} zápasů bylo úspěšně odesláno a uloženo do Google Sheets přes tvůj script!")
                            st.cache_data.clear()
                        else:
                            st.error(f"Google Script sice odpověděl, ale vrátil chybu (Status {script_res.status_code}): {script_res.text}")
                            
                else:
                    st.error(f"Chyba API: {data_api.get('message')}")
            except Exception as e:
                st.error(f"Chyba při komunikaci nebo zápisu: {e}")
