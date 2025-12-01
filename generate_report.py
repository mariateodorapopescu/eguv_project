"""
GENERATOR RAPORT AUTOMAT - Tema 2 de laborator eGovernment
Genereaza raport PDF cu grafice din datele MongoDB
Cerinte:
- Document de raportare automat
- Date relevante analizate + GRAFICE
- Cel putin 2 tipuri de date din baza de date
- Minimum 10 inregistrari
- 6 grafice + statistici detaliate
"""
"""
GENERATOR RAPORT AUTOMAT - Tema 2 de laborator eGovernment
Genereaza raport PDF cu grafice din datele MongoDB
Cerinte:
- Document de raportare automat
- Date relevante analizate + GRAFICE
- Cel putin 2 tipuri de date din baza de date
- Minimum 10 inregistrari
- 6 grafice + statistici detaliate
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from collections import defaultdict
import os

# Matplotlib pentru grafice
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ReportLab pentru PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib import colors

# Conectare MongoDB Atlas
MONGO_URI = "mongodb+srv://root:student@cluster0.oyzbfhf.mongodb.net/proiect_metrorex?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

client = MongoClient(MONGO_URI)
db = client.proiect_metrorex

# Folder output
OUTPUT_DIR = "generated_files"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Nume produse
NUME_PRODUSE = {
    'bilet_1_calatorii': 'Bilet 1 calatorie',
    'bilet_2_calatorii': 'Bilet 2 calatorii',
    'bilet_10_calatorii': 'Bilet 10 calatorii',
    'bilet_19_calatorii_s': 'Bilet 19 cal. (studenti)',
    'abonament_24': 'Abonament 24h',
    'abonament_72': 'Abonament 72h',
    'abonament_saptamanal': 'Abonament saptamanal',
    'abonament_lunar': 'Abonament lunar',
    'abonament_lunar_elev': 'Abonament lunar elevi',
    'abonament_6l': 'Abonament 6 luni',
    'abonament_anual': 'Abonament anual',
    'abonament_donatori': 'Abonament donatori',
}

ZILE_SAPTAMANA = ['Luni', 'Marti', 'Miercuri', 'Joi', 'Vineri', 'Sambata', 'Duminica']

def get_data():
    """Extrage comenzile din MongoDB"""
    comenzi = list(db.comenzi.find({}))
    print(f"Total comenzi: {len(comenzi)}")
    return comenzi

def analyze_data(comenzi):
    """Analizeaza datele - statistici extinse"""
    stats = {
        'total_comenzi': len(comenzi),
        'total_vanzari': 0,
        'total_tva': 0,
        'total_subtotal': 0,
        'produse': {},
        'metode_plata': {},
        'bilete_vs_abonamente': {'bilete': 0, 'abonamente': 0},
        'vanzari_per_produs': {},
        'cantitate_per_produs': {},
        'comenzi_per_zi': defaultdict(int),
        'vanzari_per_zi': defaultdict(float),
        'cantitati': [],
        'valori_comenzi': [],
    }
    
    for c in comenzi:
        # Valori financiare
        total = float(c.get('total', 0)) if c.get('total') else 0
        tva = float(c.get('tva', 0)) if c.get('tva') else 0
        subtotal = float(c.get('subtotal', 0)) if c.get('subtotal') else 0
        cantitate = int(c.get('cantitate', 1)) if c.get('cantitate') else 1
        
        stats['total_vanzari'] += total
        stats['total_tva'] += tva
        stats['total_subtotal'] += subtotal
        stats['valori_comenzi'].append(total)
        stats['cantitati'].append(cantitate)
        
        # Per produs
        tip = c.get('tip_produs', 'necunoscut')
        stats['produse'][tip] = stats['produse'].get(tip, 0) + 1
        stats['vanzari_per_produs'][tip] = stats['vanzari_per_produs'].get(tip, 0) + total
        stats['cantitate_per_produs'][tip] = stats['cantitate_per_produs'].get(tip, 0) + cantitate
        
        # Bilete vs Abonamente
        if 'bilet' in tip:
            stats['bilete_vs_abonamente']['bilete'] += 1
        else:
            stats['bilete_vs_abonamente']['abonamente'] += 1
        
        # Per metoda plata
        metoda = c.get('metoda_plata', 'necunoscut')
        stats['metode_plata'][metoda] = stats['metode_plata'].get(metoda, 0) + 1
        
        # Per zi a saptamanii
        data_comanda = c.get('data_comanda')
        if data_comanda:
            try:
                if isinstance(data_comanda, str):
                    dt = datetime.fromisoformat(data_comanda.replace('Z', '+00:00'))
                else:
                    dt = data_comanda
                zi = dt.weekday()  # 0=Luni, 6=Duminica
                stats['comenzi_per_zi'][zi] += 1
                stats['vanzari_per_zi'][zi] += total
            except:
                pass
    
    # Calcule suplimentare
    if stats['valori_comenzi']:
        stats['media_comanda'] = np.mean(stats['valori_comenzi'])
        stats['mediana_comanda'] = np.median(stats['valori_comenzi'])
        stats['max_comanda'] = max(stats['valori_comenzi'])
        stats['min_comanda'] = min(stats['valori_comenzi'])
        stats['std_comanda'] = np.std(stats['valori_comenzi'])
    else:
        stats['media_comanda'] = 0
        stats['mediana_comanda'] = 0
        stats['max_comanda'] = 0
        stats['min_comanda'] = 0
        stats['std_comanda'] = 0
    
    if stats['cantitati']:
        stats['media_cantitate'] = np.mean(stats['cantitati'])
        stats['total_produse_vandute'] = sum(stats['cantitati'])
    else:
        stats['media_cantitate'] = 0
        stats['total_produse_vandute'] = 0
    
    return stats

# ============================================================
# GRAFICE
# ============================================================

def create_chart_bilete_abonamente(stats):
    """Grafic 1: Pie chart - Bilete vs Abonamente"""
    labels = ['Bilete', 'Abonamente']
    sizes = [
        stats['bilete_vs_abonamente']['bilete'],
        stats['bilete_vs_abonamente']['abonamente']
    ]
    
    fig, ax = plt.subplots(figsize=(6, 5))
    colors_bw = ['#CCCCCC', '#666666']
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors_bw,
        autopct='%1.1f%%', startangle=90,
        wedgeprops={'edgecolor': 'black', 'linewidth': 1}
    )
    
    for autotext in autotexts:
        autotext.set_fontsize(11)
        autotext.set_fontweight('bold')
    
    ax.set_title('Figura 1. Distributia comenzilor: Bilete vs Abonamente',
                 fontsize=11, fontname='serif', style='italic')
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'grafic1_bilete_abonamente.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"- {path}")
    return path

def create_chart_metode_plata(stats):
    """Grafic 2: Bar chart - Metode de plata"""
    metode = list(stats['metode_plata'].keys())
    valori = list(stats['metode_plata'].values())
    
    traducere = {'card': 'Card Bancar', 'cash': 'Numerar', 'transfer': 'Transfer'}
    metode_ro = [traducere.get(m, m) for m in metode]
    
    fig, ax = plt.subplots(figsize=(6, 4))
    patterns = ['///', '...', 'xxx', '\\\\\\']
    bars = ax.bar(metode_ro, valori, color='white', edgecolor='black', linewidth=1.5)
    
    for bar, pattern in zip(bars, patterns[:len(bars)]):
        bar.set_hatch(pattern)
    
    ax.set_xlabel('Metoda de plata', fontsize=10, fontname='serif')
    ax.set_ylabel('Numar comenzi', fontsize=10, fontname='serif')
    ax.set_title('Figura 2. Distributia pe metode de plata',
                 fontsize=11, fontname='serif', style='italic')
    
    for bar, val in zip(bars, valori):
        ax.annotate(f'{val}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', fontsize=10, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'grafic2_metode_plata.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"- {path}")
    return path

def create_chart_top_produse(stats):
    """Grafic 3: Horizontal bar - Top produse vandute"""
    # Sorteaza dupa numar comenzi
    produse_sorted = sorted(stats['produse'].items(), key=lambda x: x[1], reverse=True)[:7]
    
    produse = [NUME_PRODUSE.get(p[0], p[0]) for p in produse_sorted]
    valori = [p[1] for p in produse_sorted]
    
    fig, ax = plt.subplots(figsize=(7, 5))
    
    y_pos = np.arange(len(produse))
    patterns = ['///', '...', 'xxx', '\\\\\\', '+++', 'ooo', '---']
    
    bars = ax.barh(y_pos, valori, color='white', edgecolor='black', linewidth=1)
    for bar, pattern in zip(bars, patterns):
        bar.set_hatch(pattern)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(produse, fontsize=9)
    ax.set_xlabel('Numar comenzi', fontsize=10, fontname='serif')
    ax.set_title('Figura 3. Top produse dupa numarul de comenzi',
                 fontsize=11, fontname='serif', style='italic')
    
    for i, (bar, val) in enumerate(zip(bars, valori)):
        ax.annotate(f'{val}', xy=(bar.get_width(), bar.get_y() + bar.get_height()/2),
                    xytext=(3, 0), textcoords="offset points",
                    ha='left', va='center', fontsize=9, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'grafic3_top_produse.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"- {path}")
    return path

def create_chart_vanzari_produse(stats):
    """Grafic 4: Bar chart - Vanzari (RON) per produs"""
    # Sorteaza dupa valoare vanzari
    vanzari_sorted = sorted(stats['vanzari_per_produs'].items(), key=lambda x: x[1], reverse=True)[:7]
    
    produse = [NUME_PRODUSE.get(p[0], p[0]) for p in vanzari_sorted]
    valori = [p[1] for p in vanzari_sorted]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    x_pos = np.arange(len(produse))
    bars = ax.bar(x_pos, valori, color='#888888', edgecolor='black', linewidth=1)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(produse, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Vanzari (RON)', fontsize=10, fontname='serif')
    ax.set_title('Figura 4. Venituri generate per tip de produs',
                 fontsize=11, fontname='serif', style='italic')
    
    for bar, val in zip(bars, valori):
        ax.annotate(f'{val:.0f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', fontsize=8, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'grafic4_vanzari_produse.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"- {path}")
    return path

def create_chart_comenzi_zile(stats):
    """Grafic 5: Bar chart - Comenzi pe zile ale saptamanii"""
    zile = ZILE_SAPTAMANA
    valori = [stats['comenzi_per_zi'].get(i, 0) for i in range(7)]
    
    fig, ax = plt.subplots(figsize=(7, 4))
    
    x_pos = np.arange(len(zile))
    bars = ax.bar(x_pos, valori, color='white', edgecolor='black', linewidth=1.5, hatch='///')
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(zile, fontsize=9)
    ax.set_ylabel('Numar comenzi', fontsize=10, fontname='serif')
    ax.set_title('Figura 5. Distributia comenzilor pe zilele saptamanii',
                 fontsize=11, fontname='serif', style='italic')
    
    for bar, val in zip(bars, valori):
        if val > 0:
            ax.annotate(f'{val}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', fontsize=9, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'grafic5_comenzi_zile.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"- {path}")
    return path

def create_chart_distributie_valori(stats):
    """Grafic 6: Histograma - Distributia valorilor comenzilor"""
    valori = stats['valori_comenzi']
    
    fig, ax = plt.subplots(figsize=(7, 4))
    
    n, bins, patches = ax.hist(valori, bins=10, color='#AAAAAA', edgecolor='black', linewidth=1)
    
    ax.set_xlabel('Valoare comanda (RON)', fontsize=10, fontname='serif')
    ax.set_ylabel('Frecventa', fontsize=10, fontname='serif')
    ax.set_title('Figura 6. Distributia valorilor comenzilor',
                 fontsize=11, fontname='serif', style='italic')
    
    # Adauga linie pentru medie
    media = stats['media_comanda']
    ax.axvline(media, color='black', linestyle='--', linewidth=2, label=f'Media: {media:.1f} RON')
    ax.legend(loc='upper right', fontsize=9)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'grafic6_distributie_valori.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"- {path}")
    return path

# ============================================================
# GENERARE PDF
# ============================================================

def generate_pdf_report(stats, charts):
    """Genereaza PDF format academic extins"""
    
    pdf_path = os.path.join(OUTPUT_DIR, 'raport_metrorex.pdf')
    
    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    
    # Stiluri
    styles = getSampleStyleSheet()
    
    style_normal = ParagraphStyle(
        'Normal_TNR', fontName='Times-Roman', fontSize=12,
        leading=18, alignment=TA_JUSTIFY, spaceAfter=12
    )
    
    style_title = ParagraphStyle(
        'Title_TNR', fontName='Times-Bold', fontSize=14,
        leading=21, alignment=TA_CENTER, spaceAfter=24
    )
    
    style_heading = ParagraphStyle(
        'Heading_TNR', fontName='Times-Bold', fontSize=12,
        leading=18, alignment=TA_LEFT, spaceBefore=18, spaceAfter=12
    )
    
    style_italic = ParagraphStyle(
        'Italic_TNR', fontName='Times-Italic', fontSize=12,
        leading=18, alignment=TA_CENTER
    )
    
    content = []
    
    # ==================== TITLU ====================
    content.append(Paragraph("RAPORT DE ANALIZA", style_title))
    content.append(Paragraph("Sistemul Electronic de Achizitie Bilete si Abonamente Metrorex", style_title))
    content.append(Spacer(1, 6))
    
    # ==================== 1. INTRODUCERE ====================
    content.append(Paragraph("1. Introducere", style_heading))
    
    intro = """Prezentul raport analizeaza datele colectate prin sistemul electronic de achizitie 
    bilete si abonamente Metrorex. 
    Documentul prezinta o analiza detaliata a comenzilor inregistrate, incluzand statistici 
    privind tipurile de produse achizitionate, metodele de plata utilizate, distributia 
    temporala a comenzilor si analiza valorilor tranzactiilor."""
    content.append(Paragraph(intro, style_normal))
    
    # ==================== 2. STATISTICI GENERALE ====================
    content.append(Paragraph("2. Statistici generale", style_heading))
    
    stats_text = f"""In perioada analizata, sistemul a inregistrat un numar total de 
    <b>{stats['total_comenzi']}</b> comenzi, corespunzand unui numar de 
    <b>{stats['total_produse_vandute']}</b> produse vandute. Valoarea totala a vanzarilor 
    este de <b>{stats['total_vanzari']:.2f} RON</b>, din care TVA-ul colectat reprezinta 
    <b>{stats['total_tva']:.2f} RON</b> (19%)."""
    content.append(Paragraph(stats_text, style_normal))
    
    # Tabel statistici generale
    content.append(Paragraph("<i>Tabelul 1. Indicatori statistici principali</i>", style_italic))
    content.append(Spacer(1, 6))
    
    table1_data = [
        ['Indicator', 'Valoare'],
        ['Total comenzi', f'{stats["total_comenzi"]}'],
        ['Total produse vandute', f'{stats["total_produse_vandute"]}'],
        ['Valoare totala vanzari', f'{stats["total_vanzari"]:.2f} RON'],
        ['TVA colectat', f'{stats["total_tva"]:.2f} RON'],
        ['Valoare medie comanda', f'{stats["media_comanda"]:.2f} RON'],
        ['Valoare mediana comanda', f'{stats["mediana_comanda"]:.2f} RON'],
        ['Comanda minima', f'{stats["min_comanda"]:.2f} RON'],
        ['Comanda maxima', f'{stats["max_comanda"]:.2f} RON'],
        ['Deviatia standard', f'{stats["std_comanda"]:.2f} RON'],
        ['Cantitate medie/comanda', f'{stats["media_cantitate"]:.1f} produse'],
    ]
    
    table1 = Table(table1_data, colWidths=[8*cm, 5*cm])
    table1.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    content.append(table1)
    content.append(Spacer(1, 12))
    
    # ==================== 3. ANALIZA BILETE VS ABONAMENTE ====================
    content.append(Paragraph("3. Analiza categoriilor de produse: Bilete vs Abonamente", style_heading))
    
    bilete = stats['bilete_vs_abonamente']['bilete']
    abonamente = stats['bilete_vs_abonamente']['abonamente']
    total = bilete + abonamente
    pct_bilete = (bilete / total * 100) if total > 0 else 0
    pct_abonamente = (abonamente / total * 100) if total > 0 else 0
    
    # Tabel bilete vs abonamente
    content.append(Paragraph("<i>Tabelul 2. Distributia comenzilor pe categorii</i>", style_italic))
    content.append(Spacer(1, 6))
    
    table2_data = [
        ['Categorie', 'Numar comenzi', 'Procent'],
        ['Bilete', str(bilete), f'{pct_bilete:.1f}%'],
        ['Abonamente', str(abonamente), f'{pct_abonamente:.1f}%'],
        ['Total', str(total), '100%'],
    ]
    
    table2 = Table(table2_data, colWidths=[5*cm, 4*cm, 4*cm])
    table2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Times-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    content.append(table2)
    content.append(Spacer(1, 12))
    
    if pct_bilete > pct_abonamente:
        analiza1 = f"""Din analiza datelor reiese ca biletele reprezinta categoria dominanta, 
        cu un procent de {pct_bilete:.1f}% din totalul comenzilor ({bilete} comenzi). 
        Aceasta distributie indica faptul ca o mare parte a calatorilor utilizeaza metroul 
        ocazional, preferand achizitionarea de bilete individuale."""
    else:
        analiza1 = f"""Din analiza datelor reiese ca abonamentele reprezinta categoria dominanta, 
        cu un procent de {pct_abonamente:.1f}% din totalul comenzilor ({abonamente} comenzi). 
        Aceasta distributie indica o baza stabila de calatori frecventi care prefera 
        abonamentele pentru eficienta costurilor."""
    content.append(Paragraph(analiza1, style_normal))
    
    # Grafic 1
    content.append(Spacer(1, 6))
    content.append(Image(charts['bilete_abonamente'], width=11*cm, height=9*cm))
    content.append(Spacer(1, 12))
    
    # ==================== 4. ANALIZA METODE DE PLATA ====================
    content.append(PageBreak())
    content.append(Paragraph("4. Analiza metodelor de plata", style_heading))
    
    traducere = {'card': 'card bancar', 'cash': 'numerar', 'transfer': 'transfer bancar'}
    metoda_preferata = max(stats['metode_plata'].items(), key=lambda x: x[1])
    pct_metoda = (metoda_preferata[1] / stats['total_comenzi'] * 100) if stats['total_comenzi'] > 0 else 0
    
    # Tabel metode plata
    content.append(Paragraph("<i>Tabelul 3. Distributia comenzilor pe metode de plata</i>", style_italic))
    content.append(Spacer(1, 6))
    
    table3_data = [['Metoda de plata', 'Numar comenzi', 'Procent']]
    for metoda, count in sorted(stats['metode_plata'].items(), key=lambda x: -x[1]):
        pct = (count / stats['total_comenzi'] * 100) if stats['total_comenzi'] > 0 else 0
        table3_data.append([traducere.get(metoda, metoda).title(), str(count), f'{pct:.1f}%'])
    
    table3 = Table(table3_data, colWidths=[5*cm, 4*cm, 4*cm])
    table3.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    content.append(table3)
    content.append(Spacer(1, 12))
    
    analiza2 = f"""Analiza metodelor de plata arata ca metoda preferata este 
    <b>{traducere.get(metoda_preferata[0], metoda_preferata[0])}</b>, utilizata in 
    {pct_metoda:.1f}% din tranzactii ({metoda_preferata[1]} comenzi). Aceasta preferinta 
    reflecta tendinta generala de digitalizare a platilor si adoptarea pe scara larga 
    a solutiilor electronice de plata."""
    content.append(Paragraph(analiza2, style_normal))
    
    # Grafic 2
    content.append(Image(charts['metode_plata'], width=11*cm, height=7*cm))
    content.append(Spacer(1, 12))
    
    # ==================== 5. ANALIZA PRODUSE ====================
    content.append(Paragraph("5. Analiza detaliata a produselor", style_heading))
    
    # Top produs
    top_produs = max(stats['produse'].items(), key=lambda x: x[1])
    pct_top = (top_produs[1] / stats['total_comenzi'] * 100) if stats['total_comenzi'] > 0 else 0
    
    analiza3 = f"""Cel mai vandut produs este <b>{NUME_PRODUSE.get(top_produs[0], top_produs[0])}</b>, 
    cu {top_produs[1]} comenzi ({pct_top:.1f}% din total). Graficul de mai jos prezinta 
    ierarhia produselor in functie de numarul de comenzi."""
    content.append(Paragraph(analiza3, style_normal))
    
    # Grafic 3 - Top produse
    content.append(Image(charts['top_produse'], width=12*cm, height=8*cm))
    content.append(Spacer(1, 12))
    
    # Analiza venituri per produs
    top_venit = max(stats['vanzari_per_produs'].items(), key=lambda x: x[1])
    
    analiza4 = f"""Din perspectiva veniturilor generate, produsul cu cele mai mari incasari este 
    <b>{NUME_PRODUSE.get(top_venit[0], top_venit[0])}</b>, cu vanzari totale de 
    <b>{top_venit[1]:.2f} RON</b>."""
    content.append(Paragraph(analiza4, style_normal))
    
    # Grafic 4 - Vanzari per produs
    content.append(Image(charts['vanzari_produse'], width=13*cm, height=8*cm))
    
    # ==================== 6. ANALIZA TEMPORALA ====================
    content.append(PageBreak())
    content.append(Paragraph("6. Analiza distributiei temporale", style_heading))
    
    # Ziua cu cele mai multe comenzi
    if stats['comenzi_per_zi']:
        zi_max = max(stats['comenzi_per_zi'].items(), key=lambda x: x[1])
        zi_min = min(stats['comenzi_per_zi'].items(), key=lambda x: x[1])
        
        analiza5 = f"""Analiza distributiei comenzilor pe zilele saptamanii releva faptul ca 
        cea mai aglomerata zi este <b>{ZILE_SAPTAMANA[zi_max[0]]}</b> cu {zi_max[1]} comenzi, 
        in timp ce <b>{ZILE_SAPTAMANA[zi_min[0]]}</b> inregistreaza cel mai mic numar de comenzi 
        ({zi_min[1]}). Aceasta distributie poate fi utilizata pentru optimizarea resurselor 
        si planificarea capacitatii sistemului."""
    else:
        analiza5 = """Nu sunt suficiente date pentru analiza distributiei temporale."""
    content.append(Paragraph(analiza5, style_normal))
    
    # Grafic 5 - Comenzi pe zile
    content.append(Image(charts['comenzi_zile'], width=12*cm, height=7*cm))
    content.append(Spacer(1, 12))
    
    # ==================== 7. ANALIZA VALORILOR ====================
    content.append(Paragraph("7. Analiza distributiei valorilor comenzilor", style_heading))
    
    analiza6 = f"""Valoarea medie a unei comenzi este de <b>{stats['media_comanda']:.2f} RON</b>, 
    cu o mediana de <b>{stats['mediana_comanda']:.2f} RON</b>. Valorile comenzilor variaza 
    intre <b>{stats['min_comanda']:.2f} RON</b> (minim) si <b>{stats['max_comanda']:.2f} RON</b> 
    (maxim), cu o deviatie standard de <b>{stats['std_comanda']:.2f} RON</b>. Histograma 
    de mai jos ilustreaza distributia valorilor comenzilor."""
    content.append(Paragraph(analiza6, style_normal))
    
    # Grafic 6 - Distributie valori
    content.append(Image(charts['distributie_valori'], width=12*cm, height=7*cm))
    content.append(Spacer(1, 12))
    
    # ==================== 8. CONCLUZII ====================
    content.append(PageBreak())
    content.append(Paragraph("8. Concluzii", style_heading))
    
    content.append(Paragraph("""In urma analizei datelor colectate prin sistemul electronic 
    de achizitie bilete si abonamente Metrorex, se pot formula urmatoarele concluzii:""", style_normal))
    
    concluzii = [
        f"""<b>a)</b> Sistemul a procesat cu succes {stats['total_comenzi']} comenzi, 
        generand venituri totale de {stats['total_vanzari']:.2f} RON, din care 
        {stats['total_tva']:.2f} RON reprezinta TVA colectat.""",
        
        f"""<b>b)</b> {'Biletele' if pct_bilete > pct_abonamente else 'Abonamentele'} 
        reprezinta categoria dominanta ({max(pct_bilete, pct_abonamente):.1f}%), 
        indicand {'un numar semnificativ de calatori ocazionali' if pct_bilete > pct_abonamente 
        else 'o baza stabila de utilizatori frecventi'}.""",
        
        f"""<b>c)</b> Metoda de plata preferata este {traducere.get(metoda_preferata[0], 
        metoda_preferata[0])} ({pct_metoda:.1f}%), demonstrand adoptarea solutiilor 
        electronice de plata.""",
        
        f"""<b>d)</b> Produsul cel mai solicitat este {NUME_PRODUSE.get(top_produs[0], 
        top_produs[0])}, reprezentand {pct_top:.1f}% din comenzi.""",
        
        f"""<b>e)</b> Valoarea medie a comenzilor ({stats['media_comanda']:.2f} RON) si 
        dispersia valorilor indica un mix echilibrat de achizitii mici si mari.""",
    ]
    
    for c in concluzii:
        content.append(Paragraph(c, style_normal))
    
    # ==================== FOOTER ====================
    content.append(Spacer(1, 30))
    content.append(Paragraph("_" * 60, style_normal))
    footer = f"""<i>Raport generat automat<br/>
    Data: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"""
    content.append(Paragraph(footer, style_italic))
    
    # Build PDF
    doc.build(content)
    return pdf_path

# ============================================================
# MAIN
# ============================================================

def main():
    # 1. Extrage date
    comenzi = get_data()
    
    if len(comenzi) < 10:
        print(f"\nExista numai {len(comenzi)} comenzi, ceea ce este insuficient pentru o analiza riguroasa a datelor.\nA se rula mai intai: python3 generate_test_data.py")
    
    # 2. Analizeaza
    stats = analyze_data(comenzi)
    
    # 3. Grafice
    charts = {
        'bilete_abonamente': create_chart_bilete_abonamente(stats),
        'metode_plata': create_chart_metode_plata(stats),
        'top_produse': create_chart_top_produse(stats),
        'vanzari_produse': create_chart_vanzari_produse(stats),
        'comenzi_zile': create_chart_comenzi_zile(stats),
        'distributie_valori': create_chart_distributie_valori(stats),
    }
    
    # 4. PDF
    pdf_path = generate_pdf_report(stats, charts)
    
    for name, path in charts.items():
        print(f"- {path}")
    print(f"- {pdf_path}")

if __name__ == '__main__':
    main()