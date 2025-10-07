# from datetime import datetime, date
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# import sqlite3
# import pandas as pd
# import os
# import streamlit as st


# # ✅ Database Connection
# def get_db_connection():
#     """
#     Creates a new SQLite connection.
#     Database file stored in the same directory as the app.
#     """
#     db_path = "task_management.db"
#     conn = sqlite3.connect(db_path, check_same_thread=False)
#     return conn


# # ✅ Initialize Database (create tables if not exist)
# def init_database():
#     conn = get_db_connection()
#     c = conn.cursor()
    
#     # Create tables
#     c.execute('''CREATE TABLE IF NOT EXISTS users (
#         user_id INTEGER PRIMARY KEY AUTOINCREMENT,
#         name TEXT NOT NULL,
#         email TEXT UNIQUE NOT NULL,
#         role TEXT NOT NULL
#     )''')

#     c.execute('''CREATE TABLE IF NOT EXISTS tasks (
#         task_id INTEGER PRIMARY KEY AUTOINCREMENT,
#         title TEXT NOT NULL,
#         description TEXT,
#         domain TEXT,
#         assigned_to INTEGER,
#         attachment TEXT,
#         status TEXT DEFAULT 'Pending',
#         due_date DATE,
#         frequency TEXT,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         FOREIGN KEY (assigned_to) REFERENCES users(user_id)
#     )''')

#     c.execute('''CREATE TABLE IF NOT EXISTS comments (
#         comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
#         task_id INTEGER,
#         user_id INTEGER,
#         comment_text TEXT NOT NULL,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         FOREIGN KEY (task_id) REFERENCES tasks(task_id),
#         FOREIGN KEY (user_id) REFERENCES users(user_id)
#     )''')

#     # Default Users
#     users = [
#         ('Admin','admin@company.com', 'admin'),
#         ('Yashal Ali', 'yashalalifarooqui30@gmail.com', 'user'),
#         ('Ali Yashal', 'aliyashal309@gmail.com', 'user'),
#         ('Farooqui Yashal', 'farooquiyashal@gmail.com', 'user')
#     ]

#     for user in users:
#         try:
#             c.execute('INSERT INTO users (name, email, role) VALUES (?, ?, ?)', user)
#         except sqlite3.IntegrityError:
#             pass

#     conn.commit()
#     conn.close()


# # ✅ Helper Functions
# def get_user_by_email(email):
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute('SELECT * FROM users WHERE email = ?', (email,))
#     user = c.fetchone()
#     conn.close()
#     return user


# def get_all_users():
#     conn = get_db_connection()
#     df = pd.read_sql_query('SELECT * FROM users', conn)
#     conn.close()
#     return df


