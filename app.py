import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from openai import OpenAI
import base64
from io import BytesIO
import plotly.graph_objects as go
import json
from dotenv import load_dotenv
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import streamlit.components.v1 as components
from summary_service import get_audit_summary

# ---  DİNAMİK YOL VE GÜVENLİK AYARLARI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POPPLER_PATH = os.path.join(BASE_DIR, "poppler_files", "bin")
   
# --- API KEY'İ OTOMATİK YÜKLE ---
load_dotenv() 
api_key = os.getenv("OPENAI_API_KEY")


# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="TEDAŞ Teknik Denetim Demo Web Sitesi", layout="wide")


def get_img_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

hide_styles = """
    <style>
    /* Üst barı, Deploy butonunu ve tüm header'ı yok eder */
    header, [data-testid="stToolbar"], .stAppDeployButton {
        display: none !important;
        visibility: hidden !important;
        height: 0;
    }
    
    /* Sağ üstteki üç nokta menüsünü gizler */
    #MainMenu {visibility: hidden;}
    
    /* En alttaki 'Made with Streamlit' yazısını gizler */
    footer {visibility: hidden;}
    
    /* Sayfanın en üstündeki gereksiz boşluğu kapatır */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }
    </style>
"""
st.markdown(hide_styles, unsafe_allow_html=True)

