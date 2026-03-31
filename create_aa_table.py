import sqlite3
import os

def migrate():
    db_path = "financial_analysis.db"
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Creating asset_allocations table in local SQLite database...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS asset_allocations (
        id CHAR(36) PRIMARY KEY,
        client_id CHAR(36) NOT NULL,
        ia_registration_number VARCHAR(100) NOT NULL,
        assigned_risk_tier VARCHAR(100) NOT NULL,
        tier_recommendation TEXT NOT NULL,
        equities_percentage REAL DEFAULT 0.0,
        debt_securities_percentage REAL DEFAULT 0.0,
        commodities_percentage REAL DEFAULT 0.0,
        stocks_percentage REAL DEFAULT 0.0,
        mutual_fund_equity_percentage REAL DEFAULT 0.0,
        ulip_equity_percentage REAL DEFAULT 0.0,
        fixed_deposits_bonds_percentage REAL DEFAULT 0.0,
        mutual_fund_debt_percentage REAL DEFAULT 0.0,
        ulip_debt_percentage REAL DEFAULT 0.0,
        gold_etf_percentage REAL DEFAULT 0.0,
        silver_etf_percentage REAL DEFAULT 0.0,
        system_conclusion TEXT,
        generate_system_conclusion BOOLEAN DEFAULT 1,
        discussion_notes TEXT,
        disclaimer_text TEXT,
        total_allocation REAL DEFAULT 100.0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
    );
    """
    
    try:
        cursor.execute(create_table_sql)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_allocations_client ON asset_allocations(client_id);")
        conn.commit()
        print("Asset allocation table created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
