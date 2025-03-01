import chromadb
import logging
from chromadb import PersistentClient, Collection

logger = logging.getLogger('chromadb-client')

class ChromaDBClient:
    _instance = None
    
    def __new__(cls) -> 'ChromaDBClient':
        if cls._instance is None:
            cls._instance = super(ChromaDBClient, cls).__new__(cls)
            cls._vector_db_path = "vectorDB"
            cls._client = chromadb.PersistentClient(path=cls._vector_db_path)
            try:
                cls._collection = cls._client.get_or_create_collection(name="my_collection")
                logger.info("ChromaDB client and collection initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {str(e)}")
                raise
        return cls._instance
    
    @property
    def client(self)-> PersistentClient:
        return self._client
    
    @property
    def collection(self) -> Collection:
        return self._collection

# Singleton instance
chroma_db = ChromaDBClient()