# --- AUTO LIGHT THEME & CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* --- ZORUNLU LIGHT TEMA AYARLARI --- */
    /* Kullanıcının tarayıcısı Dark modda olsa bile burası Light çalışır */
    :root {
        --primary-color: #4f86c3;
        --background-color: #f5f8fa;
        --secondary-background-color: #ffffff;
        --text-color: #000000;
        --font: 'Inter', sans-serif;
    }
    
    /* Tüm Sayfa Arka Planı */
    body, .stApp { 
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important; 
        background-color: #f5f8fa !important; 
        color: #000000 !important;
    }

    /* --- SIDEBAR VE HEADER --- */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e0e6ed;
    }
    [data-testid="stHeader"] {
        background-color: #ffffff !important;
        border-bottom: 1px solid #e0e6ed;
    }
    
    /* Sidebar içindeki tüm yazılar Siyah */
    section[data-testid="stSidebar"] * {
        color: #000000 !important;
    }

    /* --- SIDEBAR AÇMA/KAPAMA BUTONLARI (KESİN ÇÖZÜM) --- */
    /* Hem sidebar kapalıyken (ok) hem açıkken (çarpı) */
    
    /* 1. Butonların Konteyner Ayarı */
    [data-testid="stSidebarCollapsedControl"],
    button[kind="header"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: transparent !important;
        border: none !important;
        z-index: 999999 !important; /* En üstte tut */
        color: #000000 !important;
    }
    /* --- BROWSE FILES BUTONU --- */
    [data-testid="stFileUploader"] button,
    [data-testid="stFileUploader"] label {
        background-color: #4f86c3 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600;
        transition: all 0.25s ease;
    }

    /* Hover efekti */
    [data-testid="stFileUploader"] button:hover,
    [data-testid="stFileUploader"] label:hover {
        background-color: #3b6da0 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }

    /* 2. İkonların (SVG) Rengi - SİYAH */
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="stSidebarCollapsedControl"] svg path,
    button[kind="header"] svg,
    button[kind="header"] svg path,
    [data-testid="stHeader"] button svg {
        fill: #000000 !important;  /* İçi siyah */
        stroke: #000000 !important; /* Çizgisi siyah */
        color: #000000 !important;
    }

    /* 3. Hover (Üzerine gelince) Ayarı - Sabit kalsın */
    [data-testid="stSidebarCollapsedControl"]:hover,
    button[kind="header"]:hover {
        background-color: rgba(0,0,0,0.05) !important; /* Hafif gri */
        color: #000000 !important;
    }

    /* --- DOSYA YÜKLEME KUTUSU --- */
    [data-testid="stFileUploaderDropzone"] {
        background-color: #f5f8fa !important;
        border: 2px dashed #4f86c3 !important;
        border-radius: 10px;
    }
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small {
        color: #000000 !important;
    }

    /* --- BUTONLAR --- */
    div.stButton > button {
        background-color: #4f86c3 !important;
        color: white !important;
        border: none !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #3b6da0 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    
    /* --- KARTLAR VE DETAYLAR --- */
    .metric-container, .metric-card, .evidence-box {
        background: white;
        border-radius: 10px;
        color: #000000 !important;
    }
    .metric-container { border-bottom: 4px solid #4f86c3; padding: 20px; }
    .metric-card { padding: 15px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .evidence-box { padding: 25px; border: 1px solid #e0e6ed; box-shadow: 0 10px 15px rgba(0,0,0,0.05); height: 100%; }
    
    .metric-card p, .metric-card h1 { color: #000000 !important; }
    .main-header { color: #000000 !important; font-size: 2rem; font-weight: 700; margin-bottom: 1rem; }
    
    .tag-page {
        background: #e3f2fd;
        color: #0d47a1;
        padding: 3px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE FUNCTIONS ---
def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def read_excel_content(file):
    xls = pd.ExcelFile(file)
    content = ""
    for sheet in xls.sheet_names:
        df = pd.read_excel(file, sheet_name=sheet).dropna(how='all').fillna("")
        content += f"\n[Sayfa: {sheet}]\n{df.to_string(index=False)}\n"
    return content

@st.dialog("📋 Denetim Yönetici Özeti", width="large")
def show_summary_popup():
    summary_raw = st.session_state['audit_summary']
    
    # AI'dan gelen veriyi ayrıştır
    try:
        firma = summary_raw.split("[FIRMA_ISMI]:")[1].split("[OZET_METNI]:")[0].strip()
        ozet = summary_raw.split("[OZET_METNI]:")[1].strip()
    except:
        firma = ""
        ozet = summary_raw

    # Özet içeriği ve modern tasarım
    st.markdown(f"""
        <div style="
            background: #ffffff;
            border-radius: 12px;
            border-left: 6px solid #1e293b;
            padding: 2px;
            font-family: 'Inter', sans-serif;
        ">
            <div style="padding: 15px 20px; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; background: #f8faff; border-radius: 12px 12px 0 0;">
                <span style="color: #64748b; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Denetlenen Firma</span>
                <span style="color: #1e293b; font-weight: 700; font-size: 1.1rem;">{firma}</span>
            </div>
            <div style="padding: 25px; color: #334155; font-size: 1rem; line-height: 1.6;">
                <div style="margin-bottom: 15px; font-weight: 700; color: #1e293b; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                    ⚡ Kritik Teknik Bulgular
                </div>
                <div style="background: #ffffff;">
                    {ozet}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Kapat", use_container_width=True):
        st.rerun()



def show_loader(placeholder):
    placeholder.markdown("""
    <style>
    .loader-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(245,248,250,0.9);
        z-index: 999999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        backdrop-filter: blur(3px);
    }

    .spinner {
        border: 6px solid #e0e6ed;
        border-top: 6px solid #4f86c3;
        border-radius: 50%;
        width: 70px;
        height: 70px;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .loader-text {
        margin-top: 18px;
        font-size: 20px;
        font-weight: 600;
        color: #1e293b;
    }
    </style>

    <div class="loader-overlay">
        <div class="spinner"></div>
        <div class="loader-text">Lütfen bekleyiniz, analiz ediliyor...</div>
    </div>
    """, unsafe_allow_html=True)


# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:#0052cc;'>⚙️ Kontrol Paneli</h2>", unsafe_allow_html=True)

    excel_file = st.file_uploader("📋 Şartname (Excel)", type=['xlsx'])
    pdf_file = st.file_uploader("📄 Deney Raporu (PDF)", type=['pdf'])
    
   
    st.divider()
    analyze_btn = st.button("🚀 Denetimi Başlat", use_container_width=True, type="primary")

# --- 4. MAIN LOGIC ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Görselin yolunu belirtiyoruz (image/logo.png)
img_path = os.path.join("images", "TEDAS-Logo.png")

if os.path.exists(img_path):
    img_base64 = get_base64_of_bin_file(img_path)

    header_html = f"""
    <div style="display:flex;align-items:center;gap:20px;margin-bottom:15px;">

        <img src="data:image/png;base64,{img_base64}" width="100"/>

        <div style="display:flex;flex-direction:column;line-height:1.1;">
            <span style="color:#d32f2f;font-size:28px;font-weight:800;letter-spacing:1px;">
                TEDAŞ
            </span>
            <span style="color:#000000;font-size:13px;font-weight:500;">
                Türkiye Elektrik Dağıtım A.Ş.
            </span>
        </div>

        <div style="margin-left:20px;font-size:1.5rem;font-weight:700;color:#1E1E1E;">
            ⚡ Analiz Programı (Demo Web Sürümü) - Teknik Denetim Paneli
        </div>

    </div>
    """

    components.html(header_html, height=110)

else:
    st.error("Logo dosyası bulunamadı! Lütfen 'images/TEDAS-Logo.png' yolunu kontrol edin.")


if analyze_btn and api_key and excel_file and pdf_file:
    client = OpenAI(api_key=api_key)
    try:
            loader_placeholder = st.empty()
            show_loader(loader_placeholder)
            spec_data = read_excel_content(excel_file)
            pdf_bytes = pdf_file.getvalue()
            if os.path.exists(POPPLER_PATH):
                # Kendi bilgisayarında (Windows) burası çalışır
                images = convert_from_bytes(pdf_bytes, dpi=120, poppler_path=POPPLER_PATH)
            else:
                # Streamlit Cloud (Linux) üzerinde burası çalışır
                images = convert_from_bytes(pdf_bytes, dpi=120)
            st.session_state['pdf_pages'] = images
            
            all_results = []
            batch_size = 5
            for i in range(0, len(images), batch_size):
                batch_images = images[i : i + batch_size]
                b64_batch = [encode_image(img) for img in batch_images]
                
                prompt = f"""Teknik denetim yap. Excel: {spec_data}
                 JSON format: {{"sonuc": [{{"parametre": "..", "limit": "..", "olculen": "..", "durum": "Uygun/Uygun Değil", "sayfa": {i+1} , "satir_kanit": ".."}}]}}"""

            #     prompt = f"""
            # Sen, **TEDAŞ Standartlarına Hakim Kıdemli bir Test ve Kabul Mühendisisin.**
            # Görevin, Excel'deki teknik şartnameyi, PDF'deki "Deney Verileri" ve "Test Sonuçları" sayfalarıyla sayısal olarak doğrulamaktır.

            # ### 🎯 ANALİZ ODAK NOKTASI: SAYISAL VERİLER
            # 1. **Deney Verilerine Odaklan:** PDF içindeki "Ölçüm Sonuçları", "Deney Tabloları" veya "Test Verileri" başlıklarını bul. Sayısal karşılaştırmaları öncelikle bu tablolardan yap.
            # 2. **Birim Uyumu:** Excel ve PDF arasındaki birimleri (kV, A, Ohm, MVA, K, vb.) kontrol et. Birim dönüşümü gerekiyorsa (örn: ms -> sn) bunu yaparak karşılaştır.
            # 3. **Tolerans Kontrolü:** Eğer Excel'de "+/- %10" gibi bir tolerans varsa, ölçülen değerin bu aralıkta olup olmadığını matematiksel olarak hesapla ve "durum"u buna göre belirle.
            # 4. **Anlamsal Eşleştirme:** PDF'de "Sargı Direnci" yazarken Excel'de "Resistance of Winding" yazabilir. Bunların aynı teknik parametre olduğunu tespit et.

            # ---
            # ### 🛠️ GİRDİ VERİLERİ:
            # - **Şartname (Referans):** {spec_data}

            # ---
            # ### 📏 KURALLAR:
            # - **Sadece Excel'de olan parametreleri getir.** PDF'de fazladan veri varsa görmezden gel.
            # - **Sayısal Değer Yoksa:** PDF'de ilgili parametreye dair rakamsal bir veri bulunamıyorsa durumu "Bulunamadı" yap.
            # - **Kanıt Zorunluluğu:** `satir_kanit` kısmına PDF'deki ilgili hücrenin veya satırın değerini birimle birlikte aynen yaz.
            # - **Hata Payı:** Eğer bir değer sınırda ise veya uygun değilse, `teknik_not` kısmına nedenini (örn: "%12 sapma tespit edildi, limit dışı") yaz.

            # ---
            # ### 📤 ÇIKTI FORMATI (JSON):
            # {{
            # "sonuc": [
            #     {{
            #     "parametre": "Parametre Adı (Excel'deki haliyle)",
            #     "limit": "Şartnamedeki limit değer",
            #     "olculen": "PDF'de tespit edilen sayısal değer",
            #     "durum": "Uygun / Uygun Değil / Bulunamadı",
            #     "sayfa": {i+1},
            #     "satir_kanit": "PDF'deki orijinal tablo satırı veya cümle",
            #     "teknik_not": "Varsa sapma miktarı veya teknik açıklama"
            #     }}
            # ]
            # }}
            # """

                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}] + [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}} for b in b64_batch]}],
                    response_format={"type": "json_object"}
                )
                all_results.extend(json.loads(response.choices[0].message.content)["sonuc"])
            
            st.session_state['final_results'] = all_results

            with st.spinner("Yönetici özeti hazırlanıyor..."):
                summary_text = get_audit_summary(api_key, pd.DataFrame(all_results), spec_data)
                st.session_state['audit_summary'] = summary_text
            
    except Exception as e:
        st.error(f"Hata: {str(e)}")
    finally:
        loader_placeholder.empty()

# --- 5. INTERAKTIF DENETIM PANELİ & RAPORLAMA ---
if 'final_results' in st.session_state:
    # 1. Veriyi Hazırla
    res_df = pd.DataFrame(st.session_state['final_results'])
    
    # Uzman Onayı sütunu yoksa en başa ekle
    if 'Uzman Onayı' not in res_df.columns:
        res_df.insert(0, 'Uzman Onayı', False)

    # 2. Üst Bölüm: Metrik Kartları
    total = len(res_df)
    uygun = len(res_df[res_df['durum'] == 'Uygun'])
    hatali = len(res_df[res_df['durum'] != 'Uygun'])
    uygunluk_orani = int((uygun / total) * 100) if total > 0 else 0

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        fig = go.Figure(data=[go.Pie(labels=['Uygun', 'Uygun Değil'], values=[uygun, hatali], hole=.7, 
                                     marker_colors=['#28a745', '#dc3545'], textinfo='none')])
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200, paper_bgcolor="rgba(0,0,0,0)",
                          annotations=[dict(text=f'%{uygunluk_orani}', x=0.5, y=0.5, font_size=20, showarrow=False, font_color="#000000")])
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with c2:
        st.markdown(f'<div class="metric-card" style="height: 205px; display: flex; flex-direction: column; justify-content: center;">'
                    f'<p style="color: #64748b; margin-bottom: 5px;">Toplam Kontrol Noktası</p>'
                    f'<h1 style="color: #1e293b; font-size: 3rem; margin: 0;">{total}</h1>'
                    f'<p style="color: #0052cc; font-weight: 600;">Kriter İncelendi</p></div>', unsafe_allow_html=True)

    with c3:
        sayfa_sayisi = len(st.session_state.get('pdf_pages', []))
        st.markdown(f'<div class="metric-card" style="height: 205px; text-align: left; padding: 25px;">'
                    f'<p style="color: #64748b; margin-bottom: 10px;">Rapor Özeti</p>'
                    f'<div>📄 Sayfa Sayısı: <b>{sayfa_sayisi}</b></div>'
                    f'<div>✅ Uygun: <b style="color: #28a745;">{uygun}</b></div>'
                    f'<div>❌ Uygun Değil: <b style="color: #dc3545;">{hatali}</b></div>'
                    f'<div style="margin-top: 15px; background: #f1f5f9; height: 8px; border-radius: 10px;">'
                    f'<div style="background: #0052cc; width: {uygunluk_orani}%; height: 8px; border-radius: 10px;"></div></div></div>', unsafe_allow_html=True)
        

    st.divider()

    # --- 3. AgGrid: Uzman Onay Tablosu ---
    st.markdown("### 📋 Denetim Sonuç Listesi & Uzman Onayı")
    st.info("💡 **Uzman Talimatı: Kanıtı incelemek için satıra tıklayın.Onaylamak için 'Uzman Onayı' kutucuğunu işaretleyin.**")

    # Veriyi hazırlarken session_state'i ana kaynak yap
    res_df = pd.DataFrame(st.session_state['final_results'])
    
    if 'Uzman Onayı' not in res_df.columns:
        res_df.insert(0, 'Uzman Onayı', False)

    gb = GridOptionsBuilder.from_dataframe(res_df)
    
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    gb.configure_grid_options(tooltipShowDelay=0, tooltipMouseTrack=True, enableBrowserTooltips=True)

    # Sütun Tanımlamaları
    gb.configure_column("parametre", headerName="Denetim Parametresi", width=300, tooltipField="parametre")
    gb.configure_column("limit", headerName="Şartname Limiti", width=250, tooltipField="limit")
    gb.configure_column("olculen", headerName="Ölçülen Değer", width=200, tooltipField="olculen")
    gb.configure_column("Uzman Onayı", editable=True, pinned='left', width=120)

    gb.configure_column("durum", cellStyle=JsCode("""
        function(params) {
            if (params.value == 'Uygun') return {'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': 'bold'};
            return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': 'bold'};
        }
    """))

    gb.configure_selection("single", use_checkbox=False) 

    # --- TABLO BURADA ÇİZİLİYOR ---
    grid_response = AgGrid(
        res_df, 
        gridOptions=gb.build(), 
        # Update mode'dan MODEL_CHANGED'i sildik, sadece tıklama ve değer değişimini aldık
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
        theme='alpine', 
        allow_unsafe_jscode=True, 
        height=400,
        # KEY kısmını dinamik yaptık (Dosya ismine özel)
        key=f"grid_{pdf_file.name}", 
        reload_data=False,
        enable_enterprise_modules=True 
    )

    # ÖNEMLİ: Tablodaki manuel değişiklikleri (checkbox) session_state'e sessizce aktar
    # Bu kısım sadece 'Uzman Onayı' sütunu değiştiğinde state'i günceller
    if grid_response['data'] is not None:
        new_data = pd.DataFrame(grid_response['data'])
        st.session_state['final_results'] = new_data.to_dict('records')
        # Bu noktada st.rerun() kullanmıyoruz ki sayfa zıplamasın

    # Tablodaki değişiklikleri al
    updated_df = pd.DataFrame(grid_response['data'])
    st.session_state['final_results'] = updated_df.to_dict('records')

    # 4. Kaydetme ve Rapor Çıktısı (Mantıksal Kontrol)
    col_btn1, col_btn2 = st.columns([1, 1])
    
    # Tüm maddeler uzman tarafından onaylanmış mı?
    hepsi_onayli = updated_df['Uzman Onayı'].all() if not updated_df.empty else False

    with col_btn1:
        # 1. Şartname Hiyerarşisini (Sayfa 1 ve 3'e göre) Tanımla
        sartname_yapisi = [
            {
                "No": "1", 
                "Grup": "TRANSFORMATÖR KARAKTERİSTİK BİLGİLERİ", 
                "anahtar": ["Sargı", "Bağlantı", "Güç", "Gerilim", "Soğutma", "Boyut", "İzolatör", "Sac", "Plaka"]
            },
            {
                "No": "2", 
                "Grup": "RUTİN DENEYLER (TS EN 60076-1)", 
                "anahtar": ["Direnç", "Çevirme", "Vektör", "Yalıtım", "Kayıp", "Boşta", "Yükte", "Gerilim dayanım"]
            },
            {
                "No": "3", 
                "Grup": "SICAKLIK ARTIŞI DENEYİ (TS EN 60076-2)", 
                "anahtar": ["Yağ ısınması", "Sargı sıcaklık", "Isınma", "Kapatma", "Ortam", "Termokupl", "K-faktörü"]
            },
            {
                "No": "4", 
                "Grup": "ÖZEL VE TİP DENEYLER / MEKANİK KONTROLLER", 
                "anahtar": ["Sızdırmazlık", "Kazan", "Basınç", "Mekanik", "Boya", "Gürültü", "Kısa devre"]
            }
        ]

        formatted_rows = []
        header_rows = [] # Stil vermek için başlık satırlarını takip et

        # 2. Verileri Şartname Gruplarına Göre Dağıt
        for grup in sartname_yapisi:
            # Grup Başlığı Ekle
            header_rows.append(len(formatted_rows) + 2) 
            formatted_rows.append({
                "Madde No": grup["No"],
                "Denetim Parametresi": grup["Grup"],
                "Şartname Limiti": "", "Ölçülen Değer": "", "Sayfa": "", "Uzman Onayı": ""
            })
            
            sub_count = 1
            for _, row in updated_df.iterrows():
                # Ekranda (updated_df) olan satır hangi gruba aitse altına koy
                if any(k.lower() in str(row['parametre']).lower() for k in grup['anahtar']):
                    formatted_rows.append({
                        "Madde No": f"{grup['No']}.{sub_count}",
                        "Denetim Parametresi": row['parametre'],
                        "Şartname Limiti": row['limit'],
                        "Ölçülen Değer": row['olculen'],
                        "Sayfa": row['sayfa'],
                        "Uzman Onayı": "UYGUN" if row['Uzman Onayı'] else "UYGUN DEĞİL"
                    })
                    sub_count += 1

        # İmza ve Onay Bölümü
        formatted_rows.append({"Madde No": "", "Denetim Parametresi": "", "Şartname Limiti": "", "Ölçülen Değer": "", "Sayfa": "", "Uzman Onayı": ""})
        formatted_rows.append({
            "Madde No": "ONAY", 
            "Denetim Parametresi": "DENETİMİ GERÇEKLEŞTİREN UZMAN:", 
            "Şartname Limiti": "Özlem AKBOYRAZ",  
            "Sayfa": "", "Uzman Onayı": ""
        })

        report_df = pd.DataFrame(formatted_rows)

        # 3. Excel Yazma ve Görsel Biçimlendirme
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            report_df.to_excel(writer, index=False, sheet_name='Denetim_Raporu')
            worksheet = writer.sheets['Denetim_Raporu']
            
            from openpyxl.styles import Font, Alignment, PatternFill
            
            for row_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=worksheet.max_row), 1):
                for cell in row:
                    cell.alignment = Alignment(wrapText=True, vertical='center')
                    
                    # Ana Başlık Satırı (Tablo Başlığı)
                    if row_idx == 1:
                        cell.font = Font(bold=True, color="FFFFFF")
                        cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
                    
                    # Şartname Grup Başlıkları (1, 2, 3...)
                    elif row_idx in header_rows:
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")

            # Sütun Genişlikleri
            worksheet.column_dimensions['A'].width = 10
            worksheet.column_dimensions['B'].width = 45
            worksheet.column_dimensions['C'].width = 30
            worksheet.column_dimensions['D'].width = 30

        # Mavi Buton
        st.download_button(
            label="💾 UZMAN ONAYLI ŞARTNAME RAPORUNU İNDİR", 
            data=output.getvalue(), 
            file_name="Tedas_Denetim_Raporu_Final.xlsx", 
            mime="application/vnd.ms-excel", 
            use_container_width=True,
            type="primary"
        )
        
    # with col_btn2:
    #     # Uzman hepsini onaylamışsa buton pasif hale gelir (Disabled)
    #     if st.button("📌 Denetimi Sisteme Kaydet", use_container_width=True, disabled=hepsi_onayli):
    #         onay_sayisi = updated_df['Uzman Onayı'].sum()
    #         st.success(f"Kayıt Başarılı! {onay_sayisi} madde uzman tarafından onaylandı.")
    #         st.balloons()

    with col_btn2:
        if st.button("🔍 Yönetici Özetini Aç", use_container_width=True, type="primary"):
            show_summary_popup()

    st.divider()

    # 5. Detay ve PDF Kanıt Görüntüleme
    selected = grid_response['selected_rows']
    if selected is not None and len(selected) > 0:
        # AgGrid sürüm farkına göre seçili satırı al
        row = selected.iloc[0] if isinstance(selected, pd.DataFrame) else selected[0]
        kanit_metni = row.get('satir_kanit') or row.get('kanit') or row.get('metin') or "Kanıt metni bulunamadı."
        
        col_text, col_img = st.columns([1, 1])
        with col_text:
            st.markdown(f"""
                <div class="evidence-box">
                    <span class="tag-page">SAYFA {row['sayfa']}</span>
                    <h3 style="color:#1e293b;">{row['parametre']}</h3>
                    <p><b>🎯 Hedef Kriter:</b> {row['limit']}</p>
                    <p><b>📊 Ölçülen Değer:</b> {row['olculen']}</p>
                    <p><b>📝 Kanıt Metni:</b></p>
                    <div style="background:#f8faff; border-left:5px solid #4f86c3; padding:15px; font-style:italic;">
                        "{kanit_metni}"
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_img:
            p_idx = int(row['sayfa']) - 1
            if 0 <= p_idx < len(st.session_state.get('pdf_pages', [])):

                st.image(st.session_state['pdf_pages'][p_idx], use_container_width=True, caption=f"Sayfa Kanıtı: {row['sayfa']}")

