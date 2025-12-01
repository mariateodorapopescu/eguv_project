from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_pymongo import PyMongo
from datetime import datetime
from reportlab.pdfgen import canvas
import xml.etree.ElementTree as ET
from xml.dom import minidom
import numpy as np
import os

# Import modulul pentru rapoarte
import generate_report as rp

app = Flask(__name__, template_folder='.', static_folder='.')


# MongoDB Atlas
app.config["MONGO_URI"] = "mongodb+srv://root:student@cluster0.oyzbfhf.mongodb.net/proiect_metrorex?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"
mongo = PyMongo(app)

# Folder fisiere generate
if not os.path.exists('generated_files'):
    os.makedirs('generated_files')

# Preturi produse
PRICES = {
    'bilet_1_calatorii': 5.0,
    'bilet_2_calatorii': 10.0,
    'bilet_10_calatorii': 40.0,
    'abonament_24': 12.0,
    'abonament_72': 35.0,
    'abonament_saptamanal': 45.0,
    'abonament_lunar': 100.0,
    'abonament_lunar_elev': 10.0,
    'abonament_6l': 500.0,
    'abonament_anual': 900.0,
    'abonament_donatori': 50.0,
    'bilet_19_calatorii_s': 4.0,
}

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

TVA_RATE = 0.19

# ============================================================
# RUTE PAGINI
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/comenzi.html')
def comenzi_page():
    return render_template('comenzi.html')

@app.route('/dashboard.html')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/style.css')
def serve_css():
    return send_file('style.css', mimetype='text/css')

