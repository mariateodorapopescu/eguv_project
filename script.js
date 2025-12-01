/**
 * METROREX - JavaScript pentru formular
 */

// Elemente DOM
const form = document.getElementById('metrorexForm');
const modal = document.getElementById('successModal');
const tipProdusSelect = document.getElementById('tip_produs');
const cantitateInput = document.getElementById('cantitate');
const submitBtn = document.getElementById('submitBtn');

// Elemente pentru afișare calcule
const displayPretUnitar = document.getElementById('display-pret-unitar');
const displaySubtotal = document.getElementById('display-subtotal');
const displayTva = document.getElementById('display-tva');
const displayTotal = document.getElementById('display-total');

// Câmpuri ascunse
const hiddenPretUnitar = document.getElementById('pret_unitar');
const hiddenSubtotal = document.getElementById('subtotal');
const hiddenTva = document.getElementById('tva');
const hiddenTotal = document.getElementById('total');

// Variabile pentru fișiere
let currentPdfFile = '';
let currentXmlFile = '';

// Event listeners la încărcare
document.addEventListener('DOMContentLoaded', function() {
    console.log('Script încărcat!');
    
    // Calcul automat
    tipProdusSelect.addEventListener('change', calculatePrice);
    cantitateInput.addEventListener('input', calculatePrice);
    
    // Validări
    document.getElementById('cnp').addEventListener('input', validateCNP);
    document.getElementById('email').addEventListener('blur', validateEmail);
    document.getElementById('telefon').addEventListener('input', validateTelefon);
    tipProdusSelect.addEventListener('change', checkStudentSubscription);
    
    // Submit
    form.addEventListener('submit', handleSubmit);
    
    // Modal
    document.getElementById('closeModal').addEventListener('click', closeModal);
    document.getElementById('downloadPDF').addEventListener('click', downloadPDF);
    document.getElementById('downloadXML').addEventListener('click', downloadXML);
});

// ============================================
// CALCUL AUTOMAT
// ============================================

function calculatePrice() {
    const tipProdus = tipProdusSelect.value;
    const cantitate = parseInt(cantitateInput.value) || 0;
    
    if (!tipProdus || cantitate <= 0) {
        resetCalculation();
        return;
    }
    
    const selectedOption = tipProdusSelect.options[tipProdusSelect.selectedIndex];
    const pretUnitar = parseFloat(selectedOption.getAttribute('data-price')) || 0;
    
    const subtotal = pretUnitar * cantitate;
    const tva = subtotal * 0.19;
    const total = subtotal + tva;
    
    // Actualizează afișaj
    displayPretUnitar.textContent = `${pretUnitar.toFixed(2)} RON`;
    displaySubtotal.textContent = `${subtotal.toFixed(2)} RON`;
    displayTva.textContent = `${tva.toFixed(2)} RON`;
    displayTotal.textContent = `${total.toFixed(2)} RON`;
    
    // Actualizează câmpuri ascunse
    hiddenPretUnitar.value = pretUnitar.toFixed(2);
    hiddenSubtotal.value = subtotal.toFixed(2);
    hiddenTva.value = tva.toFixed(2);
    hiddenTotal.value = total.toFixed(2);
    
    console.log('Calcul:', { pretUnitar, subtotal, tva, total });
}

function resetCalculation() {
    displayPretUnitar.textContent = '0.00 RON';
    displaySubtotal.textContent = '0.00 RON';
    displayTva.textContent = '0.00 RON';
    displayTotal.textContent = '0.00 RON';
    
    hiddenPretUnitar.value = '0';
    hiddenSubtotal.value = '0';
    hiddenTva.value = '0';
    hiddenTotal.value = '0';
}

// ============================================
// VALIDĂRI
// ============================================

function validateCNP(event) {
    const cnp = event.target.value;
    const errorElement = document.getElementById('error-cnp');
    
    const cleanedCNP = cnp.replace(/\D/g, '');
    event.target.value = cleanedCNP;
    
    if (cleanedCNP.length === 0) {
        hideError(errorElement);
        return;
    }
    
    if (cleanedCNP.length !== 13) {
        showError(errorElement, 'CNP-ul trebuie sa aiba exact 13 cifre');
        return;
    }
    
    // Validare cifră control
    const controlDigits = '279146358279';
    let sum = 0;
    
    for (let i = 0; i < 12; i++) {
        sum += parseInt(cleanedCNP[i]) * parseInt(controlDigits[i]);
    }
    
    const controlDigit = sum % 11 === 10 ? 1 : sum % 11;
    const lastDigit = parseInt(cleanedCNP[12]);
    
    if (controlDigit !== lastDigit) {
        showError(errorElement, 'CNP invalid - cifra de control incorecta');
        return;
    }
    
    hideError(errorElement);
}

function validateEmail(event) {
    const email = event.target.value;
    const errorElement = document.getElementById('error-email');
    
    if (email.length === 0) {
        hideError(errorElement);
        return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!emailRegex.test(email)) {
        showError(errorElement, 'Adresa de email este invalida');
        return;
    }
    
    hideError(errorElement);
}

