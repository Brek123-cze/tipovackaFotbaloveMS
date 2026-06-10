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

if st.sidebar.button("🔄 Aktualizovat data z tabulky", use_container_width=True):
    st.cache_data.clear()  
    st.rerun()


# =========================================================================
# ⚽ FOTBALOVÁ LOGIKA BODOVÁNÍ PRO HRÁČE
# =========================================================================
def spocitej_body_hrace(tip_d, tip_h, real_d, real_h, zolik=False):
    if tip_d is None or tip_h is None or real_d is None or real_h is None:
        return 0, False

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

    if tip_d == real_d_efektivni and tip_h == real_h_efektivni:
        body = 10
        presny = True
    elif (vitez_tip == vitez_real and rozdil_tip == rozdil_real) or \
         (vitez_tip == vitez_real and goly_tip == goly_real) or \
         (vitez_real == "R" and vitez_tip == "R"):
        body = 6
    elif vitez_tip == vitez_real:
        body = 3
    else:
        body = 0

    if zolik:
        if body > 0:
            body = body * 2  
        else:
            body = -3        

    return body, presny


# =========================================================================
# 🔄 INICIALIZACE A VÝPOČET STATISTIK TIPÉRŮ PRO ŽEBŘÍČEK
# =========================================================================
celkove_goly_ms = 0
if data.get("zapasy"):
    for z in data["zapasy"]:
        if z.get("status") == "FINISHED" and pd.notna(z.get("goly_d")) and str(z["goly_d"]) != "":
            celkove_goly_ms += (int(z["goly_d"]) + int(z["goly_h"]))

statistiky_hracu = {h: {"body": 0, "presne": 0} for h in HRACI}
df_vsechny_tipy = pd.DataFrame(data.get("tipy", []))

if data.get("zapasy"):
    for z in data["zapasy"]:
        z_id = int(z["id"])
        
        if z.get("status") == "FINISHED" and pd.notna(z.get("goly_d")) and str(z["goly_d"]) != "":
            real_d = int(z["goly_d"])
            real_h = int(z["goly_h"])
            
            for hrac in HRACI:
                t_d, t_h, zolik = None, None, False
                
                if not df_vsechny_tipy.empty:
                    filtr = df_vsechny_tipy[(df_vsechny_tipy["hrac"] == hrac) & (df_vsechny_tipy["zapas_id"].astype(int) == z_id)]
                    
                    if not filtr.empty:
                        row_tip = filtr.iloc[0]
                        if pd.notna(row_tip.get("tip_d")) and pd.notna(row_tip.get("tip_h")):
                            if str(row_tip["tip_d"]) != "" and str(row_tip["tip_h"]) != "":
                                t_d = int(row_tip["tip_d"])
                                t_h = int(row_tip["tip_h"])
                        
                        if "zolik" in row_tip:
                            zolik = bool(row_tip["zolik"])

                if t_d is not None and t_h is not None:
                    b, p = spocitej_body_hrace(t_d, t_h, real_d, real_h, zolik)
                    statistiky_hracu[hrac]["body"] += b
                    if p: 
                        statistiky_hracu[hrac]["presne"] += 1

# 🔮 PŘIČTENÍ BODŮ ZA CELOTURNAJOVÉ DLOUHODOBÉ TIPY
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

