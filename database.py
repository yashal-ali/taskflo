from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import pandas as pd
import os
import streamlit as st


# ✅ Database Connection
def get_db_connection():
    """
    Creates a new SQLite connection.
    Database file stored in the same directory as the app.
    """
    db_path = "task_management.db"
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn


# ✅ Initialize Database (create tables if not exist)
def init_database():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        domain TEXT,
        assigned_to INTEGER,
        attachment TEXT,
        status TEXT DEFAULT 'Pending',
        due_date DATE,
        frequency TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_to) REFERENCES users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        user_id INTEGER,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    # Default Users
    users = [
        ('Admin','admin@company.com', 'admin'),
        ('Yashal Ali', 'yashalalifarooqui30@gmail.com', 'user'),
        ('Ali Yashal', 'aliyashal309@gmail.com', 'user'),
        ('Farooqui Yashal', 'farooquiyashal@gmail.com', 'user')
    ]

    for user in users:
        try:
            c.execute('INSERT INTO users (name, email, role) VALUES (?, ?, ?)', user)
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()


# ✅ Helper Functions
def get_user_by_email(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    return user


def get_all_users():
    conn = get_db_connection()
    df = pd.read_sql_query('SELECT * FROM users', conn)
    conn.close()
    return df


def create_task(title, description, domain, assigned_to, attachment, status, due_date, frequency):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO tasks (title, description, domain, assigned_to, attachment, status, due_date, frequency)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (title, description, domain, assigned_to, attachment, status, due_date, frequency))
    conn.commit()
    conn.close()


def get_tasks(user_id=None, role='user'):
    conn = get_db_connection()
    if role == 'admin':
        query = '''SELECT t.*, u.name as assigned_name, u.email as assigned_email,
                   (SELECT COUNT(*) FROM comments WHERE task_id = t.task_id) as comment_count
                   FROM tasks t
                   LEFT JOIN users u ON t.assigned_to = u.user_id
                   ORDER BY t.created_at DESC'''
        df = pd.read_sql_query(query, conn)
    else:
        query = '''SELECT t.*, u.name as assigned_name, u.email as assigned_email,
                   (SELECT COUNT(*) FROM comments WHERE task_id = t.task_id) as comment_count
                   FROM tasks t
                   LEFT JOIN users u ON t.assigned_to = u.user_id
                   WHERE t.assigned_to = ?
                   ORDER BY t.created_at DESC'''
        df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df


def update_task_status(task_id, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE task_id = ?', (status, task_id))
    conn.commit()
    conn.close()


def update_task(task_id, title, description, domain, assigned_to, attachment, status, due_date, frequency):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''UPDATE tasks SET title=?, description=?, domain=?, assigned_to=?, 
                 attachment=?, status=?, due_date=?, frequency=? WHERE task_id=?''',
              (title, description, domain, assigned_to, attachment, status, due_date, frequency, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM comments WHERE task_id = ?', (task_id,))
    c.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
    conn.commit()
    conn.close()


def get_comments(task_id):
    conn = get_db_connection()
    query = '''SELECT c.*, u.name, u.email FROM comments c
               JOIN users u ON c.user_id = u.user_id
               WHERE c.task_id = ?
               ORDER BY c.created_at ASC'''
    df = pd.read_sql_query(query, conn, params=(task_id,))
    conn.close()
    return df


def add_comment(task_id, user_id, comment_text):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO comments (task_id, user_id, comment_text) VALUES (?, ?, ?)',
              (task_id, user_id, comment_text))
    conn.commit()
    conn.close()


def add_user(name, email, role='user'):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (name, email, role) VALUES (?, ?, ?)', (name, email, role))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


# ✅ Email Summary Function
def send_email_summary(user_email, user_name, tasks_df, sender_email, sender_password):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Pending Tasks Summary – {datetime.now().strftime("%B %Y")}'
        msg['From'] = sender_email
        msg['To'] = user_email

        html = f"""
        <html>
          <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a202c; line-height: 1.6;">
            <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
              <div style="border-bottom: 3px solid #2563eb; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #1a202c; margin: 0 0 10px 0; font-size: 28px; font-weight: 700;">Task Summary Report</h1>
                <p style="color: #64748b; margin: 0; font-size: 16px;">Hello {user_name},</p>
              </div>
              <p style="color: #475569; font-size: 15px; margin-bottom: 25px;">Here are your pending tasks that require attention:</p>
              <table style="width: 100%; border-collapse: collapse; margin: 25px 0;">
                <thead>
                  <tr style="border-bottom: 2px solid #e2e8f0;">
                    <th style="padding: 12px 8px; text-align: left;">Task</th>
                    <th style="padding: 12px 8px; text-align: left;">Domain</th>
                    <th style="padding: 12px 8px; text-align: left;">Due Date</th>
                    <th style="padding: 12px 8px; text-align: left;">Frequency</th>
                    <th style="padding: 12px 8px; text-align: center;">Comments</th>
                  </tr>
                </thead>
                <tbody>
        """

        for _, task in tasks_df.iterrows():
            html += f"""
                  <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 12px 8px;"><b>{task['title']}</b><br><span style="color:#64748b;">{task['description'][:60]}...</span></td>
                    <td style="padding: 12px 8px;">{task['domain']}</td>
                    <td style="padding: 12px 8px;">{task['due_date']}</td>
                    <td style="padding: 12px 8px;">{task['frequency']}</td>
                    <td style="padding: 12px 8px; text-align:center; color:#2563eb;">{task['comment_count']}</td>
                  </tr>
            """

        html += """
                </tbody>
              </table>
              <div style="background-color:#f8fafc; border-left:3px solid #2563eb; padding:16px; margin:25px 0;">
                <p style="margin:0;">Please update task statuses once completed.</p>
              </div>
              <div style="margin-top:40px; border-top:1px solid #e2e8f0; padding-top:10px; color:#64748b; font-size:13px;">
                <p>Best regards,</p>
                <p style="font-weight:600; color:#475569;">TaskFlow Pro Admin</p>
              </div>
            </div>
          </body>
        </html>
        """

        part = MIMEText(html, 'html')
        msg.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return True

    except Exception as e:
        st.error(f"Error sending email to {user_email}: {str(e)}")
        return False
