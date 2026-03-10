import psycopg
from typing import Any, List, Dict
from app.connectors.base_connector import BaseConnector

class PostgreSQLConnector(BaseConnector):
    def connect(self):
        if not self.connection:
            conn_str = (
                f"host={self.config['host']} "
                f"port={self.config['port']} "
                f"dbname={self.config['database_name']} "
                f"user={self.config['username']} "
                f"password={self.config['password']}"
            )
            self.connection = psycopg.connect(conn_str)
        return self.connection

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
            return []

    def test_connection(self) -> bool:
        try:
            conn = self.connect()
            conn.close()
            self.connection = None
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
