from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
import sqlite3
from datetime import datetime
from PyPDF2 import PdfReader
import re
import random
import csv

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_NAME = 'orders.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    print_type TEXT,
                    side TEXT,
                    lamination TEXT,
                    copies INTEGER,
                    pages INTEGER,
                    total INTEGER,
                    hostel TEXT,
                    delivery TEXT,
                    name TEXT,
                    phone TEXT,
                    email TEXT,
                    room_no TEXT,
                    created_at TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

def count_pdf_pages(filepath):
    try:
        reader = PdfReader(filepath)
        return len(reader.pages)
    except Exception:
        return 1  # fallback if unreadable

def calculate_price(print_type, side, lamination, copies, pages, delivery):
    if print_type == 'bw':
        rate = 3 if side == 'single' else 5
    else:
        rate = 20
    total = rate * copies * pages
    if lamination == 'yes':
        total += 25
    if delivery == 'yes':
        total += 10
    return total

@app.route('/')
def index():
    return render_template('frontend.html')

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('file')
    copies_list = request.form.getlist('copies')
    print_type = request.form['print_type']
    side = request.form['side']
    lamination = request.form['lamination']
    hostel = request.form.get('hostel', 'no')
    delivery = request.form.get('delivery', 'no') if hostel == 'yes' else 'no'
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    room_no = request.form.get('room_no', '') if delivery == 'yes' else ''

    # Backend validation
    if not re.match(r'^\d{10}$', phone):
        return "<h3>Error: Invalid phone number. Please enter a 10 digit number.</h3>"
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return "<h3>Error: Invalid email address.</h3>"

    total_billing = 0
    details = []

    for idx, file in enumerate(files):
        # Prevent duplicate filenames
        rand_suffix = random.randint(1000, 9999)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{rand_suffix}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
        except Exception as e:
            return f"<h3>Error uploading file: {file.filename}</h3><p>{str(e)}</p>"

        # Count pages for PDF, else assume 1 page
        if filename.lower().endswith('.pdf'):
            pages = count_pdf_pages(filepath)
        else:
            pages = 1

        copies = int(copies_list[idx]) if idx < len(copies_list) else 1
        total = calculate_price(print_type, side, lamination, copies, pages, delivery)
        total_billing += total

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO orders (filename, print_type, side, lamination, copies, pages, total, hostel, delivery, name, phone, email, room_no, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (filename, print_type, side, lamination, copies, pages, total, hostel, delivery, name, phone, email, room_no, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()

        details.append(f"File: {filename} | Pages: {pages} | Copies: {copies} | Price: ₹{total}")

    if hostel == 'yes' and delivery == 'yes':
        details.append(f"<b>Room Delivery Charge: ₹10</b><br>Room No: {room_no}")

    detail_html = "<br>".join(details)
    return f"<h3>Order Received!</h3><p>Name: {name}<br>Phone: {phone}<br>Email: {email}<br>{detail_html}<br><b>Total Billing: ₹{total_billing}</b></p><a href='/admin'>Go to Admin Panel</a>"

@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM orders ORDER BY id DESC')
    orders = c.fetchall()
    conn.close()

    html = "<h2>Admin Dashboard</h2><table border='1' cellpadding='5'><tr><th>ID</th><th>File</th><th>Type</th><th>Side</th><th>Lamination</th><th>Copies</th><th>Pages</th><th>Total</th><th>Hostel</th><th>Delivery</th><th>Name</th><th>Phone</th><th>Email</th><th>Room No</th><th>Date</th><th>Download</th></tr>"
    for o in orders:
        file_link = f"<a href='/download/{o[1]}' target='_blank'>Download</a>"
        html += f"<tr><td>{o[0]}</td><td>{o[1]}</td><td>{o[2]}</td><td>{o[3]}</td><td>{o[4]}</td><td>{o[5]}</td><td>{o[6]}</td><td>₹{o[7]}</td><td>{o[8]}</td><td>{o[9]}</td><td>{o[10]}</td><td>{o[11]}</td><td>{o[12]}</td><td>{o[13]}</td><td>{o[14]}</td><td>{file_link}</td></tr>"
    html += "</table>"
    return html

@app.route('/download/<filename>')
def download(filename):
    return redirect(url_for('static', filename=f'../uploads/{filename}'))

@app.route('/export')
def export_orders():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM orders')
    rows = c.fetchall()
    conn.close()

    def generate():
        header = ['ID', 'Filename', 'Print Type', 'Side', 'Lamination', 'Copies', 'Pages', 'Total', 'Hostel', 'Delivery', 'Name', 'Phone', 'Email', 'Room No', 'Created At']
        yield ','.join(header) + '\n'
        for row in rows:
            yield ','.join([str(x) for x in row]) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=orders.csv"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)