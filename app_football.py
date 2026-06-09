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
    """Načte kompletní data (zapasy, tipy, admin) přímo přes Google Apps Script URL jako hokej"""
    # Použijeme tvou URL adresu skriptu z administrace
    URL_API = "https://script.google.com/macros/s/AKfycbypVyn-7dy9KRAvlTmRkZ7R9d66Ux9LraaSDeC0A8m0C1LGvcRmuq2lh-jlPSgbL9y1/exec"
    
    try:
        # Pošleme rychlý GET požadavek na Google skript
        response = requests.get(URL_API, timeout=15)
        if response.status_code == 200:
            vysledek = response.json()
            # Pokud skript vrátil interní chybu, ošetříme to
            if "error" in vysledek:
                st.sidebar.error(f"Interní chyba skriptu: {vysledek['error']}")
                return {"zapasy": [], "tipy": [], "admin": {}}
            return vysledek
        else:
            st.sidebar.error(f"Chyba spojení se skriptem: Status {response.status_code}")
            return {"zapasy": [], "tipy": [], "admin": {}}
    except Exception as e:
        st.sidebar.error(f"Chyba při stahování dat: {e}")
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
    st.title("📝 Moje Tipy na zápasy MS 2026")
    st.write(f"Vítej ve svém tipovacím lístku, **{current_user}**. Na každý hrací den můžeš vsadit jednoho **Žolíka** (dvojnásobné body)!")

    # 1. PŘEVOD NAČTENÝCH ZÁPASŮ NA DATAFRAME
    if not data.get("zapasy"):
        st.info("V tabulce zatím nejsou žádné zápasy. Admin je musí nejdříve naimportovat v nastavení.")
        st.stop()
        
    df_zapasy = pd.DataFrame(data["zapasy"])

    # 2. LOGIKA PLOVOUCÍHO DNE (GMT + 2 hodiny ČR, pak -6 hodin pro zařazení nočních zápasů k předchozímu večeru)
    hraci_dny_list = []
    ceske_casy_list = []

    for idx, row in df_zapasy.iterrows():
        try:
            gmt_dt = pd.to_datetime(row["datum"])
            
            # 🇨🇿 REÁLNÝ ČAS V ČR (Přičteme 2 hodiny k GMT)
            cz_dt = gmt_dt + pd.Timedelta(hours=4)
            ceske_casy_list.append(cz_dt.strftime("%Y-%m-%d %H:%M"))
            
            # 💡 PLOVOUCÍ DEN: Odečteme 6 hodin. Zápas ve 2:00 ráno (16.6.) skočí do 20:00 (15.6.) 
            # a zůstane v jednom lístku s večerními zápasy.
            virtual_dt = cz_dt - pd.Timedelta(hours=8)
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

    def zformatuj_den(den_str):
        try:
            d = pd.to_datetime(den_str)
            dny_tydne = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
            return f"{dny_tydne[d.weekday()]} {d.strftime('%d.%m.%Y')}"
        except:
            return den_str

    dnesni_datum_str = time.strftime("%Y-%m-%d")
    index_vychozi = 0
    if dnesni_datum_str in unikatni_dny:
        index_vychozi = unikatni_dny.index(dnesni_datum_str)

    vybrany_den_raw = st.selectbox(
        "📅 Vyber hrací den:", 
        unikatni_dny, 
        index=index_vychozi,
        format_func=zformatuj_den
    )

    zapasy_dne = df_zapasy[df_zapasy["hraci_den"] == vybrany_den_raw].sort_values(by="datum")

    if zapasy_dne.empty:
        st.info(f"🌴 Pro den {zformatuj_den(vybrany_den_raw)} není naplánován žádný zápas.")
        st.stop()

    st.write(f"### ⚽ Zápasy pro den: {zformatuj_den(vybrany_den_raw)}")

    # 3. NAČTENÍ DOSAVADNÍCH TIPŮ PRO PŘEDVYPLNĚNÍ
    df_tipy = pd.DataFrame(data["tipy"]) if data.get("tipy") else pd.DataFrame()

    # 🔤 SLOVNÍK PRO PŘEKLAD FÁZÍ TURNÁJE
    # API občas vrací tyhle dlouhé slepené řetězce, tak je radši pokryjeme všechny
    PREKLAD_FAZE = {
        "GROUP_STAGE": "Základní skupina",
        "LAST_32": "Šestnáctifinále (1/32)",
        "LAST_16": "Osmifinále (1/16)",
        "QUARTER_FINALS": "Čtvrtfinále",
        "SEMI_FINALS": "Semifinále",
        "THIRD_PLACE": "O 3. místo 🥉",
        "FINAL": "FINÁLE 🏆"
    }
    # Automaticky vyřešíme i ty divoké spojené texty z API (např. LAST_32LAST_32...)
    def preloz_fazi(faze_str):
        if not faze_str:
            return ""
        faze_str = str(faze_str).strip()
        if "GROUP_STAGE" in faze_str: return PREKLAD_FAZE["GROUP_STAGE"]
        if "LAST_32" in faze_str: return PREKLAD_FAZE["LAST_32"]
        if "LAST_16" in faze_str: return PREKLAD_FAZE["LAST_16"]
        if "QUARTER_FINALS" in faze_str: return PREKLAD_FAZE["QUARTER_FINALS"]
        if "SEMI_FINALS" in faze_str: return PREKLAD_FAZE["SEMI_FINALS"]
        if "THIRD_PLACE" in faze_str: return PREKLAD_FAZE["THIRD_PLACE"]
        if "FINAL" in faze_str: return PREKLAD_FAZE["FINAL"]
        return faze_str

    # 4. VYKRESLENÍ ZÁPASŮ A FORMULÁŘE
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_vnejsi_vlevo, col_hlavni_obsah, col_vnejsi_vpravo = st.columns([0.5, 5, 0.5])
    
    with col_hlavni_obsah:
        vstupy_tipu = {}
        
        for idx_zapasu, z in zapasy_dne.iterrows():
            zapas_id = int(z["id"])
            tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
            tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
            cas_zapasu = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
            
            # 💡 BEZPEČNÉ NAČTENÍ SKUPINY: Použijeme z["skupina"] přímo z aktuálního řádku zápasu 'z'
            pismeno_skupiny = str(z["skupina"]).strip() if pd.notna(z["skupina"]) else ""
            faze_cz = preloz_fazi(z["faze"])
            
            # Sestavení hezkého podnadpisu (Základní skupina A, nebo jen Čtvrtfinále)
            if pismeno_skupiny and pismeno_skupiny != "None" and pismeno_skupiny != "":
                text_faze = f"{faze_cz} Skupina {pismeno_skupiny}"
            else:
                text_faze = faze_cz

            # Najdeme stávající tip
            stajici_d = 0
            stajici_h = 0
            stavajici_zolik = False
            
            if not df_tipy.empty and "hrac" in df_tipy.columns and "zapas_id" in df_tipy.columns:
                stavy = df_tipy[(df_tipy["hrac"] == current_user) & (df_tipy["zapas_id"] == zapas_id)]
                if not stavy.empty:
                    stajici_d = int(stavy.iloc[0]["tip_d"])
                    stajici_h = int(stavy.iloc[0]["tip_h"])
                    stavajici_zolik = bool(stavy.iloc[0]["zolik"])

            # JEDEN KOMPAKTNÍ ŘÁDEK
            c_cas, c_td, c_vd, c_id, c_dvoj, c_ih, c_vh, c_th, c_zol = st.columns([1.2, 2.3, 0.5, 1, 0.3, 1, 0.5, 2.3, 1.7])
            
            with c_cas:
                st.markdown(f"<div style='padding-top: 8px; color: #666; font-size: 0.85rem;'><b>{cas_zapasu}</b><br><small style='color:#999;'>{text_faze}</small></div>", unsafe_allow_html=True)
                
            with c_td:
                st.markdown(f"<div style='text-align: right; font-weight: bold; padding-top: 6px; font-size: 1.0rem;'>{tým_d_cz}</div>", unsafe_allow_html=True)
                
            with c_vd:
                if z.get("vlajka_d"):
                    st.markdown(f"<div style='text-align: center; padding-top: 4px;'><img src='{z['vlajka_d']}' width='28'></div>", unsafe_allow_html=True)
                    
            with c_id:
                tip_d = st.number_input("", min_value=0, max_value=20, value=stajici_d, step=1, key=f"inp_d_{zapas_id}", label_visibility="collapsed")
                
            with c_dvoj:
                st.markdown("<div style='text-align: center; font-weight: bold; padding-top: 4px; color: #888;'>:</div>", unsafe_allow_html=True)
                
            with c_ih:
                tip_h = st.number_input("", min_value=0, max_value=20, value=stajici_h, step=1, key=f"inp_h_{zapas_id}", label_visibility="collapsed")
                
            with c_vh:
                if z.get("vlajka_h"):
                    st.markdown(f"<div style='text-align: center; padding-top: 4px;'><img src='{z['vlajka_h']}' width='28'></div>", unsafe_allow_html=True)
                    
            with c_th:
                st.markdown(f"<div style='text-align: left; font-weight: bold; padding-top: 6px; font-size: 1.0rem;'>{tým_h_cz}</div>", unsafe_allow_html=True)
                
            with c_zol:
                zolik = st.checkbox("🃏 Žolík", value=stavajici_zolik, key=f"chk_zol_{zapas_id}")
            
            vstupy_tipu[zapas_id] = {"tip_d": tip_d, "tip_h": tip_h, "zolik": zolik}
            st.markdown("<div style='margin: 4px 0;'></div>", unsafe_allow_html=True)

        # HROMADNÉ TLAČÍTKO POD VŠEMI ZÁPASY
        st.markdown("<br><br>", unsafe_allow_html=True)
        c_btn_l, c_btn_m, c_btn_r = st.columns([1.5, 2, 1.5])
        
        with c_btn_m:
            if st.button("💾 Uložit všechny tipy pro tento den", key="save_all_day_tips", use_container_width=True):
                pocet_zoliku = sum([1 for t in vstupy_tipu.values() if t["zolik"]])
                
                if pocet_zoliku > 1:
                    st.error("❌ Chyba: Můžeš si vybrat pouze jednoho Žolíka na jeden hrací den!")
                else:
                    with st.spinner("Ukládám všechny tipy do tabulky..."):
                        for z_id, hodnoty in vstupy_tipu.items():
                            uloz_tip_hrace(
                                hrac=current_user,
                                zapas_id=z_id,
                                tip_d=hodnoty["tip_d"],
                                tip_h=hodnoty["tip_h"],
                                zolik=hodnoty["zolik"]
                            )
                    st.success("🎉 Všechny tipy byly úspěšně uloženy najednou!")
                    time.sleep(1)
                    st.rerun()   
    
elif volba == "Celoturnajové tipy 🔮":
    st.title("🔮 Celoturnajové dlouhodobé tipy")
    st.write("Tipy na Mistra světa, semifinalisty a celkový počet gólů před výkopem prvního zápasu.")

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
