import sqlite3
from datetime import datetime
import csv

DB_NAME = "tickets.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            assigned_team TEXT,
            priority TEXT,
            deadline TEXT,
            submitted_by TEXT,
            thread_id TEXT,
            status TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_ticket(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO tickets (title, description, assigned_team, priority, deadline, submitted_by, thread_id, status, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data["title"],
        data["description"],
        data.get("assigned_team", ""),
        data.get("priority", ""),
        data.get("deadline", ""),
        data["submitted_by"],
        data["thread_id"],
        "open",
        datetime.utcnow().isoformat(),
        None
    ))
    conn.commit()
    conn.close()

def update_ticket(thread_id, assigned_team, priority, deadline):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE tickets
        SET assigned_team = ?, priority = ?, deadline = ?
        WHERE thread_id = ?
    ''', (assigned_team, priority, deadline, thread_id))
    conn.commit()
    conn.close()

def mark_ticket_completed(thread_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE tickets
        SET status = 'completed', completed_at = ?
        WHERE thread_id = ?
    ''', (datetime.utcnow().isoformat(), thread_id))
    conn.commit()
    conn.close()

def delete_ticket(thread_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM tickets WHERE thread_id = ?', (thread_id,))
    conn.commit()
    conn.close()

def export_ticket_performance_to_csv(csv_path="ticket_performance.csv"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT title, assigned_team, submitted_by, status, created_at, completed_at FROM tickets')
    rows = c.fetchall()
    conn.close()

    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Assigned Team", "Submitted By", "Status", "Created At", "Completed At", "Time Taken (hrs)"])
        for row in rows:
            created = datetime.fromisoformat(row[4]) if row[4] else None
            completed = datetime.fromisoformat(row[5]) if row[5] else None
            hours_taken = round((completed - created).total_seconds() / 3600, 2) if created and completed else ""
            writer.writerow(list(row) + [hours_taken])
