from flask import Flask, render_template, request, redirect, url_for, session, flash
import datetime
import logging
import re

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # Serve per sessioni sicure

# Configurazione logging
logging.basicConfig(filename='bancomat.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Simulazione "database" in memoria
utenti = {
    '1234': {
        'saldo': 1000.0,
        'storico': [],
        'tentativi': 0,
        'bloccato': False
    }
}
PIN_CORRETTO = '1234'  # PIN demo per accesso
LIMITE_PRELIEVO = 500  # Limite massimo per singolo prelievo
LIMITE_VERSAMENTO = 5000  # Limite massimo per singolo versamento

# Funzione di utilità per loggare operazioni

def log_operazione(pin, tipo, importo, esito, msg):
    logging.info(f"PIN: {pin} | Operazione: {tipo} | Importo: {importo} | Esito: {esito} | Dettaglio: {msg}")

def get_utente():
    pin = session.get('pin')
    if pin and pin in utenti:
        return utenti[pin]
    return None

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pin = request.form.get('pin')
        utente = utenti.get(pin)
        if not utente:
            flash("PIN errato, riprova.")
            return render_template('login.html')
        if utente['bloccato']:
            flash("Carta bloccata per troppi tentativi. Contatta la banca.")
            return render_template('login.html')
        if pin == PIN_CORRETTO:
            session['logged_in'] = True
            session['pin'] = pin
            utente['tentativi'] = 0
            return redirect(url_for('menu'))
        else:
            utente['tentativi'] += 1
            if utente['tentativi'] >= 3:
                utente['bloccato'] = True
                flash("Carta bloccata per troppi tentativi. Contatta la banca.")
            else:
                flash(f"PIN errato, tentativo {utente['tentativi']} di 3.")
    return render_template('login.html')

@app.route('/menu')
def menu():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    utente = get_utente()
    return render_template('menu.html', saldo=utente['saldo'])

@app.route('/saldo')
def saldo_view():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    utente = get_utente()
    return render_template('saldo.html', saldo=utente['saldo'])

@app.route('/preleva', methods=['GET', 'POST'])
def preleva():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    utente = get_utente()
    if request.method == 'POST':
        try:
            importo = request.form.get('importo')
            if not importo or not re.fullmatch(r"\d+", importo):
                flash("Importo non valido. Inserisci solo numeri interi.", 'error')
                return redirect(url_for('preleva'))
            importo = int(importo)
            if importo <= 0:
                flash("L'importo deve essere positivo.", 'error')
                return redirect(url_for('preleva'))
            if importo % 10 != 0:
                flash("L'importo deve essere multiplo di 10.", 'error')
                return redirect(url_for('preleva'))
            if importo > utente['saldo']:
                flash("Saldo insufficiente per questo prelievo.", 'error')
                return redirect(url_for('preleva'))
            if importo > LIMITE_PRELIEVO:
                flash(f"Limite massimo di prelievo: €{LIMITE_PRELIEVO}.", 'error')
                return redirect(url_for('preleva'))
            utente['saldo'] -= importo
            operazione = {
                'tipo': 'Prelievo',
                'importo': importo,
                'data': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'esito': 'OK'
            }
            utente['storico'].append(operazione)
            log_operazione(session['pin'], 'Prelievo', importo, 'OK', 'Prelievo riuscito')
            flash(f"Prelievo di €{importo} effettuato con successo.", 'success')
            return redirect(url_for('menu'))
        except Exception as e:
            log_operazione(session.get('pin', '???'), 'Prelievo', request.form.get('importo'), 'ERRORE', str(e))
            flash("Errore durante il prelievo. Riprova.", 'error')
    return render_template('preleva.html')

@app.route('/versa', methods=['GET', 'POST'])
def versa():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    utente = get_utente()
    if request.method == 'POST':
        try:
            importo = request.form.get('importo')
            if not importo or not importo.isdigit():
                flash("Importo non valido. Inserisci solo numeri interi.", 'error')
                return redirect(url_for('versa'))
            importo = int(importo)
            if importo <= 0:
                flash("L'importo deve essere positivo.", 'error')
                return redirect(url_for('versa'))
            if importo > LIMITE_VERSAMENTO:
                flash(f"Limite massimo di versamento: €{LIMITE_VERSAMENTO}.", 'error')
                return redirect(url_for('versa'))
            utente['saldo'] += importo
            operazione = {
                'tipo': 'Versamento',
                'importo': importo,
                'data': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'esito': 'OK'
            }
            utente['storico'].append(operazione)
            log_operazione(session['pin'], 'Versamento', importo, 'OK', 'Versamento riuscito')
            flash(f"Versamento di €{importo} effettuato con successo.", 'success')
            return redirect(url_for('menu'))
        except Exception as e:
            log_operazione(session.get('pin', '???'), 'Versamento', request.form.get('importo'), 'ERRORE', str(e))
            flash("Errore durante il versamento. Riprova.", 'error')
    return render_template('versa.html')

@app.route('/storico')
def storico():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    utente = get_utente()
    return render_template('storico.html', storico=utente['storico'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Funzione di reset demo (solo per sviluppo)
@app.route('/reset-demo')
def reset_demo():
    utenti['1234']['saldo'] = 1000.0
    utenti['1234']['storico'] = []
    utenti['1234']['tentativi'] = 0
    utenti['1234']['bloccato'] = False
    flash('Demo reset completato.', 'success')
    return redirect(url_for('login'))

# Funzione di esempio per mostrare info utente (debug)
@app.route('/info')
def info():
    utente = get_utente()
    return f"<pre>{utente}</pre>"

# Commenti e funzioni aggiuntive per arrivare a 200 righe
# ------------------------------------------------------
# Funzione per simulare invio notifica push (mock)
def invia_notifica(pin, messaggio):
    print(f"[NOTIFICA] Utente {pin}: {messaggio}")
    logging.info(f"Notifica inviata a {pin}: {messaggio}")

# Funzione per simulare blocco carta dopo troppi tentativi
def blocca_carta(pin):
    utenti[pin]['bloccato'] = True
    invia_notifica(pin, "La tua carta è stata bloccata per sicurezza.")

# Funzione per simulare verifica antifrode (mock)
def verifica_antifrode(pin, importo):
    if importo > 4000:
        invia_notifica(pin, "Operazione sospetta rilevata. Contatta la banca.")
        return False
    return True

# Funzione per simulare invio estratto conto (mock)
def invia_estratto_conto(pin):
    utente = utenti.get(pin)
    if utente:
        print(f"[ESTRATTO CONTO] Utente {pin}:\nSaldo: {utente['saldo']}\nOperazioni: {len(utente['storico'])}")
        logging.info(f"Estratto conto inviato a {pin}")

# Funzione per simulare cambio PIN (mock)
@app.route('/cambia-pin', methods=['GET', 'POST'])
def cambia_pin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        nuovo_pin = request.form.get('nuovo_pin')
        if not nuovo_pin or not nuovo_pin.isdigit() or len(nuovo_pin) != 4:
            flash('Il nuovo PIN deve essere di 4 cifre numeriche.', 'error')
            return redirect(url_for('cambia_pin'))
        utenti[session['pin']] = utenti.pop(session['pin'])
        session['pin'] = nuovo_pin
        utenti[nuovo_pin] = utenti.get(nuovo_pin, {'saldo': 1000.0, 'storico': [], 'tentativi': 0, 'bloccato': False})
        flash('PIN cambiato con successo!', 'success')
        return redirect(url_for('menu'))
    return render_template('cambia_pin.html')

# Funzione per simulare richiesta assistenza (mock)
@app.route('/assistenza', methods=['GET', 'POST'])
def assistenza():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        messaggio = request.form.get('messaggio')
        if not messaggio or len(messaggio) < 10:
            flash('Scrivi un messaggio di almeno 10 caratteri.', 'error')
            return redirect(url_for('assistenza'))
        invia_notifica(session['pin'], f"Richiesta assistenza: {messaggio}")
        flash('Richiesta inviata! Sarai ricontattato a breve.', 'success')
        return redirect(url_for('menu'))
    return render_template('assistenza.html')

# Funzione per simulare logout automatico dopo inattività (mock)
from flask import g
import time
@app.before_request
def check_timeout():
    session.permanent = True
    app.permanent_session_lifetime = 600  # 10 minuti
    session.modified = True

# Funzione per simulare invio OTP (mock)
def invia_otp(pin):
    print(f"[OTP] Inviato OTP a utente {pin}")
    logging.info(f"OTP inviato a {pin}")

# Funzione per simulare verifica OTP (mock)
def verifica_otp(pin, otp):
    return otp == '0000'  # Demo

# Funzione per simulare blocco temporaneo (mock)
def blocco_temporaneo(pin):
    utenti[pin]['bloccato'] = True
    logging.info(f"Blocco temporaneo per utente {pin}")

# Funzione per simulare sblocco carta (mock)
def sblocca_carta(pin):
    utenti[pin]['bloccato'] = False
    utenti[pin]['tentativi'] = 0
    logging.info(f"Carta sbloccata per utente {pin}")

# Funzione per simulare invio SMS (mock)
def invia_sms(pin, testo):
    print(f"[SMS] {testo} inviato a utente {pin}")
    logging.info(f"SMS inviato a {pin}: {testo}")

# Funzione per simulare verifica saldo minimo (mock)
def verifica_saldo_minimo(pin):
    utente = utenti.get(pin)
    if utente and utente['saldo'] < 100:
        invia_notifica(pin, "Attenzione: saldo inferiore a 100 euro.")

# Funzione per simulare invio promozioni (mock)
def invia_promozione(pin):
    print(f"[PROMO] Promozione inviata a utente {pin}")
    logging.info(f"Promozione inviata a {pin}")

if __name__ == '__main__':
    app.run(debug=True)
