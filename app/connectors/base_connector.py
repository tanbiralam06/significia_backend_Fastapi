from abc import ABC, abstractmethod
from typing import Any, List, Dict

class BaseConnector(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None

    @abstractmethod
    def connect(self):
        """Establish connection to the external database."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close the connection."""
        pass

    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the connection can be established."""
        pass
