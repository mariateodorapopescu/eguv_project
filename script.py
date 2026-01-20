"""
================================================================================
PAP CRAWLER RECURSIV - Colector Avansat de Planuri de Achizitii Publice
================================================================================
Autor: Pentru LAB 3 - eGovernment 2025-2026
Descriere: Crawler RECURSIV care exploreaza automat site-urile guvernamentale,
           descopera noi pagini si colecteaza toate documentele PAP

Ce face:
- Porneste de la 4 URL-uri de baza
- Exploreaza RECURSIV toate link-urile din fiecare site
- Descopera automat pagini noi cu documente
- Descarca efectiv PDF-urile gasite (optional)

Librarii necesare:
    pip install requests beautifulsoup4

================================================================================
"""

# ============================================================================
# IMPORTURI
# ============================================================================

import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin
import os
import time
import urllib3
import webbrowser
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Dezactivez warning-urile SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# CONFIGURARE CRAWLER
# ============================================================================

# Headers pentru request-uri
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7',
}

# Site-urile de pornire (seed URLs)
SITE_URI_START = [
    {
        'nume': 'Ministerul Afacerilor Interne (MAI)',
        'url': 'https://www.mai.gov.ro/informatii-publice/achizitii-publice/',
    },
    {
        'nume': 'Agentia Nationala pentru Achizitii Publice (ANAP)',
        'url': 'https://anap.gov.ro/web/achizitii/',
    },
    {
        'nume': 'Inspectoratul de Stat in Constructii (ISC)',
        'url': 'https://isc.gov.ro/program_achizitii.html',
    },
    {
        'nume': 'Ministerul Economiei',
        'url': 'https://economie.gov.ro/transparenta-institutionala/achizitii-publice/',
    }
]

# Configurare crawling - OPTIMIZAT PENTRU VITEZA
CONFIG = {
    'max_pagini_total': 0,           # 0 = fara limita, continua pana se goleste coada
    'max_adancime': 10,
    'timeout': 5,
    'retry_count': 1,
    'descarca_pdf': False,
    'folder_download': 'documente_pap',
    'permite_alte_domenii': True,
    'domenii_permise': ['.gov.ro'],
    'thread_workers': 15,
    'batch_size': 30,
}

# Cuvinte cheie pentru filtrarea documentelor PAP (STRICT!)
# Documentul trebuie sa contina cel putin una din aceste combinatii
KEYWORDS_PAP_OBLIGATORII = [
    'paap',
    'plan anual al achizitiilor',
    'plan anual al achiziţiilor',
    'planul anual al achizitiilor',
    'planul anual al achiziţiilor',
    'program anual al achizitiilor',
    'program anual al achiziţiilor',
    'programul anual al achizitiilor',
    'programul anual al achiziţiilor',
    'plan anual achizitii',
    'plan anual achiziţii',
    'program anual achizitii',
    'program anual achiziţii',
    'strategia anuala de achizitii',
    'strategia anuală de achiziții',
]

# Cuvinte cheie secundare - documentul trebuie sa contina "achizi" + unul din acestea
KEYWORDS_PAP_SECUNDARE = [
    'plan anual',
    'program anual', 
    'planul anual',
    'programul anual',
    'strategie anuala',
    'strategie anuală',
]

# Cuvinte de EXCLUS - daca contine acestea, NU e PAP
KEYWORDS_EXCLUDE = [
    'formular',
    'cerere',
    'cv ',
    'curriculum',
    'declaratie',
    'declarație', 
    'raport activitate',
    'organigrama',
    'regulament',
    'hotarare',
    'hotărâre',
    'ordin ',
    'lege ',
    'comunicat',
    'anunt angajare',
    'anunț angajare',
    'concurs',
    'examen',
    'rezultate concurs',
]

# Cuvinte cheie pentru filtrarea paginilor relevante
KEYWORDS_PAGINI = [
    'achizi', 'licitati', 'licitați', 'transparenta', 'transparență',
    'public', 'program', 'anual', 'paap'
]


# ============================================================================
# CLASA CRAWLER RECURSIV
# ============================================================================

