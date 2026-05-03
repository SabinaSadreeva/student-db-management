from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3, os
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('student_result.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.form['username'] == 'admin' and request.form['password'] == 'admin':
        session['user'] = 'admin'
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', error="Invalid credentials")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))

    # Получаем параметры фильтрации из URL
    subject_filter = request.args.get('subject_filter', '')
    min_total = request.args.get('min_total', '')
    keyword = request.args.get('keyword', '')  # поиск по имени

    conn = get_db_connection()

    # Базовый запрос с поиском по имени
    if keyword:
        students = conn.execute(
            "SELECT * FROM students WHERE name LIKE ?",
            ('%' + keyword + '%',)
        ).fetchall()
    else:
        students = conn.execute('SELECT * FROM students').fetchall()

    # Фильтрация в Python (по предмету и сумме баллов)
    filtered_students = []
    for s in students:
        total = s['subject1'] + s['subject2'] + s['subject3']
        
        # Фильтр по предмету (показываем студентов, у кого по выбранному предмету >= 50 баллов)
        if subject_filter:
            if subject_filter == '1' and s['subject1'] < 50:
                continue
            if subject_filter == '2' and s['subject2'] < 50:
                continue
            if subject_filter == '3' and s['subject3'] < 50:
                continue
        
        # Фильтр по минимальной сумме баллов
        if min_total and total < int(min_total):
            continue
        
        filtered_students.append(s)
    
    students = filtered_students

    # Подсчёт статистики только для отфильтрованных студентов
    if students:
        total_avg = sum(s['subject1'] + s['subject2'] + s['subject3'] for s in students) / (len(students) * 3)
        topper = max(students, key=lambda s: s['subject1'] + s['subject2'] + s['subject3'])
        total_count = len(students)
    else:
        total_avg = 0
        topper = None
        total_count = 0

    conn.close()
    
    return render_template('dashboard.html', 
                         students=students, 
                         total=total_count, 
                         avg=total_avg, 
                         topper=topper)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        gender = request.form['gender']
        s1 = request.form['subject1']
        s2 = request.form['subject2']
        s3 = request.form['subject3']
        photo = request.files['photo']

        if not (name and gender and s1.isdigit() and s2.isdigit() and s3.isdigit()):
            flash("Please fill in all fields correctly.")
            return redirect(url_for('add_student'))

        filename = None
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute('INSERT INTO students (name, gender, subject1, subject2, subject3, photo) VALUES (?, ?, ?, ?, ?, ?)',
                     (name, gender, int(s1), int(s2), int(s3), filename))
        conn.commit()
        conn.close()
        flash("Student added successfully.")
        return redirect(url_for('dashboard'))

    return render_template('add_student.html')

@app.route('/delete_student/<int:id>')
def delete_student(id):
    if 'user' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    student = conn.execute('SELECT photo FROM students WHERE id = ?', (id,)).fetchone()
    if student and student["photo"]:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], student["photo"])
        if os.path.exists(photo_path):
            os.remove(photo_path)
    conn.execute('DELETE FROM students WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Student deleted successfully.")
    return redirect(url_for('dashboard'))

@app.route('/search', methods=['POST'])
def search():
    if 'user' not in session:
        return redirect(url_for('home'))
    keyword = request.form['keyword']
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students WHERE name LIKE ?", ('%' + keyword + '%',)).fetchall()
    conn.close()
    return render_template('dashboard.html', students=students, total=None, avg=None, topper=None)

@app.route('/export_pdf/<int:id>')
def export_pdf(id):
    conn = get_db_connection()
    s = conn.execute('SELECT * FROM students WHERE id = ?', (id,)).fetchone()
    conn.close()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Student Result Card")

    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Name: {s['name']}")
    p.drawString(100, 750, f"Gender: {s['gender']}")
    p.drawString(100, 730, f"Subject 1 Marks: {s['subject1']}")
    p.drawString(100, 710, f"Subject 2 Marks: {s['subject2']}")
    p.drawString(100, 690, f"Subject 3 Marks: {s['subject3']}")
    total = s['subject1'] + s['subject2'] + s['subject3']
    p.drawString(100, 670, f"Total: {total}")
    grade = "A" if total >= 270 else "B" if total >= 210 else "C"
    p.drawString(100, 650, f"Grade: {grade}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='result.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
