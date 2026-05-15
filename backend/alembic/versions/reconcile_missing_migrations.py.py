from alembic import op

revision = 'reconcile_missing'
down_revision = '90773a98bfa2'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE category AS ENUM ('SOCIAL','WORK','FINANCE','EMAIL','OTHER');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("ALTER TABLE vaults ADD COLUMN IF NOT EXISTS category category")

    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'email_changed'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'password_changed'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'account_deleted'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'session_revoked'")

def downgrade():
    op.execute("ALTER TABLE vaults DROP COLUMN IF EXISTS category")
    op.execute("DROP TYPE IF EXISTS category")