class CrawlerRecursiv:
    """
    Crawler care exploreaza recursiv site-urile si colecteaza documente PAP.
    Poate explora link-uri catre alte domenii .gov.ro!
    """
    
    def __init__(self):
        """Initializeaza crawler-ul."""
        self.pagini_vizitate = set()
        self.url_in_coada = set()  # URL-uri deja in coada (pentru a evita duplicate)
        self.documente_gasite = []
        self.domenii_descoperite = set()
        self.statistici = {
            'pagini_scanate': 0,
            'erori': 0,
            'pdf_gasite': 0,
            'domenii_explorate': set()
        }
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=CONFIG.get('retry_count', 1)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def domeniu_permis(self, url):
        """Verifica daca un URL apartine unui domeniu permis."""
        try:
            parsed = urlparse(url)
            domeniu = parsed.netloc.lower()
            
            if not CONFIG['permite_alte_domenii']:
                domenii_start = [self.extrage_domeniu(site['url']) for site in SITE_URI_START]
                return domeniu in domenii_start
            
            for permis in CONFIG['domenii_permise']:
                if permis in domeniu:
                    return True
            return False
        except:
            return False
    
    def extrage_domeniu(self, url):
        """Extrage domeniul dintr-un URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ''
    
    def descarca_pagina(self, url):
        """Descarca continutul HTML al unei pagini."""
        try:
            raspuns = self.session.get(
                url, 
                timeout=CONFIG['timeout'], 
                verify=False,
                allow_redirects=True
            )
            raspuns.raise_for_status()
            raspuns.encoding = raspuns.apparent_encoding
            return raspuns.text
            
        except Exception as e:
            with self.lock:
                self.statistici['erori'] += 1
            return None
    
    def extrage_linkuri(self, html, url_baza):
        """Extrage link-urile din HTML."""
        linkuri_pagini = []
        linkuri_pdf = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
        except:
            return [], []
        
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            if href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            try:
                url_absolut = urljoin(url_baza, href)
            except:
                continue
            
            parsed = urlparse(url_absolut)
            domeniu = parsed.netloc.lower()
            
            if not self.domeniu_permis(url_absolut):
                continue
            
            # Verific daca e PDF
            if href.lower().endswith('.pdf'):
                nume = link.get_text(strip=True)
                if not nume:
                    nume = href.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ')
                
                # Verific daca e relevant pentru PAP (STRICT!)
                text_verificare = (nume + ' ' + url_absolut).lower()
                
                # Verific daca contine cuvinte de exclus
                e_exclus = any(excl in text_verificare for excl in KEYWORDS_EXCLUDE)
                if e_exclus:
                    continue
                
                # Verific daca contine keywords obligatorii
                e_pap_obligatoriu = any(kw in text_verificare for kw in KEYWORDS_PAP_OBLIGATORII)
                
                # SAU verific daca contine "achizi" + keywords secundare
                contine_achizi = 'achizi' in text_verificare
                contine_secundar = any(kw in text_verificare for kw in KEYWORDS_PAP_SECUNDARE)
                e_pap_secundar = contine_achizi and contine_secundar
                
                if e_pap_obligatoriu or e_pap_secundar:
                    linkuri_pdf.append({
                        'nume': nume,
                        'link': url_absolut,
                        'domeniu': domeniu
                    })
            else:
                # E pagina HTML - verific daca pare relevanta
                text_link = (link.get_text(strip=True) + ' ' + url_absolut).lower()
                
                if any(kw in text_link for kw in KEYWORDS_PAGINI):
                    linkuri_pagini.append({
                        'url': url_absolut,
                        'domeniu': domeniu
                    })
        
        return linkuri_pagini, linkuri_pdf
    
    def proceseaza_url(self, url_info):
        """Proceseaza un singur URL (pentru threading)."""
        url, adancime, sursa = url_info
        
        html = self.descarca_pagina(url)
        if not html:
            return None
        
        domeniu_curent = self.extrage_domeniu(url)
        linkuri_pagini, linkuri_pdf = self.extrage_linkuri(html, url)
        
        return {
            'url': url,
            'adancime': adancime,
            'sursa': sursa,
            'domeniu': domeniu_curent,
            'linkuri_pagini': linkuri_pagini,
            'linkuri_pdf': linkuri_pdf
        }
    
    def crawl(self):
        """Crawleaza recursiv cu MULTITHREADING pana se goleste coada."""
        timp_start = time.time()
        
        limita = CONFIG['max_pagini_total']
        are_limita = limita > 0
        
        print("")
        print("=" * 70)
        print("PORNESC CRAWLING-UL RECURSIV PARALEL")
        print("=" * 70)
        print(f"Site-uri de start: {len(SITE_URI_START)}")
        if are_limita:
            print(f"Limita pagini: {limita}")
        else:
            print("Limita pagini: FARA (continui pana se goleste coada)")
        print(f"Adancime maxima: {CONFIG['max_adancime']}")
        print(f"Thread-uri paralele: {CONFIG.get('thread_workers', 10)}")
        print(f"Explorare cross-domain: {'DA' if CONFIG['permite_alte_domenii'] else 'NU'}")
        print("=" * 70)
        print("")
        
        coada = []
        for site in SITE_URI_START:
            url = site['url']
            coada.append((url, 0, site['nume']))
            self.url_in_coada.add(url)
            domeniu = self.extrage_domeniu(url)
            self.statistici['domenii_explorate'].add(domeniu)
            self.domenii_descoperite.add(domeniu)
        
        pagini_scanate = 0
        workers = CONFIG.get('thread_workers', 10)
        
        # Continui cat timp am URL-uri in coada
        while coada:
            # Verific limita daca exista
            if are_limita and pagini_scanate >= limita:
                break
            
            # Calculez dimensiunea batch-ului
            if are_limita:
                batch_size = min(CONFIG.get('batch_size', 20), len(coada), limita - pagini_scanate)
            else:
                batch_size = min(CONFIG.get('batch_size', 20), len(coada))
            
            batch = []
            
            while len(batch) < batch_size and coada:
                url_info = coada.pop(0)
                url = url_info[0]
                adancime = url_info[1]
                
                # Scot din set-ul de coada
                with self.lock:
                    self.url_in_coada.discard(url)
                
                # Verific daca a fost deja vizitat
                if url in self.pagini_vizitate:
                    continue
                if adancime > CONFIG['max_adancime']:
                    continue
                
                # Marchez ca vizitat
                with self.lock:
                    if url in self.pagini_vizitate:
                        continue
                    self.pagini_vizitate.add(url)
                
                batch.append(url_info)
            
            if not batch:
                continue
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(self.proceseaza_url, url_info): url_info for url_info in batch}
                
                for future in as_completed(futures):
                    url_info = futures[future]
                    pagini_scanate += 1
                    
                    try:
                        rezultat = future.result()
                        
                        if rezultat is None:
                            print(f"[{pagini_scanate}] Nu am putut accesa: {url_info[0][:60]}...")
                            continue
                        
                        with self.lock:
                            self.statistici['pagini_scanate'] += 1
                            self.statistici['domenii_explorate'].add(rezultat['domeniu'])
                            
                            if rezultat['domeniu'] not in self.domenii_descoperite:
                                self.domenii_descoperite.add(rezultat['domeniu'])
                                print(f"[{pagini_scanate}] Domeniu nou: {rezultat['domeniu']}")
                        
                        for pdf in rezultat['linkuri_pdf']:
                            with self.lock:
                                if pdf['link'] not in [d['link'] for d in self.documente_gasite]:
                                    pdf['sursa'] = rezultat['sursa']
                                    pdf['pagina_gasita'] = rezultat['url']
                                    self.documente_gasite.append(pdf)
                                    self.statistici['pdf_gasite'] += 1
                                    print(f"[{pagini_scanate}] PDF gasit: {pdf['nume'][:50]}...")
                        
                        for link_info in rezultat['linkuri_pagini']:
                            link_url = link_info['url']
                            link_domeniu = link_info['domeniu']
                            
                            with self.lock:
                                # Verific daca URL-ul nu a fost vizitat si nu e deja in coada
                                if link_url not in self.pagini_vizitate and link_url not in self.url_in_coada:
                                    if link_domeniu != rezultat['domeniu']:
                                        noua_sursa = link_domeniu.replace('.gov.ro', '').replace('www.', '').upper()
                                    else:
                                        noua_sursa = rezultat['sursa']
                                    coada.append((link_url, rezultat['adancime'] + 1, noua_sursa))
                                    self.url_in_coada.add(link_url)
                        
                    except Exception as e:
                        print(f"[{pagini_scanate}] Eroare: {e}")
            
            timp_curent = time.time()
            timp_trecut = timp_curent - timp_start
            viteza = pagini_scanate / timp_trecut if timp_trecut > 0 else 0
            print(f"[{timp_trecut:.0f}s] Progres: {pagini_scanate} pagini | {len(self.documente_gasite)} PDF-uri | {viteza:.1f} pag/s | Coada: {len(coada)}")
            print("")
        
        timp_final = time.time()
        durata_secunde = timp_final - timp_start
        
        if durata_secunde < 60:
            durata_str = f"{durata_secunde:.1f} secunde"
        elif durata_secunde < 3600:
            minute = int(durata_secunde // 60)
            secunde = int(durata_secunde % 60)
            durata_str = f"{minute} min {secunde} sec"
        else:
            ore = int(durata_secunde // 3600)
            minute = int((durata_secunde % 3600) // 60)
            secunde = int(durata_secunde % 60)
            durata_str = f"{ore} ore {minute} min {secunde} sec"
        
        print("")
        print("=" * 70)
        if are_limita and pagini_scanate >= limita:
            print(f"OPRIT: Am atins limita de {limita} pagini")
            print(f"Mai erau {len(coada)} pagini in coada de explorat")
        else:
            print("FINALIZAT: Coada s-a golit, am explorat toate paginile disponibile")
        
        print(f"Timp total: {durata_str}")
        print(f"Pagini scanate: {pagini_scanate}")
        print(f"Domenii explorate: {len(self.statistici['domenii_explorate'])}")
        print(f"PDF-uri gasite: {len(self.documente_gasite)}")
        if durata_secunde > 0:
            print(f"Viteza medie: {pagini_scanate / durata_secunde:.1f} pagini/secunda")
        print("=" * 70)
        
        self.statistici['durata_secunde'] = durata_secunde
        self.statistici['durata_str'] = durata_str
    
    def descarca_pdf(self, url, folder):
        """Descarca efectiv un fisier PDF."""
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            nume_fisier = url.split('/')[-1]
            nume_fisier = re.sub(r'[^\w\-_\.]', '_', nume_fisier)
            
            cale_completa = os.path.join(folder, nume_fisier)
            
            raspuns = self.session.get(url, timeout=30, verify=False)
            raspuns.raise_for_status()
            
            with open(cale_completa, 'wb') as f:
                f.write(raspuns.content)
            
            return cale_completa
        except Exception as e:
            return None
    
    def salveaza_csv(self, nume_fisier='rezultate_pap_recursiv.csv'):
        """Salveaza rezultatele in CSV."""
        print(f"Salvez CSV: {nume_fisier}")
        
        with open(nume_fisier, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Nr.', 'Sursa', 'Nume Document', 'Link Download', 'Pagina Gasita'])
            
            for i, doc in enumerate(self.documente_gasite, 1):
                writer.writerow([
                    i,
                    doc.get('sursa', ''),
                    doc['nume'],
                    doc['link'],
                    doc.get('pagina_gasita', '')
                ])
        
        print(f"Am salvat {len(self.documente_gasite)} documente in {nume_fisier}")
    
    def genereaza_html(self, nume_fisier='rezultate_pap_recursiv.html'):
        """Genereaza raport HTML cu buton de download CSV."""
        print(f"Generez HTML: {nume_fisier}")
        
        pe_domenii = {}
        for doc in self.documente_gasite:
            domeniu = doc.get('domeniu', 'necunoscut')
            if domeniu not in pe_domenii:
                pe_domenii[domeniu] = []
            pe_domenii[domeniu].append(doc)
        
        csv_content = "Nr.,Sursa,Nume Document,Link Download,Pagina Gasita\n"
        for i, doc in enumerate(self.documente_gasite, 1):
            nume = doc['nume'].replace('"', '""')
            sursa = doc.get('sursa', '').replace('"', '""')
            pagina = doc.get('pagina_gasita', '').replace('"', '""')
            csv_content += f'{i},"{sursa}","{nume}","{doc["link"]}","{pagina}"\n'
        
        csv_base64 = base64.b64encode(csv_content.encode('utf-8-sig')).decode('utf-8')
        
        html = f'''<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PAP Crawler - Rezultate</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: #f5f5f5;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: #ffffff; 
            padding: 30px; 
            border-radius: 8px; 
            border: 1px solid #e0e0e0;
        }}
        h1 {{ color: #333333; margin-bottom: 5px; font-size: 24px; }}
        .subtitlu {{ color: #666666; margin-bottom: 25px; font-size: 14px; }}
        
        .header-actions {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 25px;
        }}
        
        .download-csv-btn {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: #2563eb;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            border: none;
        }}
        .download-csv-btn:hover {{
            background: #1d4ed8;
        }}
        
        .stats {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); 
            gap: 15px; 
            margin-bottom: 30px; 
        }}
        .stat-box {{ 
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            color: #333333; 
            padding: 20px; 
            border-radius: 6px; 
            text-align: center;
        }}
        .stat-box.blue {{ 
            background: #eff6ff;
            border-color: #bfdbfe;
        }}
        .stat-box.gray {{ 
            background: #f3f4f6;
            border-color: #d1d5db;
        }}
        .stat-box .numar {{ font-size: 28px; font-weight: bold; color: #1f2937; }}
        .stat-box .label {{ font-size: 13px; color: #6b7280; margin-top: 5px; }}
        
        .domeniu-section {{ 
            margin-bottom: 25px; 
            border: 1px solid #e0e0e0; 
            border-radius: 6px; 
            overflow: hidden;
        }}
        .domeniu-header {{ 
            background: #374151;
            color: white; 
            padding: 12px 20px;
            font-size: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .domeniu-header .count {{
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 13px;
        }}
        
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #f3f4f6; padding: 12px; text-align: left; font-weight: 600; font-size: 13px; color: #374151; }}
        td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 13px; }}
        tr:hover {{ background: #f9fafb; }}
        
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        
        .download-btn {{
            display: inline-block;
            background: #2563eb;
            color: white;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        .download-btn:hover {{ background: #1d4ed8; text-decoration: none; }}
        
        .page-found {{
            font-size: 11px;
            color: #9ca3af;
            word-break: break-all;
        }}
        
        .footer {{ 
            margin-top: 30px; 
            padding-top: 20px; 
            border-top: 1px solid #e5e7eb; 
            text-align: center; 
            color: #6b7280;
            font-size: 13px;
        }}
        
        .domain-list {{
            background: #f9fafb;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            border: 1px solid #e5e7eb;
        }}
        .domain-list h3 {{ margin-bottom: 10px; color: #374151; font-size: 14px; font-weight: 600; }}
        .domain-tag {{
            display: inline-block;
            background: #e5e7eb;
            color: #374151;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            margin: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-actions">
            <div>
                <h1>PAP Crawler Recursiv</h1>
                <p class="subtitlu">
                    Crawling finalizat la {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | 
                    Explorare automata a site-urilor .gov.ro
                </p>
            </div>
            <a href="data:text/csv;base64,{csv_base64}" 
               download="rezultate_pap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv" 
               class="download-csv-btn">
                Descarca CSV ({len(self.documente_gasite)} documente)
            </a>
        </div>
        
        <div class="stats">
            <div class="stat-box blue">
                <div class="numar">{len(self.documente_gasite)}</div>
                <div class="label">Documente PAP</div>
            </div>
            <div class="stat-box gray">
                <div class="numar">{self.statistici['pagini_scanate']}</div>
                <div class="label">Pagini Scanate</div>
            </div>
            <div class="stat-box gray">
                <div class="numar">{len(pe_domenii)}</div>
                <div class="label">Domenii Gasite</div>
            </div>
            <div class="stat-box blue">
                <div class="numar">{self.statistici.get('durata_str', 'N/A')}</div>
                <div class="label">Timp Total</div>
            </div>
        </div>
        
        <div class="domain-list">
            <h3>Domenii .gov.ro descoperite:</h3>
            {''.join(f'<span class="domain-tag">{dom}</span>' for dom in sorted(self.domenii_descoperite))}
        </div>
'''
        
        for domeniu, docs in sorted(pe_domenii.items()):
            html += f'''
        <div class="domeniu-section">
            <div class="domeniu-header">
                <span>{domeniu}</span>
                <span class="count">{len(docs)} documente</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 50px;">Nr.</th>
                        <th>Nume Document</th>
                        <th style="width: 120px;">Actiuni</th>
                    </tr>
                </thead>
                <tbody>
'''
            for i, doc in enumerate(docs, 1):
                html += f'''
                    <tr>
                        <td>{i}</td>
                        <td>
                            {doc['nume']}
                            <div class="page-found">Gasit pe: {doc.get('pagina_gasita', 'N/A')}</div>
                        </td>
                        <td>
                            <a href="{doc['link']}" target="_blank" class="download-btn">Descarca PDF</a>
                        </td>
                    </tr>
'''
            html += '''
                </tbody>
            </table>
        </div>
'''
        
        html += f'''
        <div class="footer">
            <p>PAP Crawler Recursiv | LAB 3 eGovernment 2025-2026</p>
            <p>Generat la {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
'''
        
        with open(nume_fisier, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"Am salvat raportul HTML in {nume_fisier}")
    
    def afiseaza_rezumat(self):
        """Afiseaza rezumatul final."""
        print("")
        print("=" * 70)
        print("REZUMAT CRAWLING RECURSIV CROSS-DOMAIN")
        print("=" * 70)
        
        print(f"Timp total de executie: {self.statistici.get('durata_str', 'N/A')}")
        
        print(f"Statistici generale:")
        print(f"- Pagini scanate: {self.statistici['pagini_scanate']}")
        print(f"- Documente PAP gasite: {len(self.documente_gasite)}")
        print(f"- Domenii explorate: {len(self.statistici['domenii_explorate'])}")
        print(f"- Erori intampinate: {self.statistici['erori']}")
        
        print(f"Domenii .gov.ro descoperite: {len(self.domenii_descoperite)}")
        for dom in sorted(self.domenii_descoperite):
            print(f"- {dom}")
        
        if self.documente_gasite:
            print("Exemple de documente gasite:")
            for doc in self.documente_gasite[:5]:
                print(f"- [{doc.get('sursa', 'N/A')}] {doc['nume'][:60]}...")


# ============================================================================
# FUNCTIE PRINCIPALA
# ============================================================================

def main():
    """Functia principala care ruleaza crawler-ul recursiv cross-domain."""
    print("")
    print("=" * 70)
    print("PAP CRAWLER RECURSIV CROSS-DOMAIN")
    print("Colectare automata de Planuri Anuale de Achizitii Publice")
    print("=" * 70)
    
    crawler = CrawlerRecursiv()
    crawler.crawl()
    
    if not crawler.documente_gasite:
        print("Nu am gasit documente PAP!")
        print("Incearca sa maresti CONFIG['max_pagini_total'] sau CONFIG['max_adancime']")
        print("Sau verifica daca site-urile sunt accesibile.")
        return
    
    crawler.salveaza_csv('rezultate_pap_recursiv.csv')
    crawler.genereaza_html('rezultate_pap_recursiv.html')
    
    crawler.afiseaza_rezumat()
    
    print("")
    print("Crawler recursiv cross-domain finalizat!")
    print("Fisiere generate:")
    print("- rezultate_pap_recursiv.csv")
    print("- rezultate_pap_recursiv.html")
    if CONFIG['descarca_pdf']:
        print(f"- {CONFIG['folder_download']}/ (PDF-uri descarcate)")
    
    html_path = os.path.abspath('rezultate_pap_recursiv.html')
    print(f"Deschid rezultatele in browser...")
    webbrowser.open('file://' + html_path)
    
    print("")
    print("=" * 70)
    print("")


if __name__ == '__main__':
    main()