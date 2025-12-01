# Sistem Automatizat de Vânzări și Raportare Metrorex

> O implementare completă a unui sistem de gestiune a tranzacțiilor, analiză de date și conformitate eGovernment, dezvoltat cu **Flask** și **MongoDB**.

-----

## Caracteristici Principale

| Modul | Descriere Detaliată |
| :--- | :--- |
| **Punct de Vânzare (POS)** | Interfață simplă (`index.html`) pentru înregistrarea rapidă a vânzărilor de titluri de călătorie. |
| **Generare Documente** | Emiți automat **Chitanțe PDF** și documente de **Audit XML** pentru fiecare tranzacție, asigurând conformitatea. |
| **Dashboard Analitic** | Vizualizare centralizată a statisticilor cheie și a distribuției datelor. |
| **Rapoarte Complexe** | Generare on-demand de **Rapoarte PDF detaliate** cu multiple grafice (ReportLab & Matplotlib) pe baza datelor din MongoDB. |
| **Gestiune Comenzi** | Interfață dedicată (`comenzi.html`) pentru vizualizarea, filtrarea și ștergerea (CRUD) tranzacțiilor. |

-----

## Stack Tehnologic

Acest proiect combină puterea Python pe partea de backend cu o bază de date NoSQL rapidă și un frontend web standard:

| Categorie | Tehnologii Cheie | Fisiere Relevante |
| :--- | :--- | :--- |
| **Backend & Web** | **Python**, **Flask** | `app.py`, `generate_report.py` |
| **Bază de Date** | **MongoDB** (Atlas Cloud) | `app.py`, `generate_test_data.py` |
| **Raportare** | **ReportLab**, **Matplotlib** | `generate_report.py` |
| **Frontend** | HTML5, CSS3, JavaScript | `index.html`, `script.js`, `style.css` |

-----

## Instalare Rapidă

### 1\. Clonare și Dependențe

```bash
# Clonează repository-ul
git clone https://github.com/mariateodorapopescu/eguv_project.git
cd eguv_project

# Creează și activează mediul virtual
python3 -m venv venv
source venv/bin/activate 

# Instalează librăriile din requirements.txt
pip install -r requirements.txt
```

### 2\. Baza de Date & Date de Test

Aplicația folosește MongoDB Atlas. String-ul de conexiune este configurat în `app.py`.

Pentru a avea date de analizat în Dashboard, rulează scriptul de populare:

```bash
python3 generate_test_data.py
# Inserează automat 20 de comenzi fictive.
```

### 3\. Pornire Server

```bash
python3 app.py
# Serverul rulează la http://127.0.0.1:5000/
```

-----

## Navigare Aplicație

| Punct de Acces | Descriere |
| :--- | :--- |
| **`/`** | **Formular Vânzări** - Pagina de intrare. |
| **`/comenzi`** | **Tabel Comenzi** - Vizualizare și gestionare. |
| **`/dashboard`** | **Analiză & Raportare** - Aici se generează Raportul PDF. |
| **`/generated_files/`** | Director pentru fișierele generate (chitanțe și rapoarte). |

-----

## Contribuție

Feedback-ul este valoros\! A se folosi funcționalitățile GitHub (Issues și Pull Requests) pentru a sugera îmbunătățiri.

-----

## Licență

Acest proiect este dezvoltat sub licența **MIT**.

-----