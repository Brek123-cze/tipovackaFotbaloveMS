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

import re

def spocitej_kanadske_bodovani(zapasy_list):
    """Projede všechny zápasy, naparsuje střelce/asistence, přiřadí jim národnost a vrátí DataFrame."""
    # Slovník se strukturou: { jmeno: {"G": 0, "A": 0, "tym": "Název týmu"} }
    statistiky = {}
    
    for zapas in zapasy_list:
        tym_domaci = PREKLAD_TYMU.get(zapas.get("domaci"), zapas.get("domaci"))
        tym_hoste = PREKLAD_TYMU.get(zapas.get("hoste"), zapas.get("hoste"))
        
        # Připravíme si dvojice: (textové pole, název týmu)
        zdroje_dat = []
        if zapas.get("strelci_d") and not pd.isna(zapas["strelci_d"]):
            zdroje_dat.append((str(zapas["strelci_d"]).split("\n"), tym_domaci))
        if zapas.get("strelci_h") and not pd.isna(zapas["strelci_h"]):
            zdroje_dat.append((str(zapas["strelci_h"]).split("\n"), tym_hoste))
            
        for radky, aktualni_tym in zdroje_dat:
            for radek in radky:
                radek = radek.strip()
                if not radek:
                    continue
                    
                # Odstraníme minutu na začátku (např. 12' nebo 45+2')
                radek_bez_minuty = re.sub(r"^\d+\+?\d*'\s*", "", radek).strip()
                if not radek_bez_minuty:
                    continue
                    
                # Najdeme asistenci v závorce -> např. "Malík (as. Ševčík)"
                match = re.match(r"([^(]+)\s*(?:\(as\.\s*([^)]+)\))?", radek_bez_minuty)
                
                if match:
                    strelce = match.group(1).strip()
                    asistent = match.group(2).strip() if match.group(2) else None
                    
                    # Zanesení střelce (Gól +1)
                    if strelce:
                        if strelce not in statistiky:
                            statistiky[strelce] = {"G": 0, "A": 0, "tym": aktualni_tym}
                        statistiky[strelce]["G"] += 1
                        
                    # Zanesení asistenta (Asistence +1)
                    if asistent:
                        if asistent not in statistiky:
                            statistiky[asistent] = {"G": 0, "A": 0, "tym": aktualni_tym}
                        statistiky[asistent]["A"] += 1

    # Převod na DataFrame
    if not statistiky:
        return pd.DataFrame(columns=["Hráč", "Tým", "Góly", "Asistence", "Body"])
        
    data_pro_df = []
    for hrac, info in statistiky.items():
        celkem_bodu = info["G"] + info["A"]
        data_pro_df.append({
            "Hráč": hrac,
            "Tým": info["tym"],
            "Góly": info["G"],
            "Asistence": info["A"],
            "Body": celkem_bodu
        })
        
    df_vysledny = pd.DataFrame(data_pro_df)
    # Seřadíme podle bodů, následně podle gólů
    df_vysledny = df_vysledny.sort_values(by=["Body", "Góly"], ascending=False).reset_index(drop=True)
    return df_vysledny


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
    volba = st.sidebar.radio("Navigace:", ["Žebříček hráčů 🏆", "Moje tipy 📝", "Celoturnajové tipy 🔮", "Tipy ostatních 👀", "Správa API a zápasů ⚙️"])
