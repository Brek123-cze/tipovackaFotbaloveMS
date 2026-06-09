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

@st.cache_data(ttl=300)  # ⏱️ Data se stáhnou z Googlu jen jednou za 5 minut, zbytek se tahá z bleskové cache!
def nacti_fotbalova_data():
    """Načte kompletní data (zapasy, tipy, admin) přímo přes Google Apps Script URL"""
    URL_API = "https://script.google.com/macros/s/AKfycbzckuQpf_fNckc9R9rrW9b7y9HUqqFHjxuD8Djd8PORtWL7zuU0l7DX1JgC92zw5aN5/exec"
    try:
        response = requests.get(URL_API, timeout=15)
        if response.status_code == 200:
            return response.json()
        return {"zapasy": [], "tipy": [], "admin": {}}
    except:
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
# 🏠 JEDNOTLIVÉ SEKCE APLIKACE
# =========================================================================
if volba == "Žebříček hráčů 🏆":
    st.title("🏆 Průběžný žebříček fotbalové tipovačky")
    st.info("Zde bude tabulka s body, medailemi a rozbalovací matice zápas po zápase.")

elif volba == "Moje tipy 📝":
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

    # 🛡️ BEZPEČNÁ POJISTKA (Žádné mazání cache, žádný rerun = KONEC CYKLENÍ)
    if not data or "zapasy" not in data or len(data["zapasy"]) == 0:
        st.error("❌ Nepodařilo se načíst data o zápasech z Google tabulky.")
        st.info("💡 Klikni prosím v levém menu na tlačítko: **🔄 Aktualizovat data z tabulky**, které data stáhne znovu.")
        st.stop() # 🛑 Kód se bezpečně zastaví, blikání ihned ustane

    # 1. PŘEVOD NAČTENÝCH ZÁPASŮ NA DATAFRAME
    if not data.get("zapasy"):
        st.info("V tabulce zatím nejsou žádné zápasy.")
        st.stop()
        
    df_zapasy = pd.DataFrame(data["zapasy"])

    # 2. LOGIKA PLOVOUCÍHO DNE (Český čas +4 hodiny, plovoucí posun)
    hraci_dny_list = []
    ceske_casy_list = []
    for idx, row in df_zapasy.iterrows():
        try:
            gmt_dt = pd.to_datetime(row["datum"])
            cz_dt = gmt_dt + pd.Timedelta(hours=4)  # Tvoje vyzkoušené funkční nastavení
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
    if Insert_dnesni_datum_str := dnesni_datum_str in unikatni_dny:
        index_vychozi = unikatni_dny.index(dnesni_datum_str)

    vybrany_den_raw = st.selectbox("📅 Vyber hrací den:", unikatni_dny, index=index_vychozi, format_func=zformatuj_den)
    zapasy_dne = df_zapasy[df_zapasy["hraci_den"] == vybrany_den_raw].sort_values(by="datum")

    if zapasy_dne.empty:
        st.info("🌴 Žádné zápasy.")
        st.stop()

    st.write(f"### ⚽ Zápasy pro den: {zformatuj_den(vybrany_den_raw)}")

    # 3. NAČTENÍ DOSAVADNÍCH TIPŮ DO SESSION STATE (Provede se pouze jednou při změně dne)
    df_tipy = pd.DataFrame(data["tipy"]) if data.get("tipy") else pd.DataFrame()

    # Inicializujeme session state klíče z databáze, pokud tam ještě nejsou
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

    # 4. VYKRESLENÍ MATICE ZÁPASŮ (Čistá lokální mačkátka)
    st.markdown("<br>", unsafe_allow_html=True)
    col_vnejsi_vlevo, col_hlavni_obsah, col_vnejsi_vpravo = st.columns([0.5, 5, 0.5])
    
    with col_hlavni_obsah:
        for _, z in zapasy_dne.iterrows():
            zapas_id = int(z["id"])
            tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
            tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
            cas_zapasu = z["cesky_cas"][11:16] if len(z["cesky_cas"]) >= 16 else ""
            
            pismeno_skupiny = str(z["skupina"]).strip() if pd.notna(z["skupina"]) else ""
            faze_cz = preloz_fazi(z["faze"])
            text_faze = f"{faze_cz} — Skupina {pismeno_skupiny}" if pismeno_skupiny and pismeno_skupiny != "None" else faze_cz

            # Načteme hodnoty ze session_state (vše běží interně v cache prohlížeče)
            val_d = st.session_state[f"v_d_{zapas_id}"]
            val_h = st.session_state[f"v_h_{zapas_id}"]

            # [ŘÁDEK ZÁPASU]
            c_cas, c_td, c_vd, c_btn_dm, c_v_d, c_btn_dp, c_dvoj, c_btn_hm, c_v_h, c_btn_hp, c_vh, c_th, c_zol = st.columns(
                [1.3, 2.0, 0.5, 0.4, 0.5, 0.4, 0.2, 0.4, 0.5, 0.4, 0.5, 2.0, 1.5]
            )
            
            with c_cas:
                st.markdown(f"<div style='padding-top: 5px; color: #666; font-size: 0.82rem;'><b>{cas_zapasu}</b><br><small style='color:#999;'>{text_faze}</small></div>", unsafe_allow_html=True)
            with c_td:
                st.markdown(f"<div style='text-align: right; font-weight: bold; padding-top: 6px;'>{tým_d_cz}</div>", unsafe_allow_html=True)
            with c_vd:
                if z.get("vlajka_d"): st.markdown(f"<div style='text-align: center; padding-top: 4px;'><img src='{z['vlajka_d']}' width='25'></div>", unsafe_allow_html=True)
            
            # ➖ Domácí
            with c_btn_dm:
                if st.button("➖", key=f"m_d_{zapas_id}") and st.session_state[f"v_d_{zapas_id}"] > 0:
                    st.session_state[f"v_d_{zapas_id}"] -= 1
                    st.rerun()
            with c_v_d:
                st.markdown(f"<h4 style='text-align: center; margin: 0; padding-top:2px;'>{val_d}</h4>", unsafe_allow_html=True)
            # ➕ Domácí
            with c_btn_dp:
                if st.button("➕", key=f"p_d_{zapas_id}"):
                    st.session_state[f"v_d_{zapas_id}"] += 1
                    st.rerun()
                    
            with c_dvoj:
                st.markdown("<div style='text-align: center; font-weight: bold; padding-top: 2px; color: #999;'>:</div>", unsafe_allow_html=True)
                
            # ➖ Hosté
            with c_btn_hm:
                if st.button("➖", key=f"m_h_{zapas_id}") and st.session_state[f"v_h_{zapas_id}"] > 0:
                    st.session_state[f"v_h_{zapas_id}"] -= 1
                    st.rerun()
            with c_v_h:
                st.markdown(f"<h4 style='text-align: center; margin: 0; padding-top:2px;'>{val_h}</h4>", unsafe_allow_html=True)
            # ➕ Hosté
            with c_btn_hp:
                if st.button("➕", key=f"p_h_{zapas_id}"):
                    st.session_state[f"v_h_{zapas_id}"] += 1
                    st.rerun()
                    
            with c_vh:
                if z.get("vlajka_h"): st.markdown(f"<div style='text-align: center; padding-top: 4px;'><img src='{z['vlajka_h']}' width='25'></div>", unsafe_allow_html=True)
            with c_th:
                st.markdown(f"<div style='text-align: left; font-weight: bold; padding-top: 6px;'>{tým_h_cz}</div>", unsafe_allow_html=True)
            with c_zol:
                # Žolík se ukládá do session state okamžitě
                st.session_state[f"v_zol_{zapas_id}"] = st.checkbox("🃏 Žolík", value=st.session_state[f"v_zol_{zapas_id}"], key=f"ch_z_{zapas_id}")
            
            st.markdown("<hr style='margin: 3px 0; border: 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)

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
                        
                        URL_API = "https://script.google.com/macros/s/AKfycbzckuQpf_fNckc9R9rrW9b7y9HUqqFHjxuD8Djd8PORtWL7zuU0l7DX1JgC92zw5aN5/exec"
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
