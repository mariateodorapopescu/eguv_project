"""
GENERATOR DATE DE TEST - LAB 2 eGovernment
Genereaza 20 comenzi fictive in baza de date MongoDB
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import random
 
# Conectare MongoDB Atlas
MONGO_URI = "mongodb+srv://root:student@cluster0.oyzbfhf.mongodb.net/proiect_metrorex?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

client = MongoClient(MONGO_URI)
db = client.proiect_metrorex

# Date fictive pentru generare
NUME = ["Popescu", "Ionescu", "Popa", "Gheorghe", "Dumitru", "Stan", "Stoica", "Marin", "Tudor", "Dobre", "Radu", "Barbu", "Nistor", "Florea", "Cristea"]
PRENUME = ["Ion", "Maria", "Andrei", "Elena", "Alexandru", "Ana", "Mihai", "Ioana", "George", "Cristina", "Adrian", "Diana", "Florin", "Laura", "Vlad"]

PRODUSE = {
    'bilet_1_calatorii': 5.0,
    'bilet_2_calatorii': 10.0,
    'bilet_10_calatorii': 40.0,
    'bilet_19_calatorii_s': 4.0,
    'abonament_24': 12.0,
    'abonament_72': 35.0,
    'abonament_saptamanal': 45.0,
    'abonament_lunar': 100.0,
    'abonament_lunar_elev': 10.0,
    'abonament_6l': 500.0,
    'abonament_anual': 900.0,
    'abonament_donatori': 50.0,
}

METODE_PLATA = ['cash', 'transfer', 'card']

TVA_RATE = 0.21

def generate_cnp():
    """Genereaza CNP fictiv valid"""
    sex = random.choice(['1', '2', '5', '6'])
    an = str(random.randint(70, 99))
    luna = str(random.randint(1, 12)).zfill(2)
    zi = str(random.randint(1, 28)).zfill(2)
    judet = str(random.randint(1, 52)).zfill(2)
    nnn = str(random.randint(1, 999)).zfill(3)
    
    cnp_partial = sex + an + luna + zi + judet + nnn
    
    # Calcul cifra control
    control = "279146358279"
    suma = sum(int(cnp_partial[i]) * int(control[i]) for i in range(12))
    c = suma % 11
    if c == 10:
        c = 1
    
    return cnp_partial + str(c)

def generate_order(index):
    """Genereaza o comanda fictiva"""
    
    nume = random.choice(NUME)
    prenume = random.choice(PRENUME)
    tip_produs = random.choice(list(PRODUSE.keys()))
    pret_unitar = PRODUSE[tip_produs]
    cantitate = random.randint(1, 5)
    metoda_plata = random.choice(METODE_PLATA)
    
    subtotal = pret_unitar * cantitate
    tva = subtotal * TVA_RATE
    total = subtotal + tva
    
    # Data random in ultimele 30 zile
    days_ago = random.randint(0, 30)
    data_comanda = datetime.now() - timedelta(days=days_ago)
    
    return {
        'nume': nume,
        'prenume': prenume,
        'cnp': generate_cnp(),
        'email': f"{prenume.lower()}.{nume.lower()}@email.com",
        'telefon': f"07{random.randint(10000000, 99999999)}",
        'adresa': f"Str. {random.choice(['Valea Lunga', 'Cascadelor', 'Frunzisului', 'Ghioceilor', 'Brazi'])} nr. {random.randint(1, 100)}, Bucuresti",
        'tip_produs': tip_produs,
        'cantitate': cantitate,
        'pret_unitar': pret_unitar,
        'subtotal': round(subtotal, 2),
        'tva': round(tva, 2),
        'total': round(total, 2),
        'metoda_plata': metoda_plata,
        'observatii': None,
        'accept_termeni': True,
        'data_comanda': data_comanda.isoformat(),
        'numar_comanda': f"MTR{data_comanda.strftime('%Y%m%d%H%M%S')}{index:02d}",
        'status': 'finalizat'
    }

def main():
    # Verifica cate comenzi exista deja
    count_existing = db.comenzi.count_documents({})
    print(f"\nComenzi existente in baza de date: {count_existing}")
    
    # Genereaza 20 comenzi noi
    NUM_COMENZI = 20
    comenzi = [generate_order(i) for i in range(NUM_COMENZI)]
    
    # Insereaza in baza de date
    result = db.comenzi.insert_many(comenzi)
    
    for i, comanda in enumerate(comenzi, 1):
        print(f"{i:2d}. {comanda['nume']} {comanda['prenume']} | "
              f"{comanda['tip_produs']:25s} | "
              f"{comanda['total']:8.2f} RON | "
              f"{comanda['metoda_plata']}")
    
    total_vanzari = sum(c['total'] for c in comenzi)
    print(f"Total vanzari generate: {total_vanzari:.2f} RON")
    
    # Per tip produs
    produse_count = {}
    for c in comenzi:
        tip = c['tip_produs']
        produse_count[tip] = produse_count.get(tip, 0) + 1
    
    print("\nDistributie produse:")
    for tip, count in sorted(produse_count.items(), key=lambda x: -x[1]):
        print(f"  {tip}: {count} comenzi")
    
    # Per metoda plata
    metode_count = {}
    for c in comenzi:
        m = c['metoda_plata']
        metode_count[m] = metode_count.get(m, 0) + 1
    
    print("\nDistributie metode plata:")
    for metoda, count in metode_count.items():
        print(f"  {metoda}: {count} comenzi")

if __name__ == '__main__':
    main()