for hrac in HRACI:
    ct = data.get("celkove_tipy", {}).get(hrac, {})
    if real_mistr and ct.get("mistr", "").strip().lower() == real_mistr:
        statistiky_hracu[hrac]["body"] += 20
        
    hrac_semi = [str(s).strip().lower() for s in ct.get("semifinale", ["", "", "", ""])]
    for tym in hrac_semi:
        if tym and tym in real_semi:
            statistiky_hracu[hrac]["body"] += 10
            
    if real_cesko and ct.get("cesko") == real_cesko:
        statistiky_hracu[hrac]["body"] += 20
        
    tip_mvp = ct.get("mvp", "").strip().lower()
    if real_mvp and tip_mvp and (real_mvp in tip_mvp or tip_mvp in real_mvp):
        statistiky_hracu[hrac]["body"] += 20
        
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
# POMOCNÁ FUNKCE PRO FORMÁTOVÁNÍ VÝSLEDKŮ NA HLAVNÍ STRÁNCE
# =========================================================================
def formatuj_vysledek_hlavni_strana(z):
    if z.get("status") != "FINISHED" or pd.isna(z.get("goly_d")):
        return ""
    
    tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
    tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
    
    gd = int(z["goly_d"])
    gh = int(z["goly_h"])
    
    polocas = ""
    if pd.notna(z.get("halftime_d")) and str(z["halftime_d"]) != "":
        polocas = f" ({int(z['halftime_d'])}:{int(z['halftime_h'])})"
        
    zakladni_cast = f"<b>{tým_d_cz}</b> {gd}:{gh}{polocas} <b>{tým_h_cz}</b>"
    
    dodatky = []
    dur = str(z.get("duration", "")).upper()
    
    if "EXTRA" in dur or "PENALTY" in dur or (pd.notna(z.get("extratime_d")) and str(z["extratime_d"]) != ""):
        if pd.notna(z.get("extratime_d")) and str(z["extratime_d"]) != "":
            dodatky.append(f"pr {int(z['extratime_d'])}:{int(z['extratime_h'])}")
        else:
            dodatky.append("pr")
            
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
        # 1. HLAVNÍ GRAFICKÝ ŽEBŘÍČEK
        zebricek = [{"jmeno": h, "body": v["body"], "presne": v["presne"]} for h, v in statistiky_hracu.items()]
        zebricek = sorted(zebricek, key=lambda x: (x["body"], x["presne"]), reverse=True)
        
        for idx, p in enumerate(zebricek):
            medaile = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "🔵"
            st.markdown(f"<div style='background-color: rgba(30,61,89,0.05); padding: 8px; border-radius: 6px; margin-bottom: 4px; display: flex; justify-content: space-between;'><b>{medaile} {idx+1}. {p['jmeno']}</b><span><b>{p['body']} B</b> (🎯 {p['presne']}x)</span></div>", unsafe_allow_html=True)

        st.info(f"🚨 **Celkový počet gólů vstřelených na celém šampionátu:** {celkove_goly_ms} gólů")

        # =========================================================================
        # ⚽ PŘEHLED ZÁPASŮ POD ŽEBŘÍČKEM
        # =========================================================================
        if data.get("zapasy"):
            st.markdown("<br><hr style='margin: 15px 0; border-top: 2px solid #ccc;'>", unsafe_allow_html=True)
            st.subheader("📊 Výsledky a program zápasů")

            df_zapasy_local = pd.DataFrame(data["zapasy"])
            
            # Použijeme stejnou logiku časového posunu hracího dne jako v Moje tipy
            hraci_dny_loc = []
            ceske_casy_loc = []
            for _, r in df_zapasy_local.iterrows():
                try:
                    gmt_dt = pd.to_datetime(r["datum"])
                    cz_dt = gmt_dt + pd.Timedelta(hours=4)  
                    ceske_casy_loc.append(cz_dt.strftime("%Y-%m-%d %H:%M"))
                    virtual_dt = cz_dt - pd.Timedelta(hours=12)
                    hraci_dny_loc.append(virtual_dt.strftime("%Y-%m-%d"))
                except:
                    ceske_casy_loc.append(r["datum"])
                    hraci_dny_loc.append("Neznámé datum")
            
            df_zapasy_local["hraci_den"] = hraci_dny_loc
            df_zapasy_local["cesky_cas"] = ceske_casy_loc

            dnesni_den_aplikace = time.strftime("%Y-%m-%d") 
            vcerejsi_den_aplikace = (pd.to_datetime(dnesni_den_aplikace) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

            tab_dnes, tab_vcera = st.tabs([f"📅 Dnešní zápasy", f"⏪ Včerejší výsledky"])

            with tab_dnes:
                zapasy_dnes = df_zapasy_local[df_zapasy_local["hraci_den"] == dnesni_den_aplikace].sort_values(by="datum")
                if zapasy_dnes.empty:
                    st.info("Dnes nejsou v plánu žádné zápasy.")
                else:
                    for _, z in zapasy_dnes.iterrows():
                        if z["status"] == "FINISHED":
                            st.markdown(formatuj_vysledek_hlavni_strana(z), unsafe_allow_html=True)
                        else:
                            cas = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
                            tým_d = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
                            tým_h = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
                            st.markdown(f"<div style='color: #555; padding: 4px 0;'>🕒 {cas} | {tým_d} vs {tým_h} <i>(neodehráno)</i></div>", unsafe_allow_html=True)

            with tab_vcera:
                zapasy_vcera = df_zapasy_local[df_zapasy_local["hraci_den"] == vcerejsi_den_aplikace].sort_values(by="datum")
                if zapasy_vcera.empty:
                    st.info("Včera se nehrály žádné zápasy.")
                else:
                    for _, z in zapasy_vcera.iterrows():
                        if z["status"] == "FINISHED":
                            st.markdown(formatuj_vysledek_hlavni_strana(z), unsafe_allow_html=True)
                        else:
                            cas = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
                            tým_d = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
                            tým_h = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
                            st.markdown(f"<div style='color: #777; padding: 4px 0;'>🕒 {cas} | {tým_d} vs {tým_h} <i>(nedohráno)</i></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 📦 EXPANDER 1: DETAILNÍ BODOVÁNÍ TIPÉRU (ZÁPAS PO ZÁPASE)
        with st.expander("📊 Rozbalit detailní přehled bodů (zápas po zápase)"):
            prehled_bodu_data = []

            for hrac in HRACI:
                radek_hrace = {"Hráč": hrac}
                
                if data.get("zapasy"):
                    for z in data["zapasy"]:
                        z_id = int(z["id"])
                        body_za_zapas = 0
                        
                        if z.get("status") == "FINISHED" and pd.notna(z.get("goly_d")) and str(z["goly_d"]) != "":
                            if not df_vsechny_tipy.empty:
                                filtr = df_vsechny_tipy[(df_vsechny_tipy["hrac"] == hrac) & (df_vsechny_tipy["zapas_id"].astype(int) == z_id)]
                                if not filtr.empty:
                                    row_tip = filtr.iloc[0]
                                    if pd.notna(row_tip.get("tip_d")) and pd.notna(row_tip.get("tip_h")):
                                        if str(row_tip["tip_d"]) != "" and str(row_tip["tip_h"]) != "":
                                            zolik = bool(row_tip.get("zolik", False))
                                            body_za_zapas, _ = spocitej_body_hrace(int(row_tip["tip_d"]), int(row_tip["tip_h"]), int(z["goly_d"]), int(z["goly_h"]), zolik)
                        
                        prefix = f"Z{z_id}"
                        tymy_zkratka = f"{z['domaci'][0:3]}-{z['hoste'][0:3]}"
                        radek_hrace[f"{prefix} ({tymy_zkratka})"] = body_za_zapas

                # Celoturnajové dlouhodobé body pro expander
                body_celkove = 0
                ct = data.get("celkove_tipy", {}).get(hrac, {})
                if real_mistr and ct.get("mistr", "").strip().lower() == real_mistr: body_celkove += 20
                hrac_semi = [str(s).strip().lower() for s in ct.get("semifinale", ["", "", "", ""])]
                for tym in hrac_semi:
                    if tym and tym in real_semi: body_celkove += 10
                if real_cesko and ct.get("cesko") == real_cesko: body_celkove += 20
                tip_mvp = ct.get("mvp", "").strip().lower()
                if real_mvp and tip_mvp and (real_mvp in tip_mvp or tip_mvp in real_mvp): body_celkove += 20
                try:
                    tip_goly = int(ct.get("goly", 0))
                except:
                    tip_goly = 0
                if real_goly > 0 and tip_goly > 0:
                    if tip_goly == real_goly: body_celkove += 20
                    elif abs(tip_goly - real_goly) <= 3: body_celkove += 10
                
                radek_hrace["🔮 Celoturnajové body"] = body_celkove
                prehled_bodu_data.append(radek_hrace)

            if prehled_bodu_data:
                df_kompletni_prehled = pd.DataFrame(prehled_bodu_data)
                st.dataframe(
                    df_kompletni_prehled, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"Hráč": st.column_config.TextColumn("Hráč", pinned=True)}
                )

elif volba == "Moje tipy 📝":
    def spocitej_tabulku_skupiny(df_vsechny_zapasy, pismeno_skupiny):
        df_sk = df_vsechny_zapasy[
            (df_vsechny_zapasy["skupina"] == pismeno_skupiny) & 
            (df_vsechny_zapasy["faze"].str.contains("GROUP", na=False))
        ]
        tymy_stats = {}
        vsechny_tymy_skupiny = set(df_sk["domaci"].dropna().unique()).union(set(df_sk["hoste"].dropna().unique()))
        for t in vsechny_tymy_skupiny:
            tymy_stats[t] = {"Z": 0, "V": 0, "R": 0, "P": 0, "Skóre": "0:0", "Skóre_Rozdil": 0, "B": 0}
            
        for _, z in df_sk.iterrows():
            if pd.notna(z["goly_d"]) and pd.notna(z["goly_h"]) and str(z["goly_d"]) != "" and str(z["goly_h"]) != "":
                gd = int(z["goly_d"])
                gh = int(z["goly_h"])
                td = z["domaci"]
                th = z["hoste"]
                
                if "Goly_Vstrelene" not in tymy_stats[td]: tymy_stats[td]["Goly_Vstrelene"] = 0
                if "Goly_Inkasovane" not in tymy_stats[td]: tymy_stats[td]["Goly_Inkasovane"] = 0
                if "Goly_Vstrelene" not in tymy_stats[th]: tymy_stats[th]["Goly_Vstrelene"] = 0
                if "Goly_Inkasovane" not in tymy_stats[th]: tymy_stats[th]["Goly_Inkasovane"] = 0

                tymy_stats[td]["Z"] += 1; tymy_stats[th]["Z"] += 1
                
                if gd > gh:
                    tymy_stats[td]["V"] += 1; tymy_stats[td]["B"] += 3
                    tymy_stats[th]["P"] += 1
                elif gd < gh:
                    tymy_stats[th]["V"] += 1; tymy_stats[th]["B"] += 3
                    tymy_stats[td]["P"] += 1
                else:
                    tymy_stats[td]["R"] += 1; tymy_stats[td]["B"] += 1
                    tymy_stats[th]["R"] += 1; tymy_stats[th]["B"] += 1
                    
                tymy_stats[td]["Goly_Vstrelene"] += gd
                tymy_stats[td]["Goly_Inkasovane"] += gh
                tymy_stats[th]["Goly_Vstrelene"] += gh
                tymy_stats[th]["Goly_Inkasovane"] += gd
                tymy_stats[td]["Skóre_Rozdil"] += (gd - gh)
                tymy_stats[th]["Skóre_Rozdil"] += (gh - gd)

        tabulka_data = []
        for t, s in tymy_stats.items():
            tým_cz = PREKLAD_TYMU.get(t, t)
            vstrelene = s.get("Goly_Vstrelene", 0)
            inkasovane = s.get("Goly_Inkasovane", 0)
            tabulka_data.append({
                "Tým": tým_cz, "Z": s["Z"], "V": s["V"], "R": s["R"], "P": s["P"], "Skóre": f"{vstrelene}:{inkasovane}", "B": s["B"], "Rozdil": s.get("Skóre_Rozdil", 0)
            })
            
        df_final = pd.DataFrame(tabulka_data)
        if not df_final.empty:
            df_final = df_final.sort_values(by=["B", "Rozdil"], ascending=[False, False]).reset_index(drop=True)
            df_final.index += 1  
            df_final = df_final.drop(columns=["Rozdil"])
        return df_final
    
    st.title("📝 Moje Tipy na zápasy MS 2026")
    st.write(f"Vítej ve svém tipovacím lístku, **{current_user}**.")

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

    PREKLAD_FAZE = {
        "GROUP_STAGE": "Základní skupina", "LAST_32": "Šestnáctifinále (1/32)", "LAST_16": "Osmifinále (1/16)",
        "QUARTER_FINALS": "Čtvrtfinále", "SEMI_FINALS": "Semifinále", "THIRD_PLACE": "O 3. místo 🥉", "FINAL": "FINÁLE 🏆"
    }

    def preloz_fazi(faze_str):
        if not faze_str or pd.isna(faze_str): return "Neznámá fáze"
        faze_str = str(faze_str).strip()
        if "GROUP_STAGE" in faze_str: return PREKLAD_FAZE["GROUP_STAGE"]
        if "LAST_32" in faze_str: return PREKLAD_FAZE["LAST_32"]
        if "LAST_16" in faze_str: return PREKLAD_FAZE["LAST_16"]
        if "QUARTER_FINALS" in faze_str: return PREKLAD_FAZE["QUARTER_FINALS"]
        if "SEMI_FINALS" in faze_str: return PREKLAD_FAZE["SEMI_FINALS"]
        if "THIRD_PLACE" in faze_str: return PREKLAD_FAZE["THIRD_PLACE"]
        if "FINAL" in faze_str: return PREKLAD_FAZE["FINAL"]
        return faze_str

    if not data or "zapasy" not in data or len(data["zapasy"]) == 0:
        st.error("❌ Nepodařilo se načíst data o zápasech z Google tabulky.")
        st.stop()

    df_zapasy = pd.DataFrame(data["zapasy"])

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

    for _, z in zapasy_dne.iterrows():
        zapas_id = int(z["id"])
        key_d = f"v_d_{zapas_id}"
        key_h = f"v_h_{zapas_id}"
        key_zol = f"v_zol_{zapas_id}"
        
        if key_d not in st.session_state:
            stajici_d, stajici_h, stavajici_zolik = 0, 0, False
            if not df_vsechny_tipy.empty:
                stavy = df_vsechny_tipy[(df_vsechny_tipy["hrac"] == current_user) & (df_vsechny_tipy["zapas_id"].astype(int) == zapas_id)]
                if not stavy.empty:
                    stajici_d = int(stavy.iloc[0]["tip_d"]) if pd.notna(stavy.iloc[0]["tip_d"]) else 0
                    stajici_h = int(stavy.iloc[0]["tip_h"]) if pd.notna(stavy.iloc[0]["tip_h"]) else 0
                    stavajici_zolik = bool(stavy.iloc[0]["zolik"]) if "zolik" in stavy.columns else False
            
            st.session_state[key_d] = stajici_d
            st.session_state[key_h] = stajici_h
            st.session_state[key_zol] = stavajici_zolik

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_vnejsi_vlevo, col_hlavni_obsah, col_vnejsi_vpravo = st.columns([0.1, 5.8, 0.1])
    
    with col_hlavni_obsah:
        for _, z in zapasy_dne.iterrows():
            zapas_id = int(z["id"])
            tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
            tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
            cas_zapasu = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
            
            pismeno_skupiny = str(z["skupina"]).strip() if pd.notna(z["skupina"]) else ""
            faze_cz = preloz_fazi(z["faze"])

            val_d = st.session_state[f"v_d_{zapas_id}"]
            val_h = st.session_state[f"v_h_{zapas_id}"]

            c_vlevo, c_vpravo = st.columns([6.5, 3.5])
            
            with c_vlevo:
                vlajka_d_html = f"<img src='{z['vlajka_d']}' width='18' style='border: 1px solid #ccc; box-shadow: 1px 1px 2px rgba(0,0,0,0.1); vertical-align: middle;'> " if z.get("vlajka_d") else ""
                vlajka_h_html = f" <img src='{z['vlajka_h']}' width='18' style='border: 1px solid #ccc; box-shadow: 1px 1px 2px rgba(0,0,0,0.1); vertical-align: middle.'>" if z.get("vlajka_h") else ""
                zapas_text = f"<b>{tým_d_cz}</b> {vlajka_d_html}vs{vlajka_h_html} <b>{tým_h_cz}</b>"
                
                st.markdown(f"""
                    <div style='line-height: 1.2; padding-top: 5px; margin-bottom: 5px;'>
                        <span style='font-size: 0.95rem; color: #111;'>{zapas_text}</span><br>
                        <small style='color: #666;'>🕒 {cas_zapasu} | {faze_cz}</small>
                    </div>
                """, unsafe_allow_html=True)
                
                if pismeno_skupiny and pismeno_skupiny != "None" and pismeno_skupiny != "":
                    with st.popover(f"🏆 Sk. {pismeno_skupiny}", use_container_width=False):
                        st.write(f"### 📊 Aktuální tabulka — Skupina {pismeno_skupiny}")
                        df_tabulka = spocitej_tabulku_skupiny(df_zapasy, pismeno_skupiny)
                        if not df_tabulka.empty:
                            st.dataframe(df_tabulka, use_container_width=False)
                        else:
                            st.info("Tabulka je prázdná, turnaj ještě nezačal.")
            
            with c_vpravo:
                c_in_d, c_sep, c_in_h, c_ch_z = st.columns([1.2, 0.3, 1.2, 1.0])
                with c_in_d:
                    st.session_state[f"v_d_{zapas_id}"] = st.number_input("D", min_value=0, max_value=20, value=int(val_d), step=1, key=f"num_d_{zapas_id}", label_visibility="collapsed")
                with c_sep:
                    st.markdown("<div style='text-align: center; font-weight: bold; padding-top: 6px; color: #888;'>vs</div>", unsafe_allow_html=True)
                with c_in_h:
                    st.session_state[f"v_h_{zapas_id}"] = st.number_input("H", min_value=0, max_value=20, value=int(val_h), step=1, key=f"num_h_{zapas_id}", label_visibility="collapsed")
                with c_ch_z:
                    st.session_state[f"v_zol_{zapas_id}"] = st.checkbox("🃏", value=st.session_state[f"v_zol_{zapas_id}"], key=f"ch_z_{zapas_id}", label_visibility="collapsed")
            
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        _, c_btn_m, _ = st.columns([1.5, 2, 1.5])
        
        with c_btn_m:
            if st.button("💾 Uložit všechny tipy pro tento den", key="save_all_day_tips", use_container_width=True):
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
                        payload = {"action": "uloz_vsechny_tipy", "hrac": current_user, "tipy": seznam_tipu_k_odeslani}
                        
                        try:
                            res = requests.post(URL_API, json=payload, timeout=15)
                            if res.status_code == 200 and res.json().get("success"):
                                st.success("🎉 Tipy uloženy do Google Sheets!")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Chyba při hromadném zápisu.")
                        except Exception as e:
                            st.error(f"Spojení selhalo: {e}")
                            
elif volba == "Celoturnajové tipy 🔮":
    st.title("🔮 Celoturnajové dlouhodobé tipy")
    
    # Seznam všech týmů pro selectboxy (vytaženo z tvého slovníku PREKLAD_TYMU)
    seznam_tymu_selectbox = ["-- Vyber tým --"] + sorted(list(PREKLAD_TYMU.values()))
    
    # Seznam střelců pro roletku MVP
    seznam_strelcu_selectbox = [
        "-- Vyber hráče --",
        "Kylian Mbappé (Francie)", "Lamine Yamal (Španělsko)", "Jude Bellingham (Anglie)",
        "Harry Kane (Anglie)", "Vinícius Júnior (Brazílie)", "Lionel Messi (Argentina)",
        "Cristiano Ronaldo (Portugalsko)", "Jamal Musiala (Německo)", "Florian Wirtz (Německo)",
        "Cody Gakpo (Nizozemsko)", "Patrik Schick (Česko)", "Tomáš Souček (Česko)",
        "Erling Haaland (Norsko)", "Kevin De Bruyne (Belgie)"
    ]

    # Bezpečné načtení dat o zamknutí
    je_zamknuto_spravcem = data.get("nastaveni", {}).get("dlouhodobe_zamknuto", False)
    dlouhodobe_disabled = False if current_user == "admin" else je_zamknuto_spravcem
        
    ct = data.get("celkove_tipy", {}).get(current_user, {}) if data.get("celkove_tipy") else {}
    
    # Pomocné funkce pro bezpečné zjištění indexu starých hodnot v roletkách
    def ziskej_index_tymu(stary_tip):
        if stary_tip in seznam_tymu_selectbox:
            return seznam_tymu_selectbox.index(stary_tip)
        return 0

    def ziskej_index_strelce(stary_tip):
        if stary_tip in seznam_strelcu_selectbox:
            return seznam_strelcu_selectbox.index(stary_tip)
        return 0

    # 📊 ROZDĚLENÍ OBRAZOVKY: [ Levý sloupec: Kurzy (35%) ]  [ Pravý sloupec: Formulář (65%) ]
    c_kurzy, c_form = st.columns([3.5, 6.5])
    
    # -------------------------------------------------------------------------
    # LEVÝ SLOUPEC: DYNAMICKÁ TABULKA DIKTY TVÉMU OBRÁZKU
    # -------------------------------------------------------------------------
    with c_kurzy:
        st.markdown("<h4 style='color: #ff4b4b; margin-bottom: 5px;'>📊 Kurzy na vítěze MS</h4>", unsafe_allow_html=True)
        st.write("Aktuální pořadí favoritů podle sázkových kanceláří:")
        
        # Sestavíme přesná data z tvého screenshotu
        kurzy_data = [
            {"Pořadí": "1. 🇪🇸", "Tým": "Španělsko", "Kurz": 5.80},
            {"Pořadí": "2. 🇫🇷", "Tým": "Francie", "Kurz": 5.90},
            {"Pořadí": "3. EN", "Tým": "Anglie", "Kurz": 8.00},
            {"Pořadí": "4. 🇵🇹", "Tým": "Portugalsko", "Kurz": 8.00},
            {"Pořadí": "5. 🇦🇷", "Tým": "Argentina", "Kurz": 10.00},
            {"Pořadí": "6. 🇧🇷", "Tým": "Brazílie", "Kurz": 10.00},
            {"Pořadí": "7. 🇩🇪", "Tým": "Německo", "Kurz": 15.00},
            {"Pořadí": "8. 🇳🇱", "Tým": "Nizozemsko", "Kurz": 18.00},
            {"Pořadí": "9. 🇳🇴", "Tým": "Norsko", "Kurz": 33.00},
            {"Pořadí": "10. 🇧🇪", "Tým": "Belgie", "Kurz": 40.00},
        ]
        df_kurzy = pd.DataFrame(kurzy_data)
        
        # Vykreslíme jako čistou, orámovanou tabulku bez indexů
        st.dataframe(
            df_kurzy, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Kurz": st.column_config.NumberColumn("Kurz", format="%.2f"),
                "Pořadí": st.column_config.TextColumn("", width="small")
            }
        )

    # -------------------------------------------------------------------------
    # PRAVÝ SLOUPEC: FORMULÁŘ PRO TIPOVÁNÍ
    # -------------------------------------------------------------------------
    with c_form:
        stary_mistr = ct.get("mistr", "")
        semi_list = ct.get("semifinale", ["", "", "", ""])
        while len(semi_list) < 4: semi_list.append("")
            
        stary_cesko = ct.get("cesko", "Základní skupina")
        stary_mvp = ct.get("mvp", 0)
        stary_goly = ct.get("goly", 0)
        
        with st.form("dlouhodobe_tipy_form"):
            st.write("### Vyplň své celoturnajové tipy")
            
            # Vítěz přes roletku
            tip_mistr = st.selectbox("Celkový vítěz turnaje 🏆", options=seznam_tymu_selectbox, index=ziskej_index_tymu(stary_mistr), disabled=dlouhodobe_disabled)
            
            st.write("**4 semifinalisté (týmy, které postoupí do bojů o medaile) ⚽**")
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                semi1 = st.selectbox("Semifinalista 1", options=seznam_tymu_selectbox, index=ziskej_index_tymu(semi_list[0]), disabled=dlouhodobe_disabled)
                semi2 = st.selectbox("Semifinalista 2", options=seznam_tymu_selectbox, index=ziskej_index_tymu(semi_list[1]), disabled=dlouhodobe_disabled)
            with c_s2:
                semi3 = st.selectbox("Semifinalista 3", options=seznam_tymu_selectbox, index=ziskej_index_tymu(semi_list[2]), disabled=dlouhodobe_disabled)
                semi4 = st.selectbox("Semifinalista 4", options=seznam_tymu_selectbox, index=ziskej_index_tymu(semi_list[3]), disabled=dlouhodobe_disabled)
           
            # Fáze ČR
            faze_options = ["Základní skupina", "Šestnáctifinále (1/32)", "Osmifinále (1/16)", "Čtvrtfinále", "Semifinále", "O 3. místo 🥉", "FINÁLE 🏆"]
            if stary_cesko not in faze_options: stary_cesko = "Základní skupina"
            tip_cesko = st.selectbox("Kam až dojde český tým? 🇨🇿", options=faze_options, index=faze_options.index(stary_cesko), disabled=dlouhodobe_disabled)
            
            # 🔥 NOVINKA: MVP / Nejlepší střelec už je také přes roletku (Bezpečné proti překlepům)
            tip_mvp = st.number_input("Kolik bodů bude mít nejlepší hráč turnaje 🌟", min_value=0, value=int(stary_mvp), step=1, disabled=dlouhodobe_disabled)
            
            # Celkový počet gólů s opravenou fotbalovou ikonou ⚽🥅
            tip_goly = st.number_input("Celkový počet gólů v celém turnaji ⚽🥅", min_value=0, value=int(stary_goly), step=1, disabled=dlouhodobe_disabled)
            
            uloz_dl_button = st.form_submit_button("Uložit celoturnajové tipy 💾")
            
        if uloz_dl_button:
            # Kontrola vyplnění všech polí
            if tip_mistr == "-- Vyber tým --" or "-- Vyber tým --" in [semi1, semi2, semi3, semi4] or tip_mvp == "-- Vyber hráče --":
                st.error("❌ Chyba: Musíš řádně zvolit Vítěze, všechny 4 Semifinalisty i Nejlepšího hráče z nabídky!")
            else:
                with st.spinner("Odesílám tvé celoturnajové tipy do Google tabulky..."):
                    payload = {
                        "action": "uloz_celkove_tipy",
                        "hrac": current_user,
                        "mistr": tip_mistr,
                        "semifinale": [semi1, semi2, semi3, semi4],
                        "cesko": tip_cesko,
                        "mvp": tip_mvp,
                        "goly": int(tip_goly)
                    }
                    
                    URL_API = "https://script.google.com/macros/s/AKfycbypVyn-7dy9KRAvlTmRkZ7R9d66Ux9LraaSDeC0A8m0C1LGvcRmuq2lh-jlPSgbL9y1/exec"
                    
                    try:
                        res = requests.post(URL_API, json=payload, timeout=15)
                        if res.status_code == 200 and res.json().get("success"):
                            st.success("🎉 Tvoje celoturnajové tipy byly bezpečně uloženy do listu 'turnaj'!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Chyba při ukládání dlouhodobých tipů.")
                    except Exception as e:
                        st.error(f"Spojení selhalo: {e}")
                        
        if je_zamknuto_spravcem and current_user != "admin":
            st.error("🔒 Dlouhodobé tipy byly uzamčeny správcem, hodnoty již nelze upravovat.")

