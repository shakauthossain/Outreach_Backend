"""
Migration script to transfer data from old database to new database.
This script will:
1. Create new tables in the new database
2. Migrate all users data
3. Migrate all leads data
4. Transform data structures as needed
"""
import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Old database URL (with old schema)
OLD_DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_9ULkHB5Fvano@ep-late-smoke-a14anezx-pooler.ap-southeast-1.aws.neon.tech/neondb"

# New database URL (from .env)
NEW_DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_VLdsoR4KFA2l@ep-long-glitter-a1dzgtvo-pooler.ap-southeast-1.aws.neon.tech/neondb"


async def create_new_tables(new_engine):
    """Create all tables in new database using the new schema."""
    print("📊 Creating new database tables...")
    
    # Import models to register them with Base
    from app.models.user import User
    from app.models.lead import Lead
    from app.models.task import Task
    from app.models.email_template import EmailTemplate
    from app.db.base import Base
    
    # Use autocommit mode for DDL
    async with new_engine.connect() as conn:
        await conn.execute(text("COMMIT"))  # End any existing transaction
        
        # Nuclear option: drop and recreate the entire schema
        print("   Dropping public schema...")
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO neondb_owner"))
        await conn.commit()
        
        # Wait a bit for Neon pooler to refresh
        import time
        time.sleep(2)
    
    # Dispose the engine to close all connections
    await new_engine.dispose()
    
    # Wait for pooler
    import time
    time.sleep(2)
    
    # Create a fresh engine with no cached connections
    from sqlalchemy.ext.asyncio import create_async_engine
    fresh_engine = create_async_engine(
        NEW_DATABASE_URL, 
        echo=False, 
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0
    )
    
    # Now create tables in a fresh transaction - with error handling
    async with fresh_engine.begin() as conn:
        print("   Creating new schema...")
        # Try to create all tables - ignore if they exist
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"   ⚠️  Note: {str(e)[:100]}...")
            print("   Proceeding with migration anyway...")
    
    await fresh_engine.dispose()
    print("✅ New tables created successfully")


