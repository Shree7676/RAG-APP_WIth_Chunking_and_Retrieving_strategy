import logging
from typing import Optional
from src.api import execute_prompt
from .search import SearchEngine
import re
from langchain.prompts import PromptTemplate
from src.templates.ask_prompt import query_prompt, no_context

# from .lang_detect import check_and_translate_language

logger = logging.getLogger('llm_asker')


class LLMAsker:
    """
        A class to ask an LLM a question using retrieved context from a vector database.
        Querying strategy:
            - Retrieves relevant chunks using a SearchEngine.
            - Constructs context from chunk content, metadata, and similarity scores.
            - Queries the LLM with context, falling back to a no-context prompt if retrieval fails.
    """

    def __init__(self):
        """Initialize LLMAsker with a SearchEngine instance."""
        self.search_engine = SearchEngine()
        logger.info("Initialized LLMAsker with SearchEngine")

    def clean_llm_response(self, response: str) -> str:
        """Convert LLM response from HTML/Markdown to clean plain text."""
        response = re.sub(r'<br\s*/?>', '\n', response, flags=re.IGNORECASE)
        def uppercase_bold(match):
            return match.group(1).upper()
        response = re.sub(r'\*\*(.*?)\*\*', uppercase_bold, response)
        response = re.sub(r'<[^>]+>', '', response)
        response = re.sub(r'\n\s*\n+', '\n\n', response).strip()
        response = re.sub(r'\s+', ' ', response)
        return response

    def ask(self, question: str, top_k: int = 3, filename_filter: Optional[str] = None) -> tuple[str, str]:
        """
            Ask the LLM a question with context from retrieved chunks.
            Steps:
                - Retrieves top_k chunks from the vector database, optionally filtered by filename.
                - Builds context from chunk content, metadata, and similarity scores.
                - Queries the LLM with the formatted context and question.
                - Falls back to a no-context query if retrieval fails.
        """
        print('Thinking...')
        logger.info(f"Processing question: '{question}'")

        # Step 1: Retrieve relevant chunks
        try:
            retrieved_chunks = self.search_engine.retrieve(
                query=question,
                top_k=top_k,
                filename_filter=filename_filter
            )
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks for context")
        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {str(e)}")
            return self._ask_without_context(question)

        # Step 2: Construct context from retrieved chunks
        context = ""
        for i, chunk in enumerate(retrieved_chunks, 1):
            context += (
                f"Chunk {i}:\n"
                f"Content: {chunk['content']}\n"
                f"Metadata: {chunk['metadata']}\n"
                f"Similarity Score: {chunk['combined_score']:.4f}\n\n"
            )

        # Step 3: Format the prompt with context and question
        prompt = PromptTemplate.from_template(template=query_prompt)
        formatted_prompt = prompt.format(
            context=context if context else "No relevant context available.",
            question=question
        )
        logger.debug(f"Formatted prompt: {formatted_prompt[:200]}...")  

        # Step 4: Query the LLM
        try:
            response = execute_prompt(formatted_prompt)
            if 'response' not in response:
                logger.error("LLM API returned no valid response")
                raise ValueError("No valid response from LLM API")
            answer = response['response']
            cleaned_answer = self.clean_llm_response(answer)
            # cleaned_answer = check_and_translate_language(question, cleaned_answer)
            logger.info("Received and cleaned response from LLM")
            return cleaned_answer , context
        except Exception as e:
            logger.error(f"Failed to query LLM: {str(e)}")
            return "Error: Could not get a response from the LLM.", "Error retrieving context"

    def _ask_without_context(self, question: str) -> tuple[str, str]:
        """Fallback method to ask the LLM without context."""
        logger.warning("No chunks retrieved, falling back to query without context")
        prompt = PromptTemplate.from_template(template=no_context)
        formatted_prompt = prompt.format(
            question=question
        )
        try:
            response = execute_prompt(formatted_prompt)
            if 'response' not in response:
                logger.error("LLM API returned no valid response")
                raise ValueError("No valid response from LLM API")
            answer = response['response']
            cleaned_answer = self.clean_llm_response(answer)
            # cleaned_answer = check_and_translate_language(question, cleaned_answer) 
            return cleaned_answer , "Error retrieving context"
        except Exception as e:
            logger.error(f"Failed to query LLM without context: {str(e)}")
            return "Error: Could not get a response from the LLM." , "Error retrieving context"
        
    

# Example usage
if __name__ == "__main__":
    asker = LLMAsker()
    question = "What are the backup service terms in the cloud contract?"
    response,context = asker.ask(question, top_k=3)
    print(f"Answer: {response}")