# def create_task(title, description, domain, assigned_to, attachment, status, due_date, frequency):
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute('''INSERT INTO tasks (title, description, domain, assigned_to, attachment, status, due_date, frequency)
#                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
#               (title, description, domain, assigned_to, attachment, status, due_date, frequency))
#     conn.commit()
#     conn.close()


# def get_tasks(user_id=None, role='user'):
#     conn = get_db_connection()
#     if role == 'admin':
#         query = '''SELECT t.*, u.name as assigned_name, u.email as assigned_email,
#                    (SELECT COUNT(*) FROM comments WHERE task_id = t.task_id) as comment_count
#                    FROM tasks t
#                    LEFT JOIN users u ON t.assigned_to = u.user_id
#                    ORDER BY t.created_at DESC'''
#         df = pd.read_sql_query(query, conn)
#     else:
#         query = '''SELECT t.*, u.name as assigned_name, u.email as assigned_email,
#                    (SELECT COUNT(*) FROM comments WHERE task_id = t.task_id) as comment_count
#                    FROM tasks t
#                    LEFT JOIN users u ON t.assigned_to = u.user_id
#                    WHERE t.assigned_to = ?
#                    ORDER BY t.created_at DESC'''
#         df = pd.read_sql_query(query, conn, params=(user_id,))
#     conn.close()
#     return df


# def update_task_status(task_id, status):
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute('UPDATE tasks SET status = ? WHERE task_id = ?', (status, task_id))
#     conn.commit()
#     conn.close()


# def update_task(task_id, title, description, domain, assigned_to, attachment, status, due_date, frequency):
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute('''UPDATE tasks SET title=?, description=?, domain=?, assigned_to=?, 
#                  attachment=?, status=?, due_date=?, frequency=? WHERE task_id=?''',
#               (title, description, domain, assigned_to, attachment, status, due_date, frequency, task_id))
#     conn.commit()
#     conn.close()


# def delete_task(task_id):
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute('DELETE FROM comments WHERE task_id = ?', (task_id,))
#     c.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
#     conn.commit()
#     conn.close()


# def get_comments(task_id):
#     conn = get_db_connection()
#     query = '''SELECT c.*, u.name, u.email FROM comments c
#                JOIN users u ON c.user_id = u.user_id
#                WHERE c.task_id = ?
#                ORDER BY c.created_at ASC'''
#     df = pd.read_sql_query(query, conn, params=(task_id,))
#     conn.close()
#     return df


# def add_comment(task_id, user_id, comment_text):
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute('INSERT INTO comments (task_id, user_id, comment_text) VALUES (?, ?, ?)',
#               (task_id, user_id, comment_text))
#     conn.commit()
#     conn.close()


# def add_user(name, email, role='user'):
#     conn = get_db_connection()
#     c = conn.cursor()
#     try:
#         c.execute('INSERT INTO users (name, email, role) VALUES (?, ?, ?)', (name, email, role))
#         conn.commit()
#         conn.close()
#         return True
#     except sqlite3.IntegrityError:
#         conn.close()
#         return False


# # ✅ Email Summary Function
# def send_email_summary(user_email, user_name, tasks_df, sender_email, sender_password):
#     try:
#         msg = MIMEMultipart('alternative')
#         msg['Subject'] = f'Pending Tasks Summary – {datetime.now().strftime("%B %Y")}'
#         msg['From'] = sender_email
#         msg['To'] = user_email

#         html = f"""
#         <html>
#           <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a202c; line-height: 1.6;">
#             <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
#               <div style="border-bottom: 3px solid #2563eb; padding-bottom: 20px; margin-bottom: 30px;">
#                 <h1 style="color: #1a202c; margin: 0 0 10px 0; font-size: 28px; font-weight: 700;">Task Summary Report</h1>
#                 <p style="color: #64748b; margin: 0; font-size: 16px;">Hello {user_name},</p>
#               </div>
#               <p style="color: #475569; font-size: 15px; margin-bottom: 25px;">Here are your pending tasks that require attention:</p>
#               <table style="width: 100%; border-collapse: collapse; margin: 25px 0;">
#                 <thead>
#                   <tr style="border-bottom: 2px solid #e2e8f0;">
#                     <th style="padding: 12px 8px; text-align: left;">Task</th>
#                     <th style="padding: 12px 8px; text-align: left;">Domain</th>
#                     <th style="padding: 12px 8px; text-align: left;">Due Date</th>
#                     <th style="padding: 12px 8px; text-align: left;">Frequency</th>
#                     <th style="padding: 12px 8px; text-align: center;">Comments</th>
#                   </tr>
#                 </thead>
#                 <tbody>
#         """

#         for _, task in tasks_df.iterrows():
#             html += f"""
#                   <tr style="border-bottom: 1px solid #e2e8f0;">
#                     <td style="padding: 12px 8px;"><b>{task['title']}</b><br><span style="color:#64748b;">{task['description'][:60]}...</span></td>
#                     <td style="padding: 12px 8px;">{task['domain']}</td>
#                     <td style="padding: 12px 8px;">{task['due_date']}</td>
#                     <td style="padding: 12px 8px;">{task['frequency']}</td>
#                     <td style="padding: 12px 8px; text-align:center; color:#2563eb;">{task['comment_count']}</td>
#                   </tr>
#             """

#         html += """
#                 </tbody>
#               </table>
#               <div style="background-color:#f8fafc; border-left:3px solid #2563eb; padding:16px; margin:25px 0;">
#                 <p style="margin:0;">Please update task statuses once completed.</p>
#               </div>
#               <div style="margin-top:40px; border-top:1px solid #e2e8f0; padding-top:10px; color:#64748b; font-size:13px;">
#                 <p>Best regards,</p>
#                 <p style="font-weight:600; color:#475569;">TaskFlow Pro Admin</p>
#               </div>
#             </div>
#           </body>
#         </html>
#         """

#         part = MIMEText(html, 'html')
#         msg.attach(part)

#         with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
#             server.login(sender_email, sender_password)
#             server.send_message(msg)

#         return True

#     except Exception as e:
#         st.error(f"Error sending email to {user_email}: {str(e)}")
#         return False


from pymongo import MongoClient
import streamlit as st
import pandas as pd
from datetime import datetime, date
from bson.objectid import ObjectId


# ✅ MongoDB Connection
@st.cache_resource
def get_db_connection():
    """
    Creates a MongoDB connection using Streamlit secrets.
    Connection is cached to avoid multiple connections.
    """
    try:
        # Get connection string from Streamlit secrets
        mongo_uri = st.secrets["mongodb"]["uri"]
        client = MongoClient(mongo_uri)
        
        # Test connection
        client.admin.command('ping')
        
        # Return database
        db = client['task_management_db']  # Database name
        return db
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {str(e)}")
        return None


# ✅ Initialize Database (create collections and default users)
def init_database():
    db = get_db_connection()
    if db is None:
        return
    
    # Collections (equivalent to SQL tables)
    users_collection = db['users']
    tasks_collection = db['tasks']
    comments_collection = db['comments']
    
    # Create indexes for better performance
    users_collection.create_index('email', unique=True)
    tasks_collection.create_index('assigned_to')
    comments_collection.create_index('task_id')
    
    # Default Users
    default_users = [
        {'name': 'Admin', 'email': 'admin@company.com', 'role': 'admin'},
        {'name': 'Yashal Ali', 'email': 'yashalalifarooqui30@gmail.com', 'role': 'user'},
        {'name': 'Ali Yashal', 'email': 'aliyashal309@gmail.com', 'role': 'user'},
        {'name': 'Farooqui Yashal', 'email': 'farooquiyashal@gmail.com', 'role': 'user'}
    ]
    
    for user in default_users:
        try:
            # Check if user already exists
            if users_collection.find_one({'email': user['email']}) is None:
                users_collection.insert_one(user)
        except Exception as e:
            pass  # User already exists


# ✅ Helper Functions
def get_user_by_email(email):
    """Get user by email address"""
    db = get_db_connection()
    if db is None:
        return None
    
    user = db['users'].find_one({'email': email})
    return user


def get_all_users():
    """Get all users as DataFrame"""
    db = get_db_connection()
    if db is None:
        return pd.DataFrame()
    
    users = list(db['users'].find())
    
    # Convert MongoDB _id to user_id for compatibility
    for user in users:
        user['user_id'] = str(user['_id'])
        del user['_id']
    
    return pd.DataFrame(users)


def create_task(title, description, domain, assigned_to, attachment, status, due_date, frequency):
    """Create a new task"""
    db = get_db_connection()
    if db is None:
        return
    if isinstance(due_date, date) and not isinstance(due_date, datetime):
        due_date = datetime.combine(due_date, datetime.min.time())
    
    task = {
        'title': title,
        'description': description,
        'domain': domain,
        'assigned_to': assigned_to,
        'attachment': attachment,
        'status': status,
        'due_date': due_date,
        'frequency': frequency,
        'created_at': datetime.now()
    }
    
    db['tasks'].insert_one(task)


def get_tasks(user_id=None, role='user'):
    """Get tasks with user info and comment counts"""
    db = get_db_connection()
    if db is None:
        return pd.DataFrame()
    
    # Build query based on role
    if role == 'admin':
        tasks = list(db['tasks'].find())
    else:
        tasks = list(db['tasks'].find({'assigned_to': user_id}))
    
    # Enrich tasks with user info and comment counts
    for task in tasks:
        task['task_id'] = str(task['_id'])
        del task['_id']
        
        # Get assigned user info
        if task.get('assigned_to'):
            user = db['users'].find_one({'_id': ObjectId(task['assigned_to'])})
            if user:
                task['assigned_name'] = user.get('name', 'Unknown')
                task['assigned_email'] = user.get('email', 'N/A')
            else:
                task['assigned_name'] = 'Unknown'
                task['assigned_email'] = 'N/A'
        else:
            task['assigned_name'] = 'Unassigned'
            task['assigned_email'] = 'N/A'
        
        # Count comments
        task['comment_count'] = db['comments'].count_documents({'task_id': task['task_id']})
    
    # Sort by created_at descending
    tasks.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    
    return pd.DataFrame(tasks)


def update_task_status(task_id, status):
    """Update task status"""
    db = get_db_connection()
    if db is None:
        return
    
    db['tasks'].update_one(
        {'_id': ObjectId(task_id)},
        {'$set': {'status': status}}
    )


def update_task(task_id, title, description, domain, assigned_to, attachment, status, due_date, frequency):
    """Update entire task"""
    db = get_db_connection()
    if db is None:
        return
    
    db['tasks'].update_one(
        {'_id': ObjectId(task_id)},
        {'$set': {
            'title': title,
            'description': description,
            'domain': domain,
            'assigned_to': assigned_to,
            'attachment': attachment,
            'status': status,
            'due_date': due_date,
            'frequency': frequency
        }}
    )


def delete_task(task_id):
    """Delete task and its comments"""
    db = get_db_connection()
    if db is None:
        return
    
    # Delete all comments for this task
    db['comments'].delete_many({'task_id': task_id})
    
    # Delete the task
    db['tasks'].delete_one({'_id': ObjectId(task_id)})


def get_comments(task_id):
    """Get all comments for a task"""
    db = get_db_connection()
    if db is None:
        return pd.DataFrame()
    
    comments = list(db['comments'].find({'task_id': task_id}))
    
    # Enrich with user info
    for comment in comments:
        comment['comment_id'] = str(comment['_id'])
        del comment['_id']
        
        # Get user info
        user = db['users'].find_one({'_id': ObjectId(comment['user_id'])})
        if user:
            comment['name'] = user.get('name', 'Unknown')
            comment['email'] = user.get('email', 'N/A')
        else:
            comment['name'] = 'Unknown'
            comment['email'] = 'N/A'
    
    # Sort by created_at ascending
    comments.sort(key=lambda x: x.get('created_at', datetime.min))
    
    return pd.DataFrame(comments)


def add_comment(task_id, user_id, comment_text):
    """Add a comment to a task"""
    db = get_db_connection()
    if db is None:
        return
    
    comment = {
        'task_id': task_id,
        'user_id': user_id,
        'comment_text': comment_text,
        'created_at': datetime.now()
    }
    
    db['comments'].insert_one(comment)


def add_user(name, email, role='user'):
    """Add a new user"""
    db = get_db_connection()
    if db is None:
        return False
    
    try:
        user = {
            'name': name,
            'email': email,
            'role': role
        }
        db['users'].insert_one(user)
        return True
    except Exception as e:
        # Duplicate email
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