@app.route('/script.js')
def serve_js():
    return send_file('script.js', mimetype='application/javascript')

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/comenzi', methods=['GET'])
def api_get_comenzi():
    """Returneaza toate comenzile ca JSON"""
    try:
        comenzi = list(mongo.db.comenzi.find({}, {'_id': 0}).sort('data_comanda', -1))
        return jsonify({
            'success': True,
            'count': len(comenzi),
            'comenzi': comenzi
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """Returneaza statistici pentru dashboard"""
    try:
        comenzi = list(mongo.db.comenzi.find({}))
        stats = calculate_stats(comenzi)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-report', methods=['POST'])
def api_generate_report():
    """Genereaza raport PDF complet cu grafice - folosind generate_report.py"""
    try:
        # 1. Extrage date din MongoDB folosind functia din generate_report
        comenzi = rp.get_data()
        
        if len(comenzi) < 1:
            return jsonify({
                'success': False,
                'error': 'Nu exista comenzi in baza de date. Adaugati comenzi mai intai.'
            }), 400
        
        # 2. Analizeaza datele folosind functia din generate_report
        stats = rp.analyze_data(comenzi)
        
        # 3. Genereaza toate graficele folosind functiile din generate_report
        charts = {
            'bilete_abonamente': rp.create_chart_bilete_abonamente(stats),
            'metode_plata': rp.create_chart_metode_plata(stats),
            'top_produse': rp.create_chart_top_produse(stats),
            'vanzari_produse': rp.create_chart_vanzari_produse(stats),
            'comenzi_zile': rp.create_chart_comenzi_zile(stats),
            'distributie_valori': rp.create_chart_distributie_valori(stats),
        }
        
        # 4. Genereaza PDF-ul raportului folosind functia din generate_report
        pdf_path = rp.generate_pdf_report(stats, charts)
        
        # Extrage doar numele fisierului din path
        pdf_filename = os.path.basename(pdf_path)
        
        return jsonify({
            'success': True,
            'message': f'Raport generat cu succes! {stats["total_comenzi"]} comenzi analizate.',
            'pdf_file': pdf_filename,
            'stats': {
                'total_comenzi': stats['total_comenzi'],
                'total_vanzari': round(stats['total_vanzari'], 2),
                'total_tva': round(stats['total_tva'], 2)
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-payment-proof/<numar_comanda>', methods=['POST'])
def generate_payment_proof(numar_comanda):
    """Genereaza dovada platii (PDF si XML) pentru o comanda specifica"""
    try:
        # Gaseste comanda
        comanda = mongo.db.comenzi.find_one({'numar_comanda': numar_comanda}, {'_id': 0})
        
        if not comanda:
            return jsonify({'success': False, 'error': 'Comanda nu a fost gasita'}), 404
        
        # Genereaza XML
        xml_filename = generate_xml(comanda, numar_comanda)
        
        # Genereaza PDF dovada plata (format bon A6)
        pdf_filename = generate_order_pdf(comanda, numar_comanda)
        
        return jsonify({
            'success': True,
            'message': 'Dovada platii generata cu succes!',
            'xml_file': xml_filename,
            'pdf_file': pdf_filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        tip_produs = data.get('tip_produs')
        cantitate = int(data.get('cantitate', 1))
        
        if tip_produs not in PRICES:
            return jsonify({'error': 'Tip produs invalid'}), 400
        
        pret_unitar = PRICES[tip_produs]
        subtotal = pret_unitar * cantitate
        tva = subtotal * TVA_RATE
        total = subtotal + tva
        
        return jsonify({
            'pret_unitar': round(pret_unitar, 2),
            'subtotal': round(subtotal, 2),
            'tva': round(tva, 2),
            'total': round(total, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit_form():
    try:
        data = request.json
        
        required_fields = ['nume', 'prenume', 'email', 'telefon', 'cnp', 'tip_produs', 'cantitate', 'total']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campul {field} este obligatoriu'}), 400
        
        if len(data['cnp']) != 13 or not data['cnp'].isdigit():
            return jsonify({'error': 'CNP invalid'}), 400
        
        if '@' not in data['email']:
            return jsonify({'error': 'Email invalid'}), 400
        
        data['data_comanda'] = datetime.now().isoformat()
        data['numar_comanda'] = f"MTR{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data['status'] = 'finalizat'
        
        # Genereaza fisierele
        xml_filename = generate_xml(data, data['numar_comanda'])
        pdf_filename = generate_order_pdf(data, data['numar_comanda'])
        
        # Salveaza caile fisierelor in comanda
        data['xml_file'] = xml_filename
        data['pdf_file'] = pdf_filename
        
        result = mongo.db.comenzi.insert_one(data)
        comanda_id = str(result.inserted_id)
        
        return jsonify({
            'success': True,
            'message': 'Comanda inregistrata!',
            'numar_comanda': data['numar_comanda'],
            'comanda_id': comanda_id,
            'xml_file': xml_filename,
            'pdf_file': pdf_filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-comanda/<numar_comanda>', methods=['DELETE'])
def delete_comanda(numar_comanda):
    """Sterge o comanda"""
    try:
        result = mongo.db.comenzi.delete_one({'numar_comanda': numar_comanda})
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Comanda stearsa'})
        return jsonify({'success': False, 'error': 'Comanda nu a fost gasita'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join('generated_files', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Fisier negasit'}), 404

# ============================================================
# FUNCTII HELPER PENTRU DASHBOARD (statistici rapide)
# ============================================================

def calculate_stats(comenzi):
    """Calculeaza statistici din comenzi - versiune pentru API dashboard"""
    stats = {
        'total_comenzi': len(comenzi),
        'total_vanzari': 0,
        'total_tva': 0,
        'produse': {},
        'metode_plata': {},
        'bilete_vs_abonamente': {'bilete': 0, 'abonamente': 0},
        'vanzari_per_produs': {},
        'comenzi_per_zi': [0] * 7,
        'valori_comenzi': [],
    }
    
    for c in comenzi:
        total = float(c.get('total', 0)) if c.get('total') else 0
        tva = float(c.get('tva', 0)) if c.get('tva') else 0
        
        stats['total_vanzari'] += total
        stats['total_tva'] += tva
        stats['valori_comenzi'].append(total)
        
        tip = c.get('tip_produs', 'necunoscut')
        stats['produse'][tip] = stats['produse'].get(tip, 0) + 1
        stats['vanzari_per_produs'][tip] = stats['vanzari_per_produs'].get(tip, 0) + total
        
        if 'bilet' in tip:
            stats['bilete_vs_abonamente']['bilete'] += 1
        else:
            stats['bilete_vs_abonamente']['abonamente'] += 1
        
        metoda = c.get('metoda_plata', 'necunoscut')
        stats['metode_plata'][metoda] = stats['metode_plata'].get(metoda, 0) + 1
        
        data_comanda = c.get('data_comanda')
        if data_comanda:
            try:
                if isinstance(data_comanda, str):
                    dt = datetime.fromisoformat(data_comanda.replace('Z', '+00:00'))
                else:
                    dt = data_comanda
                stats['comenzi_per_zi'][dt.weekday()] += 1
            except:
                pass
    
    if stats['valori_comenzi']:
        stats['media_comanda'] = round(float(np.mean(stats['valori_comenzi'])), 2)
        stats['max_comanda'] = round(float(max(stats['valori_comenzi'])), 2)
        stats['min_comanda'] = round(float(min(stats['valori_comenzi'])), 2)
    else:
        stats['media_comanda'] = 0
        stats['max_comanda'] = 0
        stats['min_comanda'] = 0
    
    stats['total_vanzari'] = round(stats['total_vanzari'], 2)
    stats['total_tva'] = round(stats['total_tva'], 2)
    
    return stats

# ============================================================
# GENERARE XML SI PDF PENTRU COMENZI INDIVIDUALE
# ============================================================

def generate_xml(data, comanda_id):
    """Genereaza XML pentru comanda"""
    root = ET.Element('ComandaMetrorex')
    root.set('versiune', '1.0')
    root.set('xmlns', 'http://metrorex.ro/comenzi')
    
    # Informatii comanda
    comanda = ET.SubElement(root, 'Comanda')
    ET.SubElement(comanda, 'NumarComanda').text = data.get('numar_comanda', comanda_id)
    ET.SubElement(comanda, 'DataComanda').text = data.get('data_comanda', datetime.now().isoformat())
    ET.SubElement(comanda, 'Status').text = data.get('status', 'finalizat')
    
    # Informatii client
    client = ET.SubElement(root, 'Client')
    ET.SubElement(client, 'Nume').text = data.get('nume', '')
    ET.SubElement(client, 'Prenume').text = data.get('prenume', '')
    ET.SubElement(client, 'CNP').text = data.get('cnp', '')
    ET.SubElement(client, 'Email').text = data.get('email', '')
    ET.SubElement(client, 'Telefon').text = data.get('telefon', '')
    if data.get('adresa'):
        ET.SubElement(client, 'Adresa').text = data.get('adresa')
    
    # Informatii produs
    produs = ET.SubElement(root, 'Produs')
    tip_produs = data.get('tip_produs', '')
    ET.SubElement(produs, 'TipProdus').text = tip_produs
    ET.SubElement(produs, 'NumeProdus').text = NUME_PRODUSE.get(tip_produs, tip_produs)
    ET.SubElement(produs, 'Cantitate').text = str(data.get('cantitate', 1))
    ET.SubElement(produs, 'PretUnitar').text = str(data.get('pret_unitar', PRICES.get(tip_produs, 0)))
    
    # Informatii financiare
    financiar = ET.SubElement(root, 'Financiar')
    ET.SubElement(financiar, 'Subtotal').text = str(data.get('subtotal', 0))
    ET.SubElement(financiar, 'TVA').text = str(data.get('tva', 0))
    ET.SubElement(financiar, 'CotaTVA').text = '19%'
    ET.SubElement(financiar, 'Total').text = str(data.get('total', 0))
    ET.SubElement(financiar, 'Moneda').text = 'RON'
    
    # Metoda plata
    plata = ET.SubElement(root, 'Plata')
    ET.SubElement(plata, 'MetodaPlata').text = data.get('metoda_plata', 'necunoscut')
    ET.SubElement(plata, 'DataPlata').text = datetime.now().isoformat()
    
    # Observatii
    if data.get('observatii'):
        ET.SubElement(root, 'Observatii').text = data.get('observatii')
    
    xml_string = minidom.parseString(ET.tostring(root, encoding='unicode')).toprettyxml(indent="  ")
    numar = data.get('numar_comanda', comanda_id)
    xml_filename = f"comanda_{numar}.xml"
    xml_path = os.path.join('generated_files', xml_filename)
    
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    return xml_filename

def generate_order_pdf(data, comanda_id):
    """Genereaza PDF dovada plata format A6 (bon de casa)"""
    numar = data.get('numar_comanda', comanda_id)
    pdf_filename = f"dovada_plata_{numar}.pdf"
    pdf_path = os.path.join('generated_files', pdf_filename)
    
    # Format A6: 105mm x 148mm
    A6 = (105 * 2.83465, 148 * 2.83465)  # Convert mm to points
    
    c = canvas.Canvas(pdf_path, pagesize=A6)
    width, height = A6
    margin = 15
    center = width / 2
    
    # ========== HEADER ==========
    y = height - 20
    
    # Logo/Titlu centrat
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(center, y, "METROREX")
    y -= 12
    c.setFont("Helvetica", 7)
    c.drawCentredString(center, y, "Societatea de Transport Bucuresti")
    y -= 10
    c.drawCentredString(center, y, "CIF: RO1234567 | J40/1234/1990")
    
    # Linie separator
    y -= 8
    c.setLineWidth(0.5)
    c.line(margin, y, width - margin, y)
    
    # ========== TITLU BON ==========
    y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(center, y, "DOVADA DE PLATA")
    
    # Numar si data
    y -= 15
    c.setFont("Courier-Bold", 8)
    c.drawCentredString(center, y, f"Nr: {numar}")
    y -= 10
    data_str = data.get('data_comanda', datetime.now().isoformat())[:19].replace('T', ' ')
    c.setFont("Courier", 7)
    c.drawCentredString(center, y, f"Data: {data_str}")
    
    # Linie punctata
    y -= 8
    c.setDash(1, 2)
    c.line(margin, y, width - margin, y)
    c.setDash()
    
    # ========== CLIENT ==========
    y -= 12
    c.setFont("Helvetica-Bold", 7)
    c.drawString(margin, y, "CLIENT:")
    y -= 9
    c.setFont("Helvetica", 7)
    c.drawString(margin, y, f"{data.get('nume', '')} {data.get('prenume', '')}")
    y -= 9
    c.drawString(margin, y, f"CNP: {data.get('cnp', '')}")
    
    # Linie punctata
    y -= 8
    c.setDash(1, 2)
    c.line(margin, y, width - margin, y)
    c.setDash()
    
    # ========== PRODUS ==========
    y -= 12
    c.setFont("Helvetica-Bold", 7)
    c.drawString(margin, y, "ARTICOL")
    c.drawRightString(width - margin, y, "PRET")
    
    y -= 10
    c.setFont("Helvetica", 7)
    tip_produs = data.get('tip_produs', '')
    nume_produs = NUME_PRODUSE.get(tip_produs, tip_produs)
    
    # Truncheaza numele daca e prea lung
    if len(nume_produs) > 25:
        nume_produs = nume_produs[:22] + "..."
    
    cantitate = data.get('cantitate', 1)
    pret_unitar = float(data.get('pret_unitar', 0))
    
    c.drawString(margin, y, nume_produs)
    y -= 9
    c.drawString(margin, y, f"  {cantitate} x {pret_unitar:.2f} RON")
    subtotal_produs = cantitate * pret_unitar
    c.drawRightString(width - margin, y, f"{subtotal_produs:.2f}")
    
    # Linie simpla
    y -= 10
    c.line(margin, y, width - margin, y)
    
    # ========== TOTALE ==========
    y -= 12
    c.setFont("Helvetica", 7)
    
    subtotal = float(data.get('subtotal', 0))
    tva = float(data.get('tva', 0))
    total = float(data.get('total', 0))
    
    c.drawString(margin, y, "Subtotal:")
    c.drawRightString(width - margin, y, f"{subtotal:.2f} RON")
    
    y -= 9
    c.drawString(margin, y, "TVA (19%):")
    c.drawRightString(width - margin, y, f"{tva:.2f} RON")
    
    # Linie dubla pentru total
    y -= 8
    c.setLineWidth(1)
    c.line(margin, y, width - margin, y)
    c.line(margin, y - 2, width - margin, y - 2)
    c.setLineWidth(0.5)
    
    y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "TOTAL:")
    c.drawRightString(width - margin, y, f"{total:.2f} RON")
    
    # ========== METODA PLATA ==========
    y -= 15
    c.setFont("Helvetica", 7)
    metoda = data.get('metoda_plata', 'necunoscut')
    traducere = {'card': 'CARD', 'cash': 'NUMERAR', 'transfer': 'TRANSFER'}
    c.drawCentredString(center, y, f"Platit: {traducere.get(metoda, metoda.upper())}")
    
    # Linie punctata
    y -= 10
    c.setDash(1, 2)
    c.line(margin, y, width - margin, y)
    c.setDash()
    
    # ========== STATUS ==========
    y -= 15
    c.setFont("Helvetica-Bold", 9)
    status = data.get('status', 'finalizat').upper()
    c.drawCentredString(center, y, f"*** {status} ***")
    
    # ========== FOOTER ==========
    y -= 20
    c.setFont("Helvetica", 5)
    c.drawCentredString(center, y, "Multumim pentru achizitie!")
    y -= 7
    c.drawCentredString(center, y, "Pastreaza acest bon pentru verificare.")
    y -= 12
    c.drawCentredString(center, y, f"Emis: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    y -= 7
    c.drawCentredString(center, y, "eGovernment LAB 2 - UPB 2025")
    
    c.save()
    return pdf_filename

if __name__ == '__main__':
    app.run(debug=True, port=5000)