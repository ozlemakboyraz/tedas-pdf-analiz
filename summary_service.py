import pandas as pd
from openai import OpenAI

def get_audit_summary(api_key, results_df, spec_data):
    client = OpenAI(api_key=api_key)
    
    # --- GÜVENLİ SÜTUN SEÇİMİ ---
    # Kodun çökmemesi için olası tüm sütun isimlerini kontrol ediyoruz
    potential_cols = ['parametre', 'durum', 'teknik_not', 'teknik_sart', 'olculen', 'limit']
    existing_cols = [col for col in potential_cols if col in results_df.columns]
    
    # Sadece mevcut sütunları stringe çeviriyoruz
    results_summary = results_df[existing_cols].to_string(index=False)
    
    spec_preview = spec_data[:2000]

    prompt = f"""
    Sen, TEDAŞ projelerinde görevli Kıdemli bir Denetim ve Kabul Mühendisisin. 
    Görevin; sunulan şartname ile test sonuçlarını bütüncül bir şekilde değerlendirmektir.

    GİRDİLER:
    1. Şartname (Excel) Beklentileri: {spec_preview}
    2. Denetim Bulguları (PDF Analizi): {results_summary}

    TALİMATLAR:
    - [FIRMA_ISMI]: PDF verilerinden üretici/firma adını tespit et.
    - [OZET_METNI]: Teknik dili güçlü, 2-3 kısa paragraftan oluşan bir değerlendirme yaz:
        * Cihazın genel karakteristiği şartnameye ne kadar uyumlu?
        * Ölçülen değerlerdeki sapmalar cihaz ömrü ve işletme güvenliği için ne ifade ediyor?
        * Kritik uygunsuzluklar varsa teknik risklerini vurgula.
    
    NOT: Kesinlikle "Sonuç", "Giriş" gibi başlıklar kullanma. Maddeler halinde değil, akıcı bir rapor dili kullan.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Özet oluşturulurken hata: {str(e)}"