else:
    volba = st.sidebar.radio("Navigace:", ["Žebříček hráčů 🏆", "Moje tipy 📝", "Celoturnajové tipy 🔮", "Tipy ostatních 👀"])

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
        
    # Bezpečný převod na string, ošetření proti None a následný strip a lower
    stary_mvp_surovy = ct.get("mvp", "")
    if pd.isna(stary_mvp_surovy) or stary_mvp_surovy is None:
        stary_mvp_surovy = ""

    tip_mvp = str(stary_mvp_surovy).strip().lower()
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
    if z.get("status") != "FINISHED" or pd.isna(z.get("goly_d")) or str(z.get("goly_d")) == "":
        return ""
    
    tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
    tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
    
    # Bezpečný převod hlavních gólů
    gd = int(float(z["goly_d"]))
    gh = int(float(z["goly_h"]))
    
    # 1. POLOČAS (První závorka za skóre)
    polocas = ""
    hd = z.get("halftime_d")
    hh = z.get("halftime_h")
    if hd is not None and hh is not None and str(hd) != "" and str(hh) != "":
        try:
            polocas = f" ({int(float(hd))}:{int(float(hh))})"
        except:
            polocas = ""
            
    # Základní řetězec výsledku
    zakladni_cast = f"<b>{tým_d_cz}</b> {gd}:{gh}{polocas} <b>{tým_h_cz}</b>"
    
    # 2. PRODLOUŽENÍ A PENALTY (Dodatek na konec pro play-off)
    dodatky = []
    
    # Kontrola prodloužení (pokud duration není REGULAR a jsou vyplněné góly v prodloužení)
    duration = str(z.get("duration", "REGULAR")).upper()
    ed = z.get("extratime_d")
    eh = z.get("extratime_h")
    
    if duration in ["EXTRA_TIME", "PENALTY_SHOOTOUT"] and ed is not None and eh is not None and str(ed) != "" and str(eh) != "":
        try:
            dodatky.append(f"pr {int(float(ed))}:{int(float(eh))}")
        except:
            pass
            
    # Kontrola penaltového rozstřelu
    pd_d = z.get("penalties_d")
    pn_h = z.get("penalties_h")
    if duration == "PENALTY_SHOOTOUT" and pd_d is not None and pn_h is not None and str(pd_d) != "" and str(pn_h) != "":
        try:
            dodatky.append(f"pn {int(float(pd_d))}:{int(float(pn_h))}")
        except:
            pass
            
    # Pokud existuje nějaký dodatek pro play-off, zabalíme ho do závorky na úplný konec
    if dodatky:
        zakladni_cast += f" ({', '.join(dodatky)})"
        
    return f"<div style='font-size: 0.95rem; line-height: 1.4; padding: 4px 0;'>⚽ {zakladni_cast}</div>"


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

        st.write("---")
        st.subheader("🏆 Nejužitečnější hráč mistrovství (Kanadské bodování)")
        
        # Vygenerujeme statistiky z aktuálních dat o zápasech
        df_bodovani = spocitej_kanadske_bodovani(data.get("zapasy", []))
        if not df_bodovani.empty:
            # 📦 EXPANDER 1: Schováme podrobnou tabulku do rozbalovacího expanderu
            with st.expander("📊 Zobrazit kompletní pořadí produktivity (G+A)"):
                st.dataframe(
                    df_bodovani,
                    column_config={
                        "Hráč": st.column_config.TextColumn("Jméno hráče"),
                        "Tým": st.column_config.TextColumn("🌍 Tým"),
                        "Góly": st.column_config.NumberColumn("⚽ Góly", format="%d"),
                        "Asistence": st.column_config.NumberColumn("👟 Asistence", format="%d"),
                        "Body": st.column_config.NumberColumn("🔥 Body (G+A)", format="%d"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
            # 2. Informativní věta o nejlepším hráči zůstává viditelná venku pod expanderem
            top_hrac = df_bodovani.iloc[0]
            st.info(f"👑 **Nejužitečnějším hráčem** je aktuálně **{top_hrac['Hráč']} ({top_hrac['Tým']})** s bilancí {top_hrac['Body']} bodů ({top_hrac['Góly']}+{top_hrac['Asistence']}).")
        else:
            st.info("Zatím nebyly zadány žádné góly ani asistence.")

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
                            
                            # --- ZOBRAZENÍ STŘELCŮ ---
                            akt_strelci_d = z.get("strelci_d", "")
                            akt_strelci_h = z.get("strelci_h", "")
                            if (akt_strelci_d and not pd.isna(akt_strelci_d)) or (akt_strelci_h and not pd.isna(akt_strelci_h)):
                                text_d = str(akt_strelci_d).replace("\n", ", ") if akt_strelci_d else "—"
                                text_h = str(akt_strelci_h).replace("\n", ", ") if akt_strelci_h else "—"
                                st.caption(f"⚽ **Střelci:** {text_d} | {text_h}")
                            # -------------------------
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
                            
                            # --- ZOBRAZENÍ STŘELCŮ ---
                            akt_strelci_d = z.get("strelci_d", "")
                            akt_strelci_h = z.get("strelci_h", "")
                            if (akt_strelci_d and not pd.isna(akt_strelci_d)) or (akt_strelci_h and not pd.isna(akt_strelci_h)):
                                text_d = str(akt_strelci_d).replace("\n", ", ") if akt_strelci_d else "—"
                                text_h = str(akt_strelci_h).replace("\n", ", ") if akt_strelci_h else "—"
                                st.caption(f"⚽ **Střelci:** {text_d} | {text_h}")
                            # -------------------------
                        else:
                            cas = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
                            tým_d = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
                            tým_h = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
                            st.markdown(f"<div style='color: #777; padding: 4px 0;'>🕒 {cas} | {tým_d} vs {tým_h} <i>(nedohráno)</i></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)



        # 📦 EXPANDER 2: DETAILNÍ BODOVÁNÍ TIPÉRU (ZÁPAS PO ZÁPASE)
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
                stary_mvp_surovy = ct.get("mvp", "")
                if pd.isna(stary_mvp_surovy) or stary_mvp_surovy is None:
                    stary_mvp_surovy = ""
                tip_mvp = str(stary_mvp_surovy).strip().lower()
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

    vsechny_tipy_list = data.get("tipy", [])
    mapa_tipu = {}
    for t in vsechny_tipy_list:
        mapa_tipu[(str(t.get("hrac", "")), str(t.get("zapas_id", "")))] = t
    
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

            # 🚨 OPRAVA: Bezpečné načtení výchozích hodnot z načtených dat ('mapa_tipu') pro konkrétního uživatele
            stary_tip = mapa_tipu.get((str(current_user), str(zapas_id)), {})
            val_d = stary_tip.get("tip_d", 0)
            val_h = stary_tip.get("tip_h", 0)
            val_zol = bool(stary_tip.get("zolik", False))

            # Převod na int, pokud se z tabulky načetl float/text
            try: val_d = int(float(val_d))
            except: val_d = 0
            try: val_h = int(float(val_h))
            except: val_h = 0

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
                    # 🚨 OPRAVA: Přidán unikátní klíč pro domácí obsahující 'current_user'
                    tip_d_vstup = st.number_input("D", min_value=0, max_value=20, value=val_d, step=1, key=f"num_d_{zapas_id}_{current_user}", label_visibility="collapsed")
                with c_sep:
                    st.markdown("<div style='text-align: center; font-weight: bold; padding-top: 6px; color: #888;'>vs</div>", unsafe_allow_html=True)
                with c_in_h:
                    # 🚨 OPRAVA: Přidán unikátní klíč pro hosty obsahující 'current_user'
                    tip_h_vstup = st.number_input("H", min_value=0, max_value=20, value=val_h, step=1, key=f"num_h_{zapas_id}_{current_user}", label_visibility="collapsed")
                with c_ch_z:
                    # 🚨 OPRAVA: Přidán unikátní klíč pro žolíka obsahující 'current_user'
                    zolik_vstup = st.checkbox("🃏", value=val_zol, key=f"ch_z_{zapas_id}_{current_user}", label_visibility="collapsed")
            
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        _, c_btn_m, _ = st.columns([1.5, 2, 1.5])
        
        with c_btn_m:
            if st.button("💾 Uložit všechny tipy pro tento den", key=f"save_all_day_tips_{current_user}", use_container_width=True):
                # Načtení hodnot z opravených dynamických klíčů
                vybrani_zolici = [st.session_state[f"ch_z_{z['id']}_{current_user}"] for _, z in zapasy_dne.iterrows()]
                
                if sum(vybrani_zolici) > 1:
                    st.error("❌ Chyba: Můžeš si vybrat pouze jednoho Žolíka na jeden hrací den!")
                else:
                    with st.spinner("Odesílám balíček dat do Google tabulky..."):
                        seznam_tipu_k_odeslani = []
                        for _, z in zapasy_dne.iterrows():
                            z_id = int(z["id"])
                            seznam_tipu_k_odeslani.append({
                                "zapas_id": z_id,
                                "tip_d": int(st.session_state[f"num_d_{z_id}_{current_user}"]),
                                "tip_h": int(st.session_state[f"num_h_{z_id}_{current_user}"]),
                                "zolik": bool(st.session_state[f"ch_z_{z_id}_{current_user}"])
                            })
                        
                        URL_API = "https://script.google.com/macros/s/AKfycbypVyn-7dy9KRAvlTmRkZ7R9d66Ux9LraaSDeC0A8m0C1LGvcRmuq2lh-jlPSgbL9y1/exec"
                        payload = {"action": "uloz_vsechny_tipy", "hrac": current_user, "tipy": seznam_tipu_k_odeslani}
                        
                        try:
                            res = requests.post(URL_API, json=payload, timeout=15)
                            if res.status_code == 200 and res.json().get("success"):
                                st.success("🎉 Tipy uloženy do Google Sheets!")
                                st.cache_data.clear()  # Vyčištění cache pro okamžitou aktualizaci
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
    
    # Bezpečné načtení dat o zamknutí
    je_zamknuto_spravcem = bool(data.get("admin", {}).get("dlouhodobe_zamknuto", False))
    dlouhodobe_disabled = False if current_user == "admin" else je_zamknuto_spravcem
        
    # Bezpečné vytažení tipů pro aktuálního uživatele
    ct = data.get("celkove_tipy", {}).get(current_user, {})
    if not isinstance(ct, dict):
        ct = {}
    
    # Pomocné funkce pro bezpečné zjištění indexu starých hodnot v roletkách
    def ziskej_index_tymu(stary_tip):
        if stary_tip in seznam_tymu_selectbox:
            return seznam_tymu_selectbox.index(stary_tip)
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
            {"Pořadí": "3. GB", "Tým": "Anglie", "Kurz": 8.00},
            {"Pořadí": "4. 🇵🇹", "Tým": "Portugalsko", "Kurz": 8.00},
            {"Pořadí": "5. 🇦🇷", "Tým": "Argentina", "Kurz": 10.00},
            {"Pořadí": "6. 🇧🇷", "Tým": "Brazílie", "Kurz": 10.00},
            {"Pořadí": "7. 🇩🇪", "Tým": "Německo", "Kurz": 15.00},
            {"Pořadí": "8. 🇳🇱", "Tým": "Nizozemsko", "Kurz": 18.00},
            {"Pořadí": "9. 🇳🇴", "Tým": "Norsko", "Kurz": 33.00},
            {"Pořadí": "10. 🇧🇪", "Tým": "Belgie", "Kurz": 40.00},
            {"Pořadí": "11. 🇨🇴", "Tým": "Kolumbie", "Kurz": 40.00},
            {"Pořadí": "... 🇨🇿", "Tým": "Česko", "Kurz": 250.00},
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
        
        # Bezpečné načtení listu semifinalistů
        semi_list = ct.get("semifinale", ["", "", "", ""])
        if not isinstance(semi_list, list):
            semi_list = ["", "", "", ""]
        while len(semi_list) < 4: 
            semi_list.append("")
            
        stary_cesko = ct.get("cesko", "Základní skupina")
        
        # Ošetření typů pro číselné vstupy z tabulky
        try:
            stary_mvp = int(ct.get("mvp", 0))
        except (ValueError, TypeError):
            stary_mvp = 0
            
        try:
            stary_goly = int(ct.get("goly", 0))
        except (ValueError, TypeError):
            stary_goly = 0
        
        st.write("### Vyplň své celoturnajové tipy")
        
        # 1. Výběr celkového vítěze (přidán unikátní klíč)
        tip_mistr = st.selectbox(
            "Celkový vítěz turnaje 🏆", 
            options=seznam_tymu_selectbox, 
            index=ziskej_index_tymu(stary_mistr), 
            disabled=dlouhodobe_disabled,
            key=f"ct_mistr_{current_user}"
        )
        
        # --- 🔮 LOGIKA AUTODOPLNĚNÍ VÍTĚZE DO SEMIFINÁLE ---
        # Pokud je zvolen reálný tým jako vítěz, ale není v načteném seznamu semifinalistů, automaticky ho dosadíme do semi1
        semi1_default = semi_list[0]
        if tip_mistr != "-- Vyber tým --" and tip_mistr not in semi_list:
            semi1_default = tip_mistr

        # Přepočítání aktuálních indexů pro roletky semifinalistů
        idx_s1 = ziskej_index_tymu(semi1_default)
        idx_s2 = ziskej_index_tymu(semi_list[1])
        idx_s3 = ziskej_index_tymu(semi_list[2])
        idx_s4 = ziskej_index_tymu(semi_list[3])
        
        st.write("**4 semifinalisté (týmy, které postoupí do bojů o medaile) ⚽**")
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            semi1 = st.selectbox("Semifinalista 1", options=seznam_tymu_selectbox, index=idx_s1, disabled=dlouhodobe_disabled, key=f"ct_s1_{current_user}")
            semi2 = st.selectbox("Semifinalista 2", options=seznam_tymu_selectbox, index=idx_s2, disabled=dlouhodobe_disabled, key=f"ct_s2_{current_user}")
        with c_s2:
            semi3 = st.selectbox("Semifinalista 3", options=seznam_tymu_selectbox, index=idx_s3, disabled=dlouhodobe_disabled, key=f"ct_s3_{current_user}")
            semi4 = st.selectbox("Semifinalista 4", options=seznam_tymu_selectbox, index=idx_s4, disabled=dlouhodobe_disabled, key=f"ct_s4_{current_user}")
       
        # Fáze ČR
        faze_options = ["Základní skupina", "Šestnáctifinále (1/32)", "Osmifinále (1/16)", "Čtvrtfinále", "Semifinále", "O 3. místo 🥉", "FINÁLE 🏆"]
        if stary_cesko not in faze_options: 
            stary_cesko = "Základní skupina"
        tip_cesko = st.selectbox("Kam až dojde český tým?", options=faze_options, index=faze_options.index(stary_cesko), disabled=dlouhodobe_disabled, key=f"ct_cesko_{current_user}")
        
        # MVP jako číselný vstup
        tip_mvp = st.number_input("Kolik kanadských bodů bude mít nejlepší hráč turnaje 🌟 (góly + asistence)", min_value=0, value=stary_mvp, step=1, disabled=dlouhodobe_disabled, key=f"ct_mvp_{current_user}")
        
        # Celkový počet gólů
        tip_goly = st.number_input("Celkový počet gólů v celém turnaji ⚽🥅", min_value=0, value=stary_goly, step=1, disabled=dlouhodobe_disabled, key=f"ct_goly_{current_user}")
        
        # --- 🚨 KONTROLA DUPLICIT A KONTROLA MISTRA V SEMIFINÁLE ---
        vybrani_semifinaliste = [semi1, semi2, semi3, semi4]
        # Vyfiltrujeme výchozí prázdnou možnost, abychom nehlásili duplicitu u nevybraných polí
        skutecne_vybrani = [t for t in vybrani_semifinaliste if t != "-- Vyber tým --"]
        
        ma_duplicity = len(skutecne_vybrani) != len(set(skutecne_vybrani))
        mistr_chybi_v_semi = (tip_mistr != "-- Vyber tým --" and tip_mistr not in vybrani_semifinaliste)
        
        # Vykreslení tlačítek na základě validace (Streamlit formuláře vyžadují submit button přímo v bloku formuláře)
        if ma_duplicity:
            st.error("❌ Chyba: Nemůžeš vybrat jeden tým do semifinále vícekrát! Oprav duplicitu.")
            st.button("Uložit celoturnajové tipy 💾", disabled=True, key="btn_disabled_dup")
        elif mistr_chybi_v_semi:
            st.warning(f"⚠️ Tvůj celkový vítěz (**{tip_mistr}**) musí být zároveň vybrán jako jeden ze 4 semifinalistů!")
            st.button("Uložit celoturnajové tipy 💾", disabled=True, key="btn_disabled_mistr")
        else:
            # Pokud je vše validní, zobrazíme plně funkční tlačítko
            uloz_dl_button = st.button("Uložit celoturnajové tipy 💾", key=f"btn_save_{current_user}")
            
            if uloz_dl_button:
                if tip_mistr == "-- Vyber tým --" or "-- Vyber tým --" in vybrani_semifinaliste:
                    st.error("❌ Chyba: Musíš řádně zvolit Vítěze a všechny 4 Semifinalisty z nabídky!")
                else:
                    with st.spinner("Odesílám tvé celoturnajové tipy do Google tabulky..."):
                        payload = {
                            "action": "uloz_celkove_tipy",
                            "hrac": current_user,
                            "mistr": tip_mistr,
                            "semifinale": vybrani_semifinaliste,
                            "cesko": tip_cesko,
                            "mvp": int(tip_mvp),
                            "goly": int(tip_goly)
                        }
                        
                        URL_API = "https://script.google.com/macros/s/AKfycbypVyn-7dy9KRAvlTmRkZ7R9d66Ux9LraaSDeC0A8m0C1LGvcRmuq2lh-jlPSgbL9y1/exec"
                        
                        try:
                            res = requests.post(URL_API, json=payload, timeout=15)
                            if res.status_code == 200 and res.json().get("success"):
                                st.success("🎉 Tvoje celoturnajové tipy byly bezpečně uloženy do listu 'turnaj'!")
                                # 🚨 NATVRDO VYMAŽE CACHE, ABY OSTATNÍ IHNED VIDĚLI NOVÁ DATA
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Chyba při ukládání dlouhodobých tipů. Google Script nevrátil 'success'.")
                        except Exception as e:
                            st.error(f"Spojení selhalo: {e}")
                            
        if je_zamknuto_spravcem and current_user != "admin":
            st.error("🔒 Dlouhodobé tipy byly uzamčeny správcem, hodnoty již nelze upravovat.")

# --- 4. ZÁLOŽKA: TIPY OSTATNÍCH ---
elif volba == "Tipy ostatních 👀":
    c_l, c_main, c_r = st.columns([0.5, 9, 0.5])
    with c_main:
        st.title("👀 Co tipovali soupeři?")
        kat = st.radio("Vyber kategorii:", ["Denní zápasy", "Celoturnajové tipy"], horizontal=True)
        
        # 🛠️ PŘÍPRAVA DAT PRO FOTBALOVOU STRUKTURU
        seznam_zapasu = data.get("zapasy", [])
        vsechny_tipy_list = data.get("tipy", [])
        
        # Získání seznamu všech unikátních hráčů v systému (vyjma admina)
        vsechni_hraci = sorted(list(set([t["hrac"] for t in vsechny_tipy_list if t["hrac"] != "admin"])))
        if not vsechni_hraci:
            vsechni_hraci = [current_user]
            
        # Převedeme seznam denních tipů do rychlého vyhledávacího slovníku
        mapa_tipu = {}
        for t in vsechny_tipy_list:
            mapa_tipu[(str(t["hrac"]), str(t["zapas_id"]))] = t

        if kat == "Denní zápasy":
            # --- 🛠️ PŘEVZETÍ ROBUSTNÍ LOGIKY PRO HRAČÍ DNY ZÁPASŮ ---
            if not data or "zapasy" not in data or len(data["zapasy"]) == 0:
                st.error("❌ Nepodařilo se načíst data o zápasech z Google tabulky.")
                st.stop()

            # Vytvoříme DataFrame, abychom mohli využít indexaci a datetime operace
            df_zapasy = pd.DataFrame(data["zapasy"])

            hraci_dny_list = []
            ceske_casy_list = []
            for idx, row in df_zapasy.iterrows():
                try:
                    # Zpracování ISO formátu 2026-06-11T17:00:00.000Z
                    gmt_dt = pd.to_datetime(row["datum"])
                    cz_dt = gmt_dt + pd.Timedelta(hours=4)  
                    ceske_casy_list.append(cz_dt.strftime("%Y-%m-%d %H:%M"))
                    
                    # Logika virtuálního dne (zápasy po půlnoci patří k předchozímu dni)
                    virtual_dt = cz_dt - pd.Timedelta(hours=12)
                    hraci_den = virtual_dt.strftime("%Y-%m-%d")
                except:
                    ceske_casy_list.append(row["datum"])
                    hraci_den = "Neznámé datum"
                hraci_dny_list.append(hraci_den)
            
            df_zapasy["hraci_den"] = hraci_dny_list
            df_zapasy["cesky_cas"] = ceske_casy_list

            unikatni_dny = sorted(list(df_zapasy["hraci_den"].unique()))
            if "Neznámé datum" in unikatni_dny: 
                unikatni_dny.remove("Neznámé datum")

            # Pomocná funkce pro lidské formátování dne v roletce (např. Čt 11.06.2026)
            def zformatuj_den(den_str):
                try:
                    d = pd.to_datetime(den_str)
                    dny_tydne = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
                    return f"{dny_tydne[d.weekday()]} {d.strftime('%d.%m.%Y')}"
                except: 
                    return den_str

            # Nastavení výchozího dne na dnešek
            dnesni_datum_str = time.strftime("%Y-%m-%d")
            index_vychozi = 0
            if dnesni_datum_str in unikatni_dny:
                index_vychozi = unikatni_dny.index(dnesni_datum_str)

            # 📅 Výběr hracího dne shodný s "Moje tipy"
            vybrany_den_raw = st.selectbox("📅 Vyber hrací den:", unikatni_dny, index=index_vychozi, format_func=zformatuj_den)
            
            # Vyfiltrování všech zápasů pro daný den
            zapasy_filtrovane = df_zapasy[df_zapasy["hraci_den"] == vybrany_den_raw].sort_values(by="datum")

            if not zapasy_filtrovane.empty:
                radky_matice = []
                import datetime as dt_lib
                aktualni_cas = dt_lib.datetime.utcnow() + dt_lib.timedelta(hours=2)
                
                for idx, z in zapasy_filtrovane.iterrows():
                    z_id = str(z["id"])
                    
                    # Kontrola ukončení zápasu
                    zapas_finished = str(z.get("status", "")).upper() == "FINISHED"
                    zapas_zahajen_casove = False
                    
                    # 🕒 Časová kontrola odtajnění tipů (porovnáváme reálný čas výkopu v ČR)
                    try:
                        # V 'cesky_cas' máme formát "%Y-%m-%d %H:%M"
                        obj_zapasu = dt_lib.datetime.strptime(z["cesky_cas"], "%Y-%m-%d %H:%M")
                        zapas_zahajen_casove = aktualni_cas >= obj_zapasu
                    except:
                        zapas_zahajen_casove = False
                        
                    odtajneno = bool(zapas_zahajen_casove or zapas_finished)
                    
                    # Získání samotného času pro výpis (např. "17:00")
                    pouze_cas = z["cesky_cas"].split(" ")[1] if " " in z["cesky_cas"] else z["cesky_cas"]
                    
                    # Sestavení textu zápasu do prvního sloupce
                    # 🇨🇿 PŘEKLAD TÝMŮ DO ČEŠTINY
                    tym_d_cz = PREKLAD_TYMU.get(z.get("domaci"), z.get("domaci", "Neznámý"))
                    tym_h_cz = PREKLAD_TYMU.get(z.get("hoste"), z.get("hoste", "Neznámý"))

                    # Sestavení prvního sloupce s českými názvy týmů
                    info_o_zapasu = f"⏱️ {pouze_cas} | {tym_d_cz} - {tym_h_cz}"
                    
                    # Pokud je zápas odehraný nebo jsou zadány góly, ukážeme výsledek přímo v záhlaví řádku
                    if zapas_finished or (z.get("goly_d") is not None and str(z.get("goly_d")) != ""):
                        try:
                            gd = int(float(z["goly_d"]))
                            gh = int(float(z["goly_h"]))
                            info_o_zapasu += f"  (🏁 {gd}:{gh})"
                        except:
                            pass
                    
                    radek = {"Zápas": info_o_zapasu}
                    
                    # Projdeme všechny soupeře a dosadíme jejich tipy
                    for hrac in vsechni_hraci:
                        stary_tip = mapa_tipu.get((str(hrac), z_id), {})
                        
                        t_d = stary_tip.get("tip_d")
                        t_h = stary_tip.get("tip_h")
                        ma_zolika = bool(stary_tip.get("zolik", False))
                        
                        ma_realny_tip = (t_d is not None and t_h is not None and str(t_d) != "" and str(t_d) != "-")
                        
                        if hrac == current_user:
                            text_tipu = f"{int(float(t_d))}:{int(float(t_h))}" if ma_realny_tip else "-:-"
                        else:
                            if odtajneno:
                                text_tipu = f"{int(float(t_d))}:{int(float(t_h))}" if ma_realny_tip else "-:-"
                            else:
                                if ma_realny_tip:
                                    text_tipu = "❓:❓"  # Skryté skóre před výkopem
                                else:
                                    text_tipu = "-:-"  # Ještě nevsadil
                                    
                        if ma_zolika and (odtajneno or hrac == current_user or ma_realny_tip):
                            text_tipu += " 🔥"
                            
                        radek[hrac] = text_tipu
                        
                    radky_matice.append(radek)
                    
                df_denni_prehled = pd.DataFrame(radky_matice)
                
                st.write(f"### 📊 Přehled tipů pro den: **{zformatuj_den(vybrany_den_raw)}**")
                st.dataframe(df_denni_prehled, use_container_width=True, hide_index=True)
            else:
                st.info("🌴 Pro tento den nejsou naplánovány žádné zápasy.")
                
        else:
            st.write("### 📊 Kompletní tabulka dlouhodobých celoturnajových tipů")    
            
            kategorie = [
                "Celkový vítěz 🏆", 
                "Semifinalista 1 ⚽", 
                "Semifinalista 2 ⚽", 
                "Semifinalista 3 ⚽", 
                "Semifinalista 4 ⚽", 
                "Konečná fáze ČR 🇨🇿", 
                "Body nejlepšího hráče (MVP) 🌟", 
                "Celkový počet gólů 🥅"
            ]
            
            tabulka_data = {}
            celkove_tipy_dict = data.get("celkove_tipy", {})
            
            for hrac in vsechni_hraci:
                ct = celkove_tipy_dict.get(hrac, {})
                s_list = ct.get("semifinale", ["-", "-", "-", "-"])
                if not isinstance(s_list, list):
                    s_list = ["-", "-", "-", "-"]
                while len(s_list) < 4: 
                    s_list.append("-")
                
                mistr = ct.get("mistr", "-")
                cesko = ct.get("cesko", "-")
                
                try:
                    mvp = int(float(ct.get("mvp", 0))) if ct.get("mvp") else "-"
                except:
                    mvp = ct.get("mvp", "-")
                    
                try:
                    goly = int(float(ct.get("goly", 0))) if ct.get("goly") else "-"
                except:
                    goly = ct.get("goly", "-")
                
                hrac_sloupec = [
                    str(mistr if mistr else "-"),
                    str(s_list[0] if s_list[0] else "-"),
                    str(s_list[1] if s_list[1] else "-"),
                    str(s_list[2] if s_list[2] else "-"),
                    str(s_list[3] if s_list[3] else "-"),
                    str(cesko if cesko else "-"),
                    str(mvp),
                    str(goly)
                ]
                tabulka_data[hrac] = hrac_sloupec
                
            df_dlouhodobe = pd.DataFrame(tabulka_data, index=kategorie)
            st.dataframe(df_dlouhodobe, use_container_width=True)
            
            if data.get("nastaveni", {}).get("dlouhodobe_zamknuto", False):
                st.caption("🔒 Dlouhodobé celoturnajové tipy byly správcem kompletně uzamčeny.")

elif volba == "Správa API a zápasů ⚙️" and current_user == "admin":
    st.title("⚙️ Administrace: Aktualizace výsledků z API")
    st.write("Tlačítko níže stáhne data z Football-Data.org, vybere pouze zápasy z aktuálního dne a aktualizuje jejich stav a skóre v Google tabulce.")

    URL_API = "https://script.google.com/macros/s/AKfycbypVyn-7dy9KRAvlTmRkZ7R9d66Ux9LraaSDeC0A8m0C1LGvcRmuq2lh-jlPSgbL9y1/exec"
    NEW_API_KEY = "24c6237d44e349179857f3ec7e229d00"
    NEW_BASE_URL = "https://api.football-data.org/v4"
    new_headers = { "X-Auth-Token": NEW_API_KEY }

    # Volba rozsahu aktualizace pro větší flexibilitu
    rozsah = st.radio("Rozsah aktualizace:", ["Pouze dnešní zápasy", "Zápasy za poslední 3 dny (vč. dneška)"], horizontal=True)

    if st.button("🔄 Spustit chytrou aktualizaci výsledků"):
        with st.spinner("Stahuji data z API a filtruji zápasy..."):
            url = f"{NEW_BASE_URL}/competitions/WC/matches"
            try:
                res = requests.get(url, headers=new_headers, timeout=10)
                data_api = res.json()
                
                if res.status_code == 200:
                    matches = data_api.get("matches", [])
                    if not matches:
                        st.warning("API nevrátilo žádné zápasy.")
                    else:
                        import datetime as dt_lib
                        # Aktuální čas v ČR (UTC+2)
                        aktualni_cas = dt_lib.datetime.utcnow() + dt_lib.timedelta(hours=2)
                        
                        # Příprava seznamu povolených datumů pro filtraci (formát YYYY-MM-DD)
                        povolene_dny = [aktualni_cas.strftime("%Y-%m-%d")]
                        if rozsah == "Zápasy za poslední 3 dny (vč. dneška)":
                            povolene_dny.append((aktualni_cas - dt_lib.timedelta(days=1)).strftime("%Y-%m-%d"))
                            povolene_dny.append((aktualni_cas - dt_lib.timedelta(days=2)).strftime("%Y-%m-%d"))

                        filtrovane_zapasy_list = []
                        
                        for idx, m in enumerate(matches):
                            raw_date = m.get("utcDate", "") # Formát z API: "2026-06-14T18:00:00Z"
                            if not raw_date:
                                continue
                                
                            den_zapasu = raw_date.split("T")[0] # Dostaneme čisté "2026-06-14"
                            
                            # 🎯 FILTR: Do tabulky pustíme jen zápasy, které odpovídají zvolenému rozsahu dnů
                            if den_zapasu in povolene_dny:
                                raw_group = m.get("group")
                                skupina = raw_group.replace("GROUP_", "") if raw_group else ""
                                hezky_datum = raw_date.replace("T", " ")[:16]
                                api_status = m.get("status")
                                nas_status = "FINISHED" if api_status == "FINISHED" else "NS"
                                
                                # Extrakce rozšířených statistik z API (poločas, prodloužení, penalty)
                                score_obj = m.get("score", {})
                                
                                novy_zapas = {
                                    "api_id": int(m.get("id")),
                                    "datum": str(hezky_datum),
                                    "faze": str(m.get("stage")),
                                    "skupina": str(skupina),
                                    "domaci": str(m.get("homeTeam", {}).get("name", "TBD")),
                                    "hoste": str(m.get("awayTeam", {}).get("name", "TBD")),
                                    "vlajka_d": str(m.get("homeTeam", {}).get("crest", "")),
                                    "vlajka_h": str(m.get("awayTeam", {}).get("crest", "")),
                                    "goly_d": score_obj.get("fullTime", {}).get("home") if score_obj.get("fullTime", {}).get("home") is not None else "",
                                    "goly_h": score_obj.get("fullTime", {}).get("away") if score_obj.get("fullTime", {}).get("away") is not None else "",
                                    "status": str(nas_status),
                                    "halftime_d": score_obj.get("halfTime", {}).get("home") if score_obj.get("halfTime", {}).get("home") is not None else "",
                                    "halftime_h": score_obj.get("halfTime", {}).get("away") if score_obj.get("halfTime", {}).get("away") is not None else "",
                                    "duration": str(score_obj.get("duration", "REGULAR")),
                                    "extratime_d": score_obj.get("extraTime", {}).get("home") if score_obj.get("extraTime", {}).get("home") is not None else "",
                                    "extratime_h": score_obj.get("extraTime", {}).get("away") if score_obj.get("extraTime", {}).get("away") is not None else "",
                                    "penalties_d": score_obj.get("penalties", {}).get("home") if score_obj.get("penalties", {}).get("home") is not None else "",
                                    "penalties_h": score_obj.get("penalties", {}).get("away") if score_obj.get("penalties", {}).get("away") is not None else ""
                                }
                                filtrovane_zapasy_list.append(novy_zapas)

                        if not filtrovane_zapasy_list:
                            st.info(f"📅 V reálném API kalendáři nebyly nalezeny žádné zápasy pro dny: {', '.join(povolene_dny)}.")
                        else:
                            st.write(f"### 📋 Náhled zápasů k aktualizaci (Nalezeno: {len(filtrovane_zapasy_list)}):")
                            st.dataframe(pd.DataFrame(filtrovane_zapasy_list))
                            
                            st.write("🔄 Odesílám selektivní data do Google tabulky...")
                            # Změna akce na chytrou aktualizaci
                            payload = {"action": "aktualizuj_vysledky", "data": filtrovane_zapasy_list}
                            script_res = requests.post(URL_API, json=payload, timeout=15)
                            
                            if script_res.status_code == 200 and script_res.json().get("success"):
                                st.success(f"🔥 Výsledky zápasů ({len(filtrovane_zapasy_list)}) byly úspěšně aktualizovány v Google Sheets!")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                text_chyby = script_res.json().get("error") if script_res.status_code == 200 else script_res.text
                                st.error(f"Chyba Google Scriptu: {text_chyby}")
                else:
                    st.error(f"Chyba API: {data_api.get('message')}")
            except Exception as e:
                st.error(f"Chyba při komunikaci nebo zápisu: {e}")

    st.write("---")
    st.subheader("🔧 Správa střelců a asistencí zápasů")
    
    if "zapasy" in data and len(data["zapasy"]) > 0:
        zapasy_df = pd.DataFrame(data["zapasy"])
        
        # 1. Odfiltrování zápasů, které UŽ MAJÍ uložené střelce
        # (Považujeme zápas za vyřízený, pokud je v strelci_d nebo strelci_h nějaký text)
        rozpracovane_zapasy = zapasy_df[
            (zapasy_df["strelci_d"].isna() | (zapasy_df["strelci_d"].astype(str).str.strip() == "")) &
            (zapasy_df["strelci_h"].isna() | (zapasy_df["strelci_h"].astype(str).str.strip() == ""))
        ]
        
        if rozpracovane_zapasy.empty:
            st.success("🎉 Všechny zápasy mají úspěšně zadané střelce! Žádné další zápasy k doplnění.")
        else:
            # Seřazení a výběr unikátních dnů POUZE ze zápasů, které ještě nemají střelce
            dostupne_dny = sorted(rozpracovane_zapasy["datum"].unique())
            vybrany_den = st.selectbox("📅 Vyber den zápasů pro editaci střelců:", dostupne_dny, key="admin_den_strelcu")
            
            # Filtrace pro daný den z těch rozpracovaných zápasů
            zapasy_dne = rozpracovane_zapasy[rozpracovane_zapasy["datum"] == vybrany_den]
            
            for idx, zapas in zapasy_dne.iterrows():
                id_zapasu = zapas["id"]
                tym_domaci = zapas["domaci"]
                tym_hoste = zapas["hoste"]
                
                # Ošetření prázdných hodnot (zde budou teoreticky vždy prázdné, ale pro jistotu)
                akt_strelci_d = zapas.get("strelci_d", "")
                if pd.isna(akt_strelci_d): akt_strelci_d = ""
                    
                akt_strelci_h = zapas.get("strelci_h", "")
                if pd.isna(akt_strelci_h): akt_strelci_h = ""
                
                with st.container(border=True):
                    st.markdown(f"**⚽ {tym_domaci} vs. {tym_hoste}** *(ID: {id_zapasu})*")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        vstup_d = st.text_area(
                            label=f"Střelci {tym_domaci}",
                            value=akt_strelci_d,
                            placeholder="Formát:\n12' Malík (as. Ševčík)\n45' Kovář",
                            key=f"input_sd_{id_zapasu}",
                            height=100
                        )
                    with col2:
                        vstup_h = st.text_area(
                            label=f"Střelci {tym_hoste}",
                            value=akt_strelci_h,
                            placeholder="Formát:\n60' Robertson",
                            key=f"input_sh_{id_zapasu}",
                            height=100
                        )
                    
                    if st.button("💾 Uložit střelce zápasu", key=f"btn_save_s_{id_zapasu}"):
                        with st.spinner("Ukládám střelce..."):
                            payload = {
                                "action": "uloz_strelce",
                                "id_zapasu": str(id_zapasu),
                                "strelci_domaci": vstup_d.strip(),
                                "strelci_hoste": vstup_h.strip()
                            }
                            try:
                                res = requests.post(URL_API, json=payload, timeout=15)
                                if res.status_code == 200 and res.json().get("success"):
                                    st.success("Uloženo! Zápas byl vyřazen ze seznamu k doplnění.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"Chyba: {res.json().get('error')}")
                            except Exception as e:
                                st.error(f"Chyba spojení: {e}")
    else:
        st.warning("Žádná data o zápasech nebyla nalezena.")
    
    # --- SEKCE PRO ZAMČENÍ CELOTURNAJOVÝCH TIPŮ ---
    st.markdown("---")
    st.subheader("🔒 Uzamčení celoturnajových tipů")
    st.write("Zde můžeš jako správce kompletně uzamknout možnost zadávání a úprav celoturnajových dlouhodobých tipů pro všechny běžné hráče.")

    # Načtení aktuálního stavu z Google Sheets (pokud klíč neexistuje, výchozí je False - otevřeno)
    aktualni_stav_zamku = bool(data.get("admin", {}).get("dlouhodobe_zamknuto", False))

    # Vykreslení zaškrtávacího políčka
    stav_checkbox = st.checkbox("Uzamknout celoturnajové tipy pro hráče", value=aktualni_stav_zamku)

    if st.button("💾 Uložit nastavení zámku", key="btn_save_admin_lock"):
        with st.spinner("Aktualizuji nastavení v Google Sheets..."):
            payload = {
                "action": "uloz_nastaveni_admin",
                "klic": "dlouhodobe_zamknuto",
                "hodnota": bool(stav_checkbox)
            }
            
            try:
                # Použijeme stejnou URL_API, kterou máte definovanou níže v kódu administrace
                res_admin = requests.post(URL_API, json=payload, timeout=15)
                if res_admin.status_code == 200 and res_admin.json().get("success"):
                    if stav_checkbox:
                        st.success("🔒 Celoturnajové tipy byly úspěšně UZAMČENY!")
                    else:
                        st.success("🔓 Celoturnajové tipy byly úspěšně OTEVŘENY pro úpravy!")
                    
                    # Vyčištění cache, aby se změna ihned projevila v celé aplikaci
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Nepodařilo se uložit nastavení do tabulky.")
            except Exception as e:
                st.error(f"Chyba komunikace: {e}")
                
    st.markdown("---")