function validateTelefon(event) {
    const telefon = event.target.value;
    const errorElement = document.getElementById('error-telefon');
    
    const cleanedTelefon = telefon.replace(/[^\d\+\-\s\(\)]/g, '');
    event.target.value = cleanedTelefon;
    
    if (cleanedTelefon.length === 0) {
        hideError(errorElement);
        return;
    }
    
    const digitsOnly = cleanedTelefon.replace(/\D/g, '');
    
    if (digitsOnly.length < 10) {
        showError(errorElement, 'Numarul de telefon trebuie sa contina cel putin 10 cifre');
        return;
    }
    
    hideError(errorElement);
}

function checkStudentSubscription() {
    const tipProdus = tipProdusSelect.value;
    const conditiiElevDiv = document.getElementById('conditii-elev');
    
    if (tipProdus === 'abonament_lunar_elev' || tipProdus === 'bilet_19_calatorii_s') {
        conditiiElevDiv.style.display = 'block';
    } else {
        conditiiElevDiv.style.display = 'none';
        document.getElementById('am_legitimatie').checked = false;
    }
}

function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
}

function hideError(element) {
    element.style.display = 'none';
}

// ============================================
// SUBMIT FORMULAR
// ============================================

async function handleSubmit(event) {
    event.preventDefault();
    
    console.log('Submit formular...');
    
    if (!validateForm()) {
        alert('Va rugam sa completati corect toate campurile obligatorii!');
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Se trimite...';
    
    const formData = collectFormData();
    
    console.log('Date colectate:', formData);
    
    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            console.log('Succes!', result);
            
            currentPdfFile = result.pdf_file;
            currentXmlFile = result.xml_file;
            
            showSuccessModal(result);
            
            form.reset();
            resetCalculation();
        } else {
            throw new Error(result.error || 'Eroare necunoscuta');
        }
    } catch (error) {
        console.error('Eroare:', error);
        alert(`Eroare: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'TRIMITE COMANDA';
    }
}

function validateForm() {
    const nume = document.getElementById('nume').value.trim();
    const prenume = document.getElementById('prenume').value.trim();
    const cnp = document.getElementById('cnp').value.trim();
    const email = document.getElementById('email').value.trim();
    const telefon = document.getElementById('telefon').value.trim();
    const tipProdus = document.getElementById('tip_produs').value;
    const cantitate = parseInt(document.getElementById('cantitate').value);
    const acceptTermeni = document.getElementById('accept_termeni').checked;
    
    if (!nume || !prenume || !cnp || !email || !telefon || !tipProdus) {
        return false;
    }
    
    if (cnp.length !== 13 || !/^\d+$/.test(cnp)) {
        return false;
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        return false;
    }
    
    if (cantitate < 1 || cantitate > 50) {
        return false;
    }
    
    if (!acceptTermeni) {
        showError(document.getElementById('error-termeni'), 'Trebuie sa acceptati termenii si conditiile');
        return false;
    }
    
    if (tipProdus === 'abonament_lunar_elev' || tipProdus === 'bilet_19_calatorii_s') {
        const amLegitimatie = document.getElementById('am_legitimatie').checked;
        if (!amLegitimatie) {
            alert('Pentru produsul de elev/student trebuie sa confirmati ca detineti legitimatie valabila.');
            return false;
        }
    }
    
    return true;
}

function collectFormData() {
    return {
        nume: document.getElementById('nume').value.trim(),
        prenume: document.getElementById('prenume').value.trim(),
        cnp: document.getElementById('cnp').value.trim(),
        email: document.getElementById('email').value.trim(),
        telefon: document.getElementById('telefon').value.trim(),
        adresa: document.getElementById('adresa').value.trim() || null,
        tip_produs: document.getElementById('tip_produs').value,
        cantitate: parseInt(document.getElementById('cantitate').value),
        pret_unitar: parseFloat(document.getElementById('pret_unitar').value),
        subtotal: parseFloat(document.getElementById('subtotal').value),
        tva: parseFloat(document.getElementById('tva').value),
        total: parseFloat(document.getElementById('total').value),
        metoda_plata: document.querySelector('input[name="metoda_plata"]:checked').value,
        observatii: document.getElementById('observatii').value.trim() || null,
        accept_termeni: document.getElementById('accept_termeni').checked
    };
}

// ============================================
// MODAL
// ============================================

function showSuccessModal(result) {
    const modalDetails = document.getElementById('modal-details');
    
    modalDetails.innerHTML = `
        <p><strong>Numar comanda:</strong> ${result.numar_comanda}</p>
        <p><strong>Status:</strong> Inregistrata cu succes</p>
        <p><strong>Total:</strong> ${hiddenTotal.value} RON</p>
        <p style="margin-top: 1rem; color: #666; font-size: 0.9rem;">
            Ordinul de plata si confirmarea XML au fost generate.
        </p>
    `;
    
    modal.style.display = 'block';
}

function closeModal() {
    modal.style.display = 'none';
}

// ============================================
// DOWNLOAD
// ============================================

function downloadPDF() {
    if (currentPdfFile) {
        window.location.href = `/download/${currentPdfFile}`;
        console.log('Descarcare PDF:', currentPdfFile);
    } else {
        alert('Fisierul PDF nu este disponibil.');
    }
}

function downloadXML() {
    if (currentXmlFile) {
        window.location.href = `/download/${currentXmlFile}`;
        console.log('Descarcare XML:', currentXmlFile);
    } else {
        alert('Fisierul XML nu este disponibil.');
    }
}

console.log('Script Metrorex incarcat!');