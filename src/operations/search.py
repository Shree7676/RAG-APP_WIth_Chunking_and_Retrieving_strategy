import logging
from typing import List, Dict, Optional
from src.api import embed_texts
from .chromadb_client import chroma_db
import numpy as np
from keybert import KeyBERT

logger = logging.getLogger('search')

class SearchEngine:
    """
        A class to retrieve relevant chunks from a Chroma vector database based on a query.
        Retrieval strategy:
            - Embeds the query and retrieves initial matches via vector similarity.
            - Refines results using metadata (keywords, summary, description, filename).
            - Combines vector similarity and metadata scores to rank and return top-k chunks.
    """

    def __init__(self, collection_name: str = "default_collection"):
        """Initialize the SearchEngine with a Chroma collection."""
        self.collection = chroma_db.collection
        self.kw_model = KeyBERT()
        logger.info(f"Initialized SearchEngine with collection: {collection_name}")

    def retrieve(self, query: str, top_k: int = 5, filename_filter: Optional[str] = None) -> List[Dict]:
        """Retrieve top-k relevant chunks for a query using embeddings and metadata."""
        logger.info(f"Retrieving top-{top_k} chunks for query: '{query}'")

        # Step 1: Embed the query
        try:
            query_embedding = embed_texts([query], 'query')[0]
            logger.debug("Generated query embedding")
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            raise

        # Step 2: Initial vector search with Chroma
        filter_dict = {"filename": filename_filter} if filename_filter else None
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Fetch more (e.g., 10) for metadata refinement
            where=filter_dict,
            include=["documents", "metadatas", "distances"]
        )
        initial_count = len(results["documents"][0])
        logger.info(f"Retrieved {initial_count} initial matches from vector DB")

        # Step 3: Metadata-based refinement
        query_keywords = set(
            kw[0] for kw in self.kw_model.extract_keywords(
                query, keyphrase_ngram_range=(1, 3), top_n=5, stop_words=None
            )
        )
        retrieved_chunks = []

        for doc, metadata, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            # Extract metadata fields
            chunk_keywords = set(metadata.get("section_keywords", "").split(", "))
            summary = metadata.get("summary", "")
            description = metadata.get("description", "")
            filename = metadata.get("filename", "")

            # Calculate metadata relevance score
            keyword_overlap = len(query_keywords.intersection(chunk_keywords))
            summary_overlap = sum(1 for kw in query_keywords if kw.lower() in summary.lower())
            description_overlap = sum(1 for kw in query_keywords if kw.lower() in description.lower())
            filename_bonus = 1 if any(kw.lower() in filename.lower() for kw in query_keywords) else 0
            metadata_score = keyword_overlap + summary_overlap + description_overlap + filename_bonus

            # Normalize metadata score (optional, max could be dynamic)
            normalized_metadata_score = min(metadata_score / 5.0, 1.0)  # Cap at 5 keywords for normalization

            # Combine scores
            vector_similarity = 1 - distance  # Distance (0-1) to similarity (0-1)
            combined_score = vector_similarity * 0.7 + normalized_metadata_score * 0.3

            retrieved_chunks.append({
                "content": doc,
                "metadata": metadata,
                "vector_similarity": vector_similarity,
                "metadata_score": metadata_score,  # Raw score for transparency
                "combined_score": combined_score
            })

        # Step 4: Sort by combined score and return top-k
        retrieved_chunks = sorted(retrieved_chunks, key=lambda x: x["combined_score"], reverse=True)[:top_k]
        logger.info(f"Returning {len(retrieved_chunks)} refined chunks")
        return retrieved_chunks

# Example usage
if __name__ == "__main__":
    search_engine = SearchEngine()
    query = "What are the backup service terms in the cloud contract?"
    results = search_engine.retrieve(query, top_k=3)
    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"Content: {result['content']}")
        print(f"Metadata: {result['metadata']}")
        print(f"Vector Similarity: {result['vector_similarity']:.4f}")
        print(f"Metadata Score: {result['metadata_score']}")
        print(f"Combined Score: {result['combined_score']:.4f}\n")