elif volba == "Správa API a zápasů ⚙️" and current_user == "admin":
    st.title("⚙️ Administrace: Import zápasů z Football-Data.org")
    st.write("Tlačítko níže stáhne všech 104 zápasů turnaje 2026 a odešle je přes Google Apps Script do tvé tabulky.")

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
                            raw_group = m.get("group")
                            skupina = raw_group.replace("GROUP_", "") if raw_group else ""
                            raw_date = m.get("utcDate", "")
                            hezky_datum = raw_date.replace("T", " ")[:16] if raw_date else ""
                            api_status = m.get("status")
                            nas_status = "FINISHED" if api_status == "FINISHED" else "NS"
                            
                            # 🔥 ROZŠÍŘENÍ IMPORTÉRU: Zde zakládáme prázdné nové sloupce, aby ti je import nepřemazal!
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
                                "goly_d": m.get("score", {}).get("fullTime", {}).get("home") if m.get("score", {}).get("fullTime", {}).get("home") is not None else "",
                                "goly_h": m.get("score", {}).get("fullTime", {}).get("away") if m.get("score", {}).get("fullTime", {}).get("away") is not None else "",
                                "status": str(nas_status),
                                "halftime_d": "",
                                "halftime_h": "",
                                "duration": "REGULAR",
                                "extratime_d": "",
                                "extratime_h": "",
                                "penalties_d": "",
                                "penalties_h": ""
                            }
                            nove_zapasy_list.append(novy_zapas)
                        
                        st.write("### 📋 Náhled dat odesílaných do Google tabulky:")
                        st.dataframe(pd.DataFrame(nove_zapasy_list).head(5))
                        
                        st.write("🔄 Posílám data přes Apps Script...")
                        payload = {"action": "uloz_zapasy", "data": nove_zapasy_list}
                        script_res = requests.post(URL_API, json=payload, timeout=15)
                        
                        if script_res.status_code == 200:
                            st.success(f"🔥 Všech {len(nove_zapasy_list)} zápasů bylo úspěšně uloženo do Google Sheets!")
                            st.cache_data.clear()
                        else:
                            st.error(f"Chyba Google Scriptu (Status {script_res.status_code}): {script_res.text}")
                else:
                    st.error(f"Chyba API: {data_api.get('message')}")
            except Exception as e:
                st.error(f"Chyba při komunikaci nebo zápisu: {e}")
