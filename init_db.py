import sqlite3

conn = sqlite3.connect('student_result.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        photo TEXT,
        subject1 INTEGER NOT NULL,
        subject2 INTEGER NOT NULL,
        subject3 INTEGER NOT NULL
    )
''')

conn.commit()
conn.close()

print("✅ Database with extra fields created successfully.")
