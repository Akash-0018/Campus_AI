"""Embeddings service for Campus AI using ChromaDB"""
import logging
from typing import List, Optional
import chromadb
from sentence_transformers import SentenceTransformer
from utils.config import CHROMA_PERSISTENT_PATH, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Service for managing embeddings with ChromaDB"""
    
    def __init__(self):
        """Initialize ChromaDB client and embedding model"""
        try:
            logger.info("[EMBEDDINGS_INIT_START] Initializing EmbeddingsService...")
            # Initialize ChromaDB with persistent storage (new API)
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSISTENT_PATH)
            logger.info(f"[EMBEDDINGS_INIT] ChromaDB client initialized at: {CHROMA_PERSISTENT_PATH}")
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"[EMBEDDINGS_INIT_SUCCESS] EmbeddingsService initialized with model: {EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"[EMBEDDINGS_INIT_ERROR] Failed to initialize EmbeddingsService: {e}", exc_info=True)
            raise
    
    def get_or_create_collection(self, collection_name: str) -> any:
        """Get or create a ChromaDB collection"""
        try:
            logger.debug(f"[COLLECTION_MANAGER] Getting or creating collection: {collection_name}")
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.debug(f"[COLLECTION_MANAGER_SUCCESS] Collection ready: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"[COLLECTION_MANAGER_ERROR] Error getting or creating collection '{collection_name}': {e}", exc_info=True)
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        try:
            logger.info(
                f"[EMBEDDINGS-AGENT] Starting text-to-embedding conversion | "
                f"text_length={len(text)} characters | "
                f"model={EMBEDDING_MODEL}"
            )
            
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()
            
            logger.info(
                f"[EMBEDDINGS-AGENT] ✓ Embedding generated successfully | "
                f"dimension={len(embedding_list)} | "
                f"model={EMBEDDING_MODEL}"
            )
            return embedding_list
        except Exception as e:
            logger.error(f"[EMBEDDINGS-AGENT] ✗ Error embedding text: {e}", exc_info=True)
            raise
    
    def build_resume_query(self, query_history: List[str]) -> str:
        """Build a single semantic query from query history"""
        if isinstance(query_history, str):
            return query_history
        if isinstance(query_history, list):
            return " ".join(filter(None, query_history))
        return str(query_history)
    
    def add_document(
        self, 
        collection_name: str, 
        document_id: str,
        text: str,
        metadata: Optional[dict] = None
    ) -> str:
        """Add document to collection with embeddings"""
        try:
            logger.info(f"[STORAGE_START] Starting document storage process...")
            logger.info(f"[STORAGE_PARAMS] Collection: {collection_name}, Document ID: {document_id}")
            logger.info(f"[STORAGE_DATABASE_INFO] ChromaDB Collection: {collection_name} (Persistent path: {CHROMA_PERSISTENT_PATH})")
            
            collection = self.get_or_create_collection(collection_name)
            logger.info(f"[STORAGE_COLLECTION] Collection '{collection_name}' ready")
            
            logger.info(f"[STORAGE_EMBEDDING] Generating embedding for document...")
            embedding = self.embed_text(text)
            logger.info(f"[STORAGE_EMBEDDING_DONE] Embedding generated with dimension: {len(embedding)}")
            
            logger.info(f"[STORAGE_CHROMA_DB] Storing document in ChromaDB...")
            logger.info(f"[STORAGE_METADATA] Metadata: {metadata}")
            
            collection.add(
                ids=[document_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata or {}]
            )
            
            logger.info(f"[STORAGE_CHROMA_SUCCESS] Document stored in ChromaDB: {document_id}")
            logger.info(f"[STORAGE_COMPLETE] Document successfully stored in ChromaDB collection '{collection_name}' with ID: {document_id}")
            return document_id
        except Exception as e:
            logger.error(f"[STORAGE_ERROR] Error adding document to collection: {e}", exc_info=True)
            raise
    
    def search_resumes(
        self,
        collection_name: str,
        query_history: List[str],
        top_k: int = 2,
        min_similarity: float = 0.65
    ) -> List[dict]:
        """
        Semantic resume retrieval using multi-turn query context

        Args:
            collection_name: ChromaDB collection
            query_history: List of user queries (initial + follow-ups)
            top_k: Always 2 for resume shortlisting
            min_similarity: Strong threshold for resumes
        """
        try:
            logger.info(f"[SEARCH_RESUMES_START] Starting resume search in collection: {collection_name}")
            logger.info(f"[SEARCH_PARAMS] Query history: {query_history}, Top K: {top_k}, Min similarity: {min_similarity}")
            
            collection = self.get_or_create_collection(collection_name)

            # 1️⃣ Build a single semantic query
            combined_query = self.build_resume_query(query_history)
            logger.info(f"[SEARCH_QUERY_BUILT] Combined query: {combined_query}")

            # 2️⃣ Embed combined query
            logger.info(f"[SEARCH_EMBEDDING_START] Generating embedding for search query...")
            query_embedding = self.embed_text(combined_query)
            logger.info(f"[SEARCH_EMBEDDING_SUCCESS] Query embedding generated: dimension={len(query_embedding)}")

            # 3️⃣ Retrieve more candidates than needed
            logger.info(f"[SEARCH_RETRIEVAL_START] Retrieving candidates from ChromaDB (requesting 15 for filtering)...")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=15,
                include=["documents", "metadatas", "distances"]
            )
            logger.info(f"[SEARCH_RETRIEVAL_SUCCESS] Retrieved {len(results['ids'][0]) if results['ids'] else 0} candidates from ChromaDB")

            shortlisted = []

            if results and results["ids"]:
                logger.info(f"[SEARCH_FILTERING_START] Filtering candidates by similarity threshold: {min_similarity}")
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]

                    # Cosine similarity (safe & correct)
                    similarity = max(0.0, 1 - distance)

                    if similarity >= min_similarity:
                        shortlisted.append({
                            "id": doc_id,
                            "document": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "similarity": round(similarity, 4)
                        })
                        logger.debug(f"[SEARCH_MATCH] Candidate {doc_id} - Similarity: {similarity}")

            # 4️⃣ Sort strictly by similarity
            shortlisted.sort(key=lambda x: x["similarity"], reverse=True)
            logger.info(f"[SEARCH_FILTERING_COMPLETE] Candidates filtered and sorted: {len(shortlisted)} qualified candidates")

            # 5️⃣ Return TOP-2 only
            result = shortlisted[:top_k]
            logger.info(f"[SEARCH_COMPLETE] Search complete - Returning top {len(result)} candidates")
            for i, candidate in enumerate(result, 1):
                logger.info(f"[SEARCH_RESULT_{i}] ID: {candidate['id']}, Similarity: {candidate['similarity']}")
            
            return result

        except Exception as e:
            logger.error(f"[SEARCH_ERROR] Resume search failed: {e}", exc_info=True)
            raise
    
    def search(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 2,
        min_similarity: float = 0.65,
        allowed_ids: list[str] = None
    ) -> List[dict]:
        """
        Generic search method for profile queries with flexible parameters.
        Converts single query_text to query_history list format for search_resumes.
        
        Args:
            collection_name: ChromaDB collection name
            query_text: Single query string (or list of queries)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
        
        Returns:
            List of matching documents with metadata and similarity scores
        """
        try:
            logger.info(f"[SEARCH_START] Starting generic search in collection: {collection_name}")
            # Convert single query to list format
            query_history = [query_text] if isinstance(query_text, str) else query_text
            logger.info(f"[SEARCH_FORMAT] Query converted to history format: {query_history}")
            
            # Use search_resumes with the converted format
            result = self.search_resumes(
                collection_name=collection_name,
                query_history=query_history,
                top_k=top_k,
                min_similarity=min_similarity
            )
            logger.info(f"[SEARCH_GENERIC_COMPLETE] Generic search completed")
            return result
        except Exception as e:
            logger.error(f"[SEARCH_GENERIC_ERROR] Search failed: {e}", exc_info=True)
            raise

    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Delete document from collection"""
        try:
            logger.info(f"[DELETE_DOCUMENT_START] Deleting document: {document_id} from collection: {collection_name}")
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=[document_id])
            logger.info(f"[DELETE_DOCUMENT_SUCCESS] Document {document_id} deleted from collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"[DELETE_DOCUMENT_ERROR] Error deleting document: {e}", exc_info=True)
            raise
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete entire collection"""
        try:
            logger.info(f"[DELETE_COLLECTION_START] Deleting collection: {collection_name}")
            self.chroma_client.delete_collection(name=collection_name)
            logger.info(f"[DELETE_COLLECTION_SUCCESS] Collection {collection_name} deleted")
            return True
        except Exception as e:
            logger.error(f"[DELETE_COLLECTION_ERROR] Error deleting collection: {e}", exc_info=True)
            raise

# Global embeddings service instance
embeddings_service = EmbeddingsService()