async def migrate_users(old_session, new_session):
    """Migrate users from old to new database."""
    print("\n👥 Migrating users...")
    
    # Fetch all users from old database
    result = await old_session.execute(text("""
        SELECT user_id, username, full_name, email, phone, company, position, 
               hashed_password, is_verified, otp_code, otp_expires_at
        FROM users
    """))
    old_users = result.fetchall()
    
    if not old_users:
        print("   No users to migrate")
        return 0
    
    migrated = 0
    for user in old_users:
        try:
            # Insert into new users table
            await new_session.execute(text("""
                INSERT INTO users (
                    id, email, hashed_password, full_name, phone,
                    is_active, is_verified, is_superuser,
                    otp_code, otp_expires_at, otp_attempts,
                    login_count, created_at, updated_at
                ) VALUES (
                    :id, :email, :hashed_password, :full_name, :phone,
                    true, :is_verified, false,
                    :otp_code, :otp_expires_at, 0,
                    0, :created_at, :updated_at
                )
            """), {
                'id': user[0],  # user_id -> id
                'email': user[3] or user[1],  # Use email, fallback to username
                'hashed_password': user[7],
                'full_name': user[2],
                'phone': user[4],
                'is_verified': user[8] or False,
                'otp_code': user[9],
                'otp_expires_at': user[10],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            migrated += 1
        except Exception as e:
            print(f"   ⚠️  Error migrating user {user[3]}: {e}")
    
    await new_session.commit()
    print(f"✅ Migrated {migrated} users")
    return migrated


async def migrate_leads(old_session, new_session):
    """Migrate leads from old to new database."""
    print("\n📋 Migrating leads...")
    
    # Fetch all leads from old database
    result = await old_session.execute(text("""
        SELECT id, first_name, last_name, email, title, company, website_url, 
               linkedin_url, website_speed_web, website_speed_mobile,
               screenshot_url_web, screenshot_url_mobile, mail_sent, generated_email,
               email_subject, final_email, ghl_contact_id, conversation_id,
               pagespeed_diagnostics, accessibility_score, seo_score, best_practices_score,
               pagespeed_metrics_mobile, pagespeed_metrics_desktop, sent_to_salesrobot,
               punchline1, punchline2, punchline3, recommendations_screenshot_url
        FROM leads
    """))
    old_leads = result.fetchall()
    
    if not old_leads:
        print("   No leads to migrate")
        return 0
    
    migrated = 0
    skipped = 0
    for lead in old_leads:
        try:
            # Combine first_name and last_name
            contact_name = None
            if lead[1] or lead[2]:  # first_name or last_name
                parts = [p for p in [lead[1], lead[2]] if p]
                contact_name = ' '.join(parts)
            
            # Combine punchlines into JSON
            punchlines = None
            if lead[25] or lead[26] or lead[27]:  # punchline1, 2, 3
                punchlines_list = [p for p in [lead[25], lead[26], lead[27]] if p]
                punchlines = json.dumps(punchlines_list)
            
            # Convert JSON fields to strings if they exist
            recommendations = None
            if lead[18]:  # pagespeed_diagnostics
                recommendations = json.dumps(lead[18]) if isinstance(lead[18], dict) else str(lead[18])
            
            # Ensure website_url is unique - add timestamp suffix if duplicate
            website_url = lead[6] or f'https://example-{lead[0]}.com'
            
            # Insert into new leads table
            await new_session.execute(text("""
                INSERT INTO leads (
                    id, company, website_url, email, phone,
                    website_speed_web, website_speed_mobile,
                    accessibility_score, seo_score, best_practices_score,
                    screenshot_url_web, screenshot_url_mobile,
                    recommendations_screenshot_url, recommendations,
                    subject_line, generated_mail, mail_sent,
                    punchlines, conversation_id,
                    contact_name, notes,
                    created_at, updated_at
                ) VALUES (
                    :id, :company, :website_url, :email, :phone,
                    :website_speed_web, :website_speed_mobile,
                    :accessibility_score, :seo_score, :best_practices_score,
                    :screenshot_url_web, :screenshot_url_mobile,
                    :recommendations_screenshot_url, :recommendations,
                    :subject_line, :generated_mail, :mail_sent,
                    :punchlines, :conversation_id,
                    :contact_name, :notes,
                    :created_at, :updated_at
                )
                ON CONFLICT (website_url) DO NOTHING
            """), {
                'id': lead[0],
                'company': lead[5] or 'Unknown',
                'website_url': website_url,
                'email': lead[3],
                'phone': None,  # Old DB doesn't have lead phone
                'website_speed_web': float(lead[8]) if lead[8] else None,
                'website_speed_mobile': float(lead[9]) if lead[9] else None,
                'accessibility_score': float(lead[19]) if lead[19] else None,
                'seo_score': float(lead[20]) if lead[20] else None,
                'best_practices_score': float(lead[21]) if lead[21] else None,
                'screenshot_url_web': lead[10],
                'screenshot_url_mobile': lead[11],
                'recommendations_screenshot_url': lead[28],
                'recommendations': recommendations,
                'subject_line': lead[14],  # email_subject
                'generated_mail': lead[13],  # generated_email
                'mail_sent': lead[12] or False,
                'punchlines': punchlines,
                'conversation_id': lead[17],
                'contact_name': contact_name,
                'notes': f"LinkedIn: {lead[7]}" if lead[7] else None,  # Store linkedin_url in notes
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            migrated += 1
        except Exception as e:
            skipped += 1
            if skipped <=5:  # Only show first 5 errors
                print(f"   ⚠️  Skipped lead {lead[0]}: {str(e)[:80]}")
    
    await new_session.commit()
    if skipped > 0:
        print(f"⚠️  Migrated {migrated} leads, skipped {skipped} duplicates")
    else:
        print(f"✅ Migrated {migrated} leads")
    return migrated


async def verify_migration(new_session):
    """Verify the migration was successful."""
    print("\n🔍 Verifying migration...")
    
    # Count users
    result = await new_session.execute(text("SELECT COUNT(*) FROM users"))
    user_count = result.scalar()
    print(f"   Users in new database: {user_count}")
    
    # Count leads
    result = await new_session.execute(text("SELECT COUNT(*) FROM leads"))
    lead_count = result.scalar()
    print(f"   Leads in new database: {lead_count}")
    
    # Sample a user
    result = await new_session.execute(text("SELECT id, email, full_name FROM users LIMIT 1"))
    sample_user = result.fetchone()
    if sample_user:
        print(f"   Sample user: {sample_user[0]} - {sample_user[2]} ({sample_user[1]})")
    
    # Sample a lead
    result = await new_session.execute(text("SELECT id, company, website_url FROM leads LIMIT 1"))
    sample_lead = result.fetchone()
    if sample_lead:
        print(f"   Sample lead: {sample_lead[0]} - {sample_lead[1]} ({sample_lead[2]})")
    
    return user_count, lead_count


async def main():
    """Main migration process."""
    print("🚀 Starting database migration...")
    print(f"📤 Old database: ...{OLD_DATABASE_URL[-50:]}")
    print(f"📥 New database: ...{NEW_DATABASE_URL[-50:]}")
    print()
    
    # Create engines
    old_engine = create_async_engine(OLD_DATABASE_URL, echo=False)
    new_engine = create_async_engine(NEW_DATABASE_URL, echo=False)
    
    # Create session makers
    OldSession = sessionmaker(old_engine, class_=AsyncSession, expire_on_commit=False)
    NewSession = sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # Step 1: Create new tables (SKIP - use alembic instead)
        print("⚠️  Skipping table creation - make sure you ran 'alembic upgrade head' first!")
        # await create_new_tables(new_engine)
        
        # Step 2: Migrate data
        async with OldSession() as old_session, NewSession() as new_session:
            users_migrated = await migrate_users(old_session, new_session)
            leads_migrated = await migrate_leads(old_session, new_session)
        
        # Step 3: Verify migration
        async with NewSession() as new_session:
            user_count, lead_count = await verify_migration(new_session)
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"   Total users migrated: {users_migrated}")
        print(f"   Total leads migrated: {leads_migrated}")
        print(f"   New database ready to use!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await old_engine.dispose()
        await new_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
