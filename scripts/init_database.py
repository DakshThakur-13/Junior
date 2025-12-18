"""
Script to initialize Supabase database with schema and demo data

USAGE:
1. Go to your Supabase Dashboard > SQL Editor
2. Copy and paste the contents of src/junior/db/schema.sql
3. Run it to create tables and functions
4. Then copy and paste src/junior/db/demo_data.sql
5. Run it to insert demo data

OR run this script to insert demo data programmatically:
"""
from pathlib import Path
from junior.db.client import get_supabase_client
from junior.core import get_logger

logger = get_logger(__name__)

def insert_demo_data():
    """Insert demo data using Supabase Python client"""
    try:
        client = get_supabase_client()
        logger.info("✓ Connected to Supabase")
        
        print("=" * 70)
        print("Junior Database - Demo Data Insertion")
        print("=" * 70)
        
        # Insert demo users
        print("\n📊 Inserting demo users...")
        users = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "email": "advocate.sharma@example.com",
                "name": "Adv. Rajesh Sharma",
                "role": "lawyer",
                "bar_council_id": "BAR/DL/2015/12345",
                "preferred_language": "ENGLISH",
                "subscription_tier": "pro",
                "is_active": True
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "email": "adv.priya@example.com",
                "name": "Adv. Priya Menon",
                "role": "lawyer",
                "bar_council_id": "BAR/KA/2018/67890",
                "preferred_language": "HINDI",
                "subscription_tier": "enterprise",
                "is_active": True
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "email": "student.kumar@example.com",
                "name": "Amit Kumar",
                "role": "student",
                "preferred_language": "ENGLISH",
                "subscription_tier": "free",
                "is_active": True
            }
        ]
        
        for user in users:
            try:
                client.users.upsert(user).execute()
                print(f"  ✓ {user['name']}")
            except Exception as e:
                print(f"  ⚠ {user['name']}: {e}")
        
        print("\n✓ Database setup complete!")
        print("\n" + "=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print("\n1. Apply Schema (SQL Editor):")
        print("   • Go to Supabase Dashboard > SQL Editor")
        print(f"   • Copy: src/junior/db/schema.sql")
        print("   • Paste and run in SQL Editor")
        print("\n2. Insert Full Demo Data (SQL Editor):")
        print(f"   • Copy: src/junior/db/demo_data.sql")
        print("   • Paste and run in SQL Editor")
        print("\n3. Verify:")
        print("   • 7 landmark Supreme Court cases")
        print("   • Document chunks for semantic search")
        print("   • Case citations and relationships")
        print("   • Sample chat sessions")
        print("\n" + "=" * 70)
        
        # Print SQL file locations
        db_path = Path(__file__).parent.parent / "src" / "junior" / "db"
        print(f"\nSQL Files Location:")
        print(f"  Schema: {db_path / 'schema.sql'}")
        print(f"  Demo Data: {db_path / 'demo_data.sql'}")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        print("\n" + "=" * 70)
        print("✗ Failed. Check your Supabase credentials in .env")
        print("=" * 70)
        raise

if __name__ == "__main__":
    insert_demo_data()
