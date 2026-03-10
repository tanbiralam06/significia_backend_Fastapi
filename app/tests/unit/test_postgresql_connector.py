import pytest
from unittest.mock import MagicMock, patch
from app.connectors.database.postgresql import PostgreSQLConnector

def test_postgresql_connector_test_connection_success():
    config = {
        "host": "localhost",
        "port": 5432,
        "database_name": "testdb",
        "username": "user",
        "password": "password"
    }
    
    with patch("psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        connector = PostgreSQLConnector(config)
        result = connector.test_connection()
        
        assert result is True
        mock_connect.assert_called_once()
        mock_conn.close.assert_called_once()

def test_postgresql_connector_test_connection_failure():
    config = {
        "host": "invalid-host",
        "port": 5432,
        "database_name": "testdb",
        "username": "user",
        "password": "password"
    }
    
    with patch("psycopg.connect") as mock_connect:
        mock_connect.side_effect = Exception("Connection failed")
        
        connector = PostgreSQLConnector(config)
        result = connector.test_connection()
        
        assert result is False
        mock_connect.assert_called_once()
