import sqlite3

conn = sqlite3.connect('dredge_remote.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS winch_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    file_name TEXT,
    cruise TEXT,
    start_time TEXT,
    end_time TEXT,
    settings TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS dredge_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date TEXT,
    start_time TEXT,
    end_date TEXT,
    end_time TEXT,
    cruise TEXT,
    cast_id TEXT,
    notes TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    file_name TEXT,
    cruise TEXT,
    cast_id TEXT,
    sensor_type TEXT,
    start_time TEXT,
    end_time TEXT,
    settings TEXT
)
''')

conn.commit()
conn.close()