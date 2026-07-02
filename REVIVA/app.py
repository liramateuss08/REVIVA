from flask import Flask, render_template
from datetime import datetime
import sqlite3
import serial
import threading
import time

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid_rfid TEXT,
            nome TEXT,
            curso TEXT,
            turma TEXT,
            checkin TEXT,
            checkout TEXT,
            total_horas TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM registros")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO registros (uid_rfid, nome, curso, turma, checkin, checkout, total_horas) VALUES ('A1 B2 C3 D4', 'Mateus Antônio', 'TDS', '3° TDS \"A\"', NULL, NULL, '--')")
        cursor.execute("INSERT INTO registros (uid_rfid, nome, curso, turma, checkin, checkout, total_horas) VALUES ('E5 F6 G7 H8', 'Ana Souza', 'Marketing', '1° MKT \"A\"', '08:00:00', NULL, 'Em contagem...')")
        conn.commit()
    conn.close()

def registrar_ponto(uid_cartao):
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, checkin, checkout FROM registros WHERE uid_rfid = ?", (uid_cartao,))
    aluno = cursor.fetchone()
    if aluno:
        aluno_id, nome, checkin, checkout = aluno
        hora_agora = datetime.now().strftime("%H:%M:%S")
        if not checkin:
            cursor.execute("UPDATE registros SET checkin = ?, total_horas = 'Em contagem...' WHERE id = ?", (hora_agora, aluno_id))
        elif checkin and not checkout:
            t1 = datetime.strptime(checkin, "%H:%M:%S")
            t2 = datetime.strptime(hora_agora, "%H:%M:%S")
            if (t2 - t1).seconds > 60:
                td = t2 - t1
                total = f"{td.seconds // 3600}h {(td.seconds % 3600) // 60}m"
                cursor.execute("UPDATE registros SET checkout = ?, total_horas = ? WHERE id = ?", (hora_agora, total, aluno_id))
        conn.commit()
    conn.close()

def escutar_arduino():
    try:
        porta_serial = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        while True:
            if porta_serial.in_waiting > 0:
                uid_cartao = porta_serial.readline().decode('utf-8').strip()
                if uid_cartao: registrar_ponto(uid_cartao)
            time.sleep(0.1)
    except: pass

@app.route('/')
def index(): return render_template('index.html')

@app.route('/curso/<nome_curso>')
def ver_curso(nome_curso):
    salas = ['1° TDS "A"', '1° TDS "B"', '2° TDS "A"', '2° TDS "B"', '3° TDS "A"', '3° TDS "B"'] if nome_curso.upper() == 'TDS' else ['1° MKT "A"', '1° MKT "B"', '2° MKT "A"', '2° MKT "B"', '3° MKT "A"', '3° MKT "B"']
    return render_template('turmas.html', curso=nome_curso, salas=salas)

@app.route('/turma/<nome_turma>')
def ver_turma(nome_turma):
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nome, checkin, checkout, total_horas FROM registros WHERE turma = ?", (nome_turma,))
    alunos = [{'nome': r[0], 'checkin': r[1] or '--', 'checkout': r[2] or '--', 'total': r[3]} for r in cursor.fetchall()]
    conn.close()
    return render_template('dashboard.html', turma=nome_turma, alunos=alunos)

if __name__ == '__main__':
    init_db()
    threading.Thread(target=escutar_arduino, daemon=True).start()
    app.run(debug=True, use_reloader=False)