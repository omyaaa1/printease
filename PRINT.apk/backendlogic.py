from flask import Flask, render_template, request, redirect, url_for, Response, send_from_directory
import os
import sqlite3
from datetime import datetime
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
import re
import random
import uuid

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_UPLOAD = os.path.join(BASE_DIR, 'uploads')
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', DEFAULT_UPLOAD)
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'printease_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_NAME = os.path.join(BASE_DIR, 'orders.db')
if os.environ.get('VERCEL'):
    DB_NAME = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'orders.db')


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
                    created_at TEXT,
                    tracking_code TEXT,
                    status TEXT
                )''')
    conn.commit()
    conn.close()


def ensure_columns():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("PRAGMA table_info(orders)")
    existing = {row[1] for row in c.fetchall()}
    if 'tracking_code' not in existing:
        c.execute("ALTER TABLE orders ADD COLUMN tracking_code TEXT")
    if 'status' not in existing:
        c.execute("ALTER TABLE orders ADD COLUMN status TEXT")
    conn.commit()
    if 'status' not in existing:
        c.execute("UPDATE orders SET status = 'Pending' WHERE status IS NULL OR status = ''")
    if 'tracking_code' not in existing:
        c.execute("SELECT id FROM orders WHERE tracking_code IS NULL OR tracking_code = ''")
        for (order_id,) in c.fetchall():
            c.execute("UPDATE orders SET tracking_code = ? WHERE id = ?", (f"PE{order_id:06d}", order_id))
    conn.commit()
    conn.close()


def generate_tracking_code():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    while True:
        code = f"PE-{uuid.uuid4().hex[:8].upper()}"
        c.execute("SELECT 1 FROM orders WHERE tracking_code = ?", (code,))
        if not c.fetchone():
            conn.close()
            return code


init_db()
ensure_columns()


def count_pdf_pages(filepath):
    try:
        reader = PdfReader(filepath)
        return len(reader.pages)
    except Exception:
        return 1


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
    return render_template('frontend.html', error=None)


@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('file')
    copies_list = request.form.getlist('copies')
    pages_list = request.form.getlist('pages')
    print_type = request.form['print_type']
    side = request.form['side']
    lamination = request.form['lamination']
    hostel = request.form.get('hostel', 'no')
    delivery = request.form.get('delivery', 'no') if hostel == 'yes' else 'no'
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    room_no = request.form.get('room_no', '') if delivery == 'yes' else ''

    if not name:
        return render_template('frontend.html', error="Name is required.")
    if not re.match(r'^\d{10}$', phone):
        return render_template('frontend.html', error="Invalid phone number. Please enter a 10 digit number.")
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return render_template('frontend.html', error="Invalid email address.")
    if delivery == 'yes' and not room_no:
        return render_template('frontend.html', error="Room number is required for delivery.")
    if not files or len(files) == 0 or files[0].filename == '':
        return render_template('frontend.html', error="Please select at least one file.")

    total_billing = 0
    details = []
    tracking_code = generate_tracking_code()

    for idx, file in enumerate(files):
        rand_suffix = random.randint(1000, 9999)
        clean_name = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{rand_suffix}_{clean_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
        except Exception as e:
            return render_template('frontend.html', error=f"Error uploading file: {file.filename}. {str(e)}")

        if filename.lower().endswith('.pdf'):
            pages = count_pdf_pages(filepath)
        else:
            try:
                pages = int(pages_list[idx]) if idx < len(pages_list) else 1
            except ValueError:
                pages = 1

        try:
            copies = int(copies_list[idx]) if idx < len(copies_list) else 1
        except ValueError:
            copies = 1

        total = calculate_price(print_type, side, lamination, copies, pages, delivery)
        total_billing += total

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO orders (filename, print_type, side, lamination, copies, pages, total, hostel, delivery, name, phone, email, room_no, created_at, tracking_code, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (filename, print_type, side, lamination, copies, pages, total, hostel, delivery, name, phone, email, room_no, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tracking_code, 'Pending'))
        conn.commit()
        conn.close()

        details.append({
            'filename': filename,
            'pages': pages,
            'copies': copies,
            'total': total
        })

    return render_template(
        'order_success.html',
        name=name,
        phone=phone,
        email=email,
        details=details,
        total_billing=total_billing,
        hostel=hostel,
        delivery=delivery,
        room_no=room_no,
        tracking_code=tracking_code
    )


@app.route('/admin')
def admin():
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if q:
        like = f"%{q}%"
        c.execute('''SELECT * FROM orders
                     WHERE tracking_code LIKE ? OR phone LIKE ? OR name LIKE ? OR email LIKE ?
                     ORDER BY id DESC''', (like, like, like, like))
    else:
        c.execute('SELECT * FROM orders ORDER BY id DESC')
    orders = c.fetchall()
    conn.close()

    return render_template('admin.html', orders=orders, q=q)


@app.route('/admin/update-status', methods=['POST'])
def update_status():
    order_id = request.form.get('order_id')
    status = request.form.get('status', 'Pending')
    if not order_id:
        return redirect(url_for('admin'))
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))


@app.route('/track', methods=['GET', 'POST'])
def track():
    order = None
    orders = []
    search = ''
    if request.method == 'POST':
        search = request.form.get('search', '').strip()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if search:
            if re.match(r'^PE-', search) or re.match(r'^PE\d+', search):
                c.execute('SELECT * FROM orders WHERE tracking_code = ? ORDER BY id DESC', (search,))
                order = c.fetchone()
            else:
                like = f"%{search}%"
                c.execute('''SELECT * FROM orders
                             WHERE phone LIKE ? OR email LIKE ? OR name LIKE ?
                             ORDER BY id DESC''', (like, like, like))
                orders = c.fetchall()
        conn.close()
    return render_template('track.html', order=order, orders=orders, search=search)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/export')
def export_orders():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM orders ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()

    def generate():
        header = ['ID', 'Filename', 'Print Type', 'Side', 'Lamination', 'Copies', 'Pages', 'Total', 'Hostel', 'Delivery', 'Name', 'Phone', 'Email', 'Room No', 'Created At', 'Tracking Code', 'Status']
        yield ','.join(header) + '\n'
        for row in rows:
            yield ','.join([str(x) for x in row]) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=orders.csv"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
