import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from app_skeleton.api.common import DB_CONN
from app_skeleton.api.supabase_config import postgres_conn

def sync_allowlist():
    conn_str = postgres_conn() or DB_CONN
    if not conn_str:
        print("No database connection string found.")
        return

    with psycopg.connect(conn_str, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            print("Fetching current members from platform.researcher...")
            cur.execute("SELECT username, email FROM platform.researcher WHERE email IS NOT NULL;")
            members = cur.fetchall()
            
            emails_to_allow = [m[1].strip().lower() for m in members if m[1]]
            print(f"Found {len(emails_to_allow)} valid emails in platform.researcher.")

            if not emails_to_allow:
                print("No emails found to sync.")
                return

            # Clear all current allowlist and insert only the current members
            print("Clearing old allowlist entries...")
            cur.execute("DELETE FROM platform.allowed_email;")

            print("Inserting current members into platform.allowed_email...")
            for email in emails_to_allow:
                cur.execute(
                    """
                    INSERT INTO platform.allowed_email (email, status) 
                    VALUES (%s, 'approved') 
                    ON CONFLICT (email) DO UPDATE SET status = 'approved';
                    """,
                    (email,)
                )
            
            conn.commit()
            print("Allowlist successfully synced with platform.researcher.")

if __name__ == "__main__":
    sync_allowlist()
