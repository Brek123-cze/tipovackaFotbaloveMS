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
"Congo DR": "Konžská dem. rep.",
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
    st.write("Tipuj výsledky zápasů. Na každý hrací den můžeš vsadit jednoho **Žolíka** (dvojnásobné body)!")



    # 1. PŘEVOD NAČTENÝCH ZÁPASŮ NA DATAFRAME
    if not data.get("zapasy"):
        st.info("V tabulce zatím nejsou žádné zápasy. Admin je musí nejdříve naimportovat v nastavení.")
        st.stop()
        
    df_zapasy = pd.DataFrame(data["zapasy"])

    # 2. LOGIKA PLOVOUCÍHO DNE (Od poledne do poledne pro americký časový posun)
    hraci_dny_list = []
    for idx, row in df_zapasy.iterrows():
        try:
            dt = pd.to_datetime(row["datum"])
            # 💡 TRIK: Odečteme 12 hodin. Noční zápasy ze 4:00 ráno spadnou do předchozího dne
            virtual_dt = dt - pd.Timedelta(hours=12)
            hraci_den = virtual_dt.strftime("%Y-%m-%d")
        except:
            hraci_den = "Neznámé datum"
        hraci_dny_list.append(hraci_den)
    
    df_zapasy["hraci_den"] = hraci_dny_list

    # Seřadíme unikátní dny
    unikatni_dny = sorted(list(df_zapasy["hraci_den"].unique()))
    if "Neznámé datum" in unikatni_dny:
        unikatni_dny.remove("Neznámé datum")

    # Pomocná funkce pro hezké zobrazení v roletce (Po 15.06.2026)
    def zformatuj_den(den_str):
        try:
            d = pd.to_datetime(den_str)
            dny_tydne = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
            return f"{dny_tydne[d.weekday()]} {d.strftime('%d.%m.%Y')}"
        except:
            return den_str

    # Automatický výběr dne (pokud turnaj ještě nezačal, skočí na první hrací den)
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

    # Vyfiltrujeme zápasy pouze pro tento jeden plovoucí den
    zapasy_dne = df_zapasy[df_zapasy["hraci_den"] == vybrany_den_raw].sort_values(by="datum")

    if zapasy_dne.empty:
        st.info(f"🌴 Pro den {zformatuj_den(vybrany_den_raw)} není naplánován žádný zápas.")
        st.stop()

    st.write(f"### ⚽ Zápasy pro den: {zformatuj_den(vybrany_den_raw)}")

    # 3. NAČTENÍ DOSAVADNÍCH TIPŮ UŽIVATELE
    df_tipy = pd.DataFrame(data["tipy"]) if data.get("tipy") else pd.DataFrame()

    ma_zolika_dnes = False
    if not df_tipy.empty and "hrac" in df_tipy.columns and "zolik" in df_tipy.columns:
        uzivatel_tipy_dnes = df_tipy[(df_tipy["hrac"] == current_user) & (df_tipy["zapas_id"].isin(zapasy_dne["id"]))]
        if True in uzivatel_tipy_dnes["zolik"].values or "True" in uzivatel_tipy_dnes["zolik"].values or 1 in uzivatel_tipy_dnes["zolik"].values:
            ma_zolika_dnes = True

    st.info("💡 Na každý hrací den můžeš vybrat přesně jednoho **Žolíka**.")
    
    # 4. VYKRESLENÍ FORMULÁŘE PRO TIPOVÁNÍ
    with st.form(key=f"form_tipy_{vybrany_den_raw}"):
        
        for _, z in zapasy_dne.iterrows():
            zapas_id = int(z["id"])
            api_id = int(z["api_id"])    # 🚀 Připraveno pro budoucí online dotazy na web (např. 456789)
            
            tým_d_cz = PREKLAD_TYMU.get(z["domaci"], z["domaci"])
            tým_h_cz = PREKLAD_TYMU.get(z["hoste"], z["hoste"])
            cas_zapasu = z["datum"][11:16] if len(z["datum"]) >= 16 else ""
            
            st.write(f"**{z['faze']}** {f'— Skupina {z['skupina']}' if z['skupina'] else ''} ({cas_zapasu})")
            
            col_domaci, col_input_d, col_vs, col_input_h, col_hoste = st.columns([3, 1, 0.5, 1, 3])
            
            with col_domaci:
                if z.get("vlajka_d"):
                    st.image(z["vlajka_d"], width=30)
                st.markdown(f"<div style='padding-top:5px;'><b>{tým_d_cz}</b></div>", unsafe_allow_html=True)
                
            with col_input_d:
                tip_d_val = st.number_input("", min_value=0, max_value=20, step=1, key=f"d_{zapas_id}", label_visibility="collapsed")
                
            with col_vs:
                st.markdown("<h4 style='text-align: center; margin: 0;'>:</h4>", unsafe_allow_html=True)
                
            with col_input_h:
                tip_h_val = st.number_input("", min_value=0, max_value=20, step=1, key=f"h_{zapas_id}", label_visibility="collapsed")
                
            with col_hoste:
                if z.get("vlajka_h"):
                    st.image(z["vlajka_h"], width=30)
                st.markdown(f"<div style='padding-top:5px;'><b>{tým_h_cz}</b></div>", unsafe_allow_html=True)
            
            zolik_checkbox = st.checkbox("🃏 Použít Žolíka na tento zápas", key=f"zolik_{zapas_id}")
            st.markdown("---")

        submit_button = st.form_submit_button(label="💾 Uložit moje tipy pro tento den")
        
        if submit_button:
            vybrani_zolici = [st.session_state[f"zolik_{z['id']}"] for _, z in zapasy_dne.iterrows() if f"zolik_{z['id']}" in st.session_state]
            
            if sum(vybrani_zolici) > 1:
                st.error("❌ Chyba: Můžeš si vybrat pouze jednoho Žolíka na jeden hrací den!")
            else:
                st.success("Tipy jsou připraveny k zápisu!")
   
    
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
