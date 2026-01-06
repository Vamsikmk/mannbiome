#!/usr/bin/env python3
"""
Script to create the customer_recommendations table for LLM caching
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Database connection - same as used in DBCustomerPortal.py
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please configure your .env file.")

def create_recommendations_table():
    """Create the customer_recommendations table"""
    
    # SQL from create_recommendations_table.sql
    create_table_sql = """
-- Create the customer_recommendations table for caching LLM recommendations
-- Add this to your database schema

CREATE TABLE IF NOT EXISTS microbiome.customer_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers.customer(customer_id),
    domain_id INTEGER NOT NULL REFERENCES microbiome.health_domains(domain_id),
    
    -- Recommendation content (JSONB for flexibility)
    dietary_recommendations JSONB,
    lifestyle_recommendations JSONB,
    probiotic_recommendations JSONB,
    prebiotic_recommendations JSONB,
    summary TEXT,
    
    -- Metadata
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    model_version VARCHAR(50),
    
    -- Customer context at generation time
    customer_age INTEGER,
    domain_score DECIMAL(3,2),
    domain_diversity DECIMAL(3,2),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(customer_id, domain_id, is_active)
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_customer_recommendations_lookup 
ON microbiome.customer_recommendations(customer_id, domain_id, is_active);

CREATE INDEX IF NOT EXISTS idx_recommendations_expiry 
ON microbiome.customer_recommendations(expires_at);
"""

    try:
        print("🔗 Connecting to database...")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            print("✅ Database connection successful!")
            print("🏗️ Creating customer_recommendations table...")
            
            # Execute the SQL
            connection.execute(text(create_table_sql))
            connection.commit()
            
            print("✅ Table created successfully!")
            
            # Verify the table was created
            print("🔍 Verifying table creation...")
            result = connection.execute(text("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'microbiome' 
                AND table_name = 'customer_recommendations'
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            if columns:
                print("✅ Table verification successful!")
                print("\n📋 Table structure:")
                print("-" * 50)
                for row in columns:
                    print(f"  {row.column_name:25} | {row.data_type}")
                print("-" * 50)
                print(f"  Total columns: {len(columns)}")
            else:
                print("⚠️ Table created but verification failed")
            
            # Check indexes
            print("\n🔍 Checking indexes...")
            index_result = connection.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE schemaname = 'microbiome' 
                AND tablename = 'customer_recommendations';
            """))
            
            indexes = index_result.fetchall()
            if indexes:
                print("✅ Indexes created successfully!")
                print(f"  Total indexes: {len(indexes)}")
                for idx in indexes:
                    print(f"  - {idx.indexname}")
            
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def test_table_access():
    """Test basic operations on the new table"""
    try:
        print("\n🧪 Testing table access...")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Test insert/select permissions
            test_query = text("""
                SELECT COUNT(*) as row_count 
                FROM microbiome.customer_recommendations;
            """)
            
            result = connection.execute(test_query)
            count = result.fetchone()
            print(f"✅ Table access test successful! Current rows: {count.row_count}")
            
    except Exception as e:
        print(f"⚠️ Table access test failed: {e}")

if __name__ == "__main__":
    print("🚀 Creating MannBiome LLM Recommendations Cache Table")
    print("=" * 60)
    
    create_recommendations_table()
    test_table_access()
    
    print("\n🎉 Database setup complete!")
    print("\n📖 Next steps:")
    print("  1. Set ANTHROPIC_API_KEY environment variable")
    print("  2. Install requirements: pip install -r requirements.txt")
    print("  3. Test the API endpoints")