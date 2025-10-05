import os
import sys
import logging
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any
import pandas as pd

# ✅ Conditional dotenv loading
if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file for local testing")
else:
    print("🌀 No .env file found - using system environment variables")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ComplianceEmailSystem:
    def __init__(self, db_path: str = "task_management.db"):
        self.db_path = db_path
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_username = os.environ.get("SMTP_USERNAME")
        self.smtp_password = os.environ.get("SMTP_PASSWORD")

        logger.info(
            f"SMTP Configuration: Server={self.smtp_server}, Port={self.smtp_port}, Username={self.smtp_username}"
        )

        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
            logger.error("❌ SMTP credentials are incomplete or missing!")
        self.data = None
    
    def load_database_data(self) -> bool:
        """Load and validate data from SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # FIXED: Join with users table to get actual email addresses
            query = """
            SELECT 
                t.domain as 'Domain',
                t.title as 'Task', 
                t.description as 'Task Description',
                u.email as 'Email',
                u.name as 'User Name',
                t.attachment as 'Attachment Link',
                t.status as 'Status',
                t.due_date as 'Due Date',
                t.frequency as 'Frequency'
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.user_id
            WHERE t.status = 'Pending'
            """
            
            self.data = pd.read_sql_query(query, conn)
            conn.close()
            
            # Validate required columns
            required_columns = ['Domain', 'Task', 'Task Description', 'Email', 'Attachment Link', 
                              'Status', 'Due Date', 'Frequency']
            missing_columns = [col for col in required_columns if col not in self.data.columns]
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                logger.error(f"Available columns: {list(self.data.columns)}")
                return False
                
            # Convert date columns
            self.data['Due Date'] = pd.to_datetime(self.data['Due Date']).dt.date
            
            # Fill missing domains with a default value if any
            if self.data['Domain'].isnull().any():
                logger.warning("Some tasks have missing Domain values, filling with 'General'")
                self.data['Domain'] = self.data['Domain'].fillna('General')
            
            # Filter out tasks without valid email addresses
            original_count = len(self.data)
            self.data = self.data[self.data['Email'].notna() & (self.data['Email'] != '')]
            if len(self.data) < original_count:
                logger.warning(f"Filtered out {original_count - len(self.data)} tasks without valid email addresses")
            
            logger.info(f"Successfully loaded {len(self.data)} tasks across {self.data['Domain'].nunique()} domains")
            logger.info(f"Users with tasks: {self.data['Email'].unique().tolist()}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            return False
    
    def filter_tasks_by_schedule(self, schedule_type: str) -> pd.DataFrame:
        """Filter tasks based on schedule type (monthly, quarterly, reminder, daily)"""
        today = datetime.now().date()
        
        if schedule_type == "monthly":
            # Monthly tasks - send on 1st of month
            if today.day != 1:
                logger.info("Not the 1st of month - skipping monthly tasks")
                return pd.DataFrame()
            
            monthly_tasks = self.data[
                (self.data['Frequency'].str.lower().str.contains('monthly', na=False)) &
                (self.data['Status'].str.lower() == 'pending')
            ]
            logger.info(f"Found {len(monthly_tasks)} monthly tasks across {monthly_tasks['Domain'].nunique()} domains")
            return monthly_tasks
            
        elif schedule_type == "quarterly":
            # Quarterly tasks - send on 25th of the last month of each quarter
            # Last months of quarters: March (3), June (6), September (9), December (12)
            quarter_months = [3, 6, 9, 12]
            current_month = today.month
            current_day = today.day
            
            # Check if today is 25th of a quarter-end month
            if current_month not in quarter_months or current_day != 25:
                logger.info(f"Not 25th of a quarter-end month (current: {today}) - skipping quarterly tasks")
                return pd.DataFrame()
            
            quarterly_tasks = self.data[
                (self.data['Frequency'].str.lower().str.contains('quarterly', na=False)) &
                (self.data['Status'].str.lower() == 'pending')
            ]
            logger.info(f"Found {len(quarterly_tasks)} quarterly tasks across {quarterly_tasks['Domain'].nunique()} domains")
            return quarterly_tasks
            
        elif schedule_type == "daily":
            # Daily tasks - send every day
            daily_tasks = self.data[
                (self.data['Status'].str.lower() == 'pending') &
                (self.data['Due Date'] >= today)
            ]
            logger.info(f"Found {len(daily_tasks)} tasks for daily reminders across {daily_tasks['Domain'].nunique()} domains")
            return daily_tasks
            
        elif schedule_type == "reminder":
            # Weekly reminders - send every Monday for pending tasks
            if today.weekday() != 0:  # Monday is 0
                logger.info("Not Monday - skipping weekly reminders")
                return pd.DataFrame()
            
            reminder_tasks = self.data[
                (self.data['Status'].str.lower() == 'pending') &
                (self.data['Due Date'] >= today)
            ]
            logger.info(f"Found {len(reminder_tasks)} tasks for reminders across {reminder_tasks['Domain'].nunique()} domains")
            return reminder_tasks
            
        else:
            logger.error(f"Unknown schedule type: {schedule_type}")
            return pd.DataFrame()
    
    def create_email_content(self, user_tasks: pd.DataFrame, schedule_type: str) -> str:
        """Create HTML email content for user tasks"""
        user_email = user_tasks['Email'].iloc[0]
        user_name = user_tasks['User Name'].iloc[0] if 'User Name' in user_tasks.columns and pd.notna(user_tasks['User Name'].iloc[0]) else 'User'
        task_count = len(user_tasks)
        
        email_type = schedule_type.capitalize()
        if schedule_type == "reminder":
            email_type = "Weekly Reminder"
        elif schedule_type == "daily":
            email_type = "Daily Reminder"
        
        # Group tasks by domain for better organization
        tasks_by_domain = user_tasks.groupby('Domain')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 5px; }}
                .domain-section {{ margin: 20px 0; padding: 15px; background-color: #e9ecef; border-radius: 5px; }}
                .domain-title {{ font-size: 1.2em; font-weight: bold; color: #495057; margin-bottom: 10px; }}
                .task-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .task-table th, .task-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                .task-table th {{ background-color: #4CAF50; color: white; }}
                .task-table tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .urgent {{ color: #ff6b6b; font-weight: bold; }}
                .footer {{ margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }}
                .summary {{ background-color: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                .quarter-notice {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #ffc107; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Compliance Task {email_type}</h2>
                <p>Hello {user_name}, you have {task_count} pending compliance task(s) across {len(tasks_by_domain)} domain(s)</p>
            </div>
        """
        
        # Add quarterly notice if applicable
        if schedule_type == "quarterly":
            html_content += """
            <div class="quarter-notice">
                <h3>📅 Quarterly Compliance Notice</h3>
                <p><strong>This is your quarterly compliance reminder.</strong> Please ensure all quarterly tasks are completed before the end of the current quarter.</p>
            </div>
            """
        
        html_content += f"""
            <div class="summary">
                <h3>📊 Task Summary by Domain:</h3>
                <ul>
        """
        
        # Add domain summary
        for domain, domain_tasks in tasks_by_domain:
            html_content += f'<li><strong>{domain}</strong>: {len(domain_tasks)} task(s)</li>'
        
        html_content += """
                </ul>
            </div>
        """
        
        # Add tasks organized by domain
        for domain, domain_tasks in tasks_by_domain:
            html_content += f"""
            <div class="domain-section">
                <div class="domain-title">🏢 Domain: {domain}</div>
                <table class="task-table">
                    <thead>
                        <tr>
                            <th>Task</th>
                            <th>Task Description</th>
                            <th>Deadline</th>
                            <th>Frequency</th>
                            <th>Attachment Link</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for _, task in domain_tasks.iterrows():
                days_remaining = (task['Due Date'] - datetime.now().date()).days
                urgent_class = "urgent" if days_remaining <= 3 else ""
                
                html_content += f"""
                        <tr>
                            <td><strong>{task['Task']}</strong></td>
                            <td>{task['Task Description']}</td>
                            <td class="{urgent_class}">{task['Due Date'].strftime('%Y-%m-%d')} ({days_remaining} days remaining)</td>
                            <td>{task['Frequency']}</td>
                            <td><a href="{task['Attachment Link']}" target="_blank">Upload Files</a></td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            </div>
            """
        
        html_content += f"""
            <div class="footer">
                <p><strong>Action Required:</strong> Please complete these tasks by their respective deadlines.</p>
                <p><strong>Note:</strong> This is an automated message. Please do not reply to this email.</p>
                <p><strong>Domains Affected:</strong> {", ".join(tasks_by_domain.groups.keys())}</p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email via SMTP"""
        try:
            if not all([self.smtp_username, self.smtp_password]):
                logger.error("SMTP credentials are incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username
            msg['To'] = to_email
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email with better error handling
            logger.info(f"Attempting to send email to {to_email}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def process_tasks(self, schedule_type: str, dry_run: bool = False) -> Dict[str, Any]:
        """Main processing function with dry run option"""
        if not self.load_database_data():
            return {"success": False, "error": "Failed to load database data"}
        
        # Filter tasks based on schedule
        filtered_tasks = self.filter_tasks_by_schedule(schedule_type)
        
        if filtered_tasks.empty:
            logger.info(f"No tasks to process for {schedule_type}")
            return {"success": True, "emails_sent": 0, "total_tasks": 0, "unique_users": 0, "domains_affected": 0}
        
        # Group tasks by email
        grouped_tasks = filtered_tasks.groupby('Email')
        emails_sent = 0
        emails_failed = 0
        
        email_subject = f"Compliance Task {schedule_type.capitalize()}"
        if schedule_type == "reminder":
            email_subject = "Weekly Compliance Task Reminder"
        elif schedule_type == "daily":
            email_subject = "Daily Compliance Task Reminder"
        elif schedule_type == "quarterly":
            email_subject = "Quarterly Compliance Task Reminder - Action Required"
        
        # Dry run mode
        if dry_run:
            logger.info("🚀 DRY RUN MODE - No emails will be actually sent")
            print(f"\n📋 DRY RUN RESULTS for {schedule_type}:")
            print(f"📧 Would send emails to {len(grouped_tasks)} users")
            print(f"📊 Would process {len(filtered_tasks)} tasks")
            print(f"🏢 Domains affected: {filtered_tasks['Domain'].nunique()}")
            
            for email, tasks in grouped_tasks:
                user_name = tasks['User Name'].iloc[0] if 'User Name' in tasks.columns and pd.notna(tasks['User Name'].iloc[0]) else 'Unknown'
                print(f"   📨 To: {user_name} ({email}), Tasks: {len(tasks)}")
                
            return {
                "success": True,
                "dry_run": True,
                "would_send_emails": len(grouped_tasks),
                "total_tasks": len(filtered_tasks),
                "domains_affected": filtered_tasks['Domain'].nunique()
            }
        
        # Actual email sending
        for email, tasks in grouped_tasks:
            # Create email content
            html_content = self.create_email_content(tasks, schedule_type)
            
            # Send email
            if self.send_email(email, email_subject, html_content):
                emails_sent += 1
            else:
                emails_failed += 1
        
        result = {
            "success": True,
            "emails_sent": emails_sent,
            "emails_failed": emails_failed,
            "total_tasks": len(filtered_tasks),
            "unique_users": len(grouped_tasks),
            "domains_affected": filtered_tasks['Domain'].nunique()
        }
        
        logger.info(f"Processing complete: {emails_sent} emails sent, {emails_failed} failed, {result['domains_affected']} domains affected")
        return result


def main():
    dry_run = "--dry-run" in sys.argv
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    if len(args) != 1:
        print("Usage: python script.py <schedule_type> [--dry-run]")
        print("Valid schedule types: daily, monthly, quarterly, reminder")
        sys.exit(1)

    schedule_type = args[0].lower()
    valid_types = ["daily", "monthly", "quarterly", "reminder"]

    if schedule_type not in valid_types:
        print(f"Invalid schedule type. Must be one of {valid_types}")
        sys.exit(1)

    db_file = "task_management.db"
    if not os.path.exists(db_file):
        logger.error(f"Database file not found: {db_file}")
        sys.exit(1)

    system = ComplianceEmailSystem(db_file)
    result = system.process_tasks(schedule_type, dry_run=dry_run)

    if result.get("success"):
        if dry_run:
            print(f"✅ DRY RUN completed for {schedule_type} tasks")
        else:
            print(f"✅ Successfully processed {schedule_type} tasks")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()