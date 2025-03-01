import re
import os
import logging
from typing import List
import requests
from keybert import KeyBERT
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.api import execute_prompt
from src.api import embed_texts
from .chromadb_client import chroma_db
from langchain.prompts import PromptTemplate
from src.templates.embed_prompt import emb_prompt

logger = logging.getLogger('embed')


class EmbedService:
    """
        A class to process markdown documents, enrich them with metadata, and prepare chunks for vector storage.
        Split markdown text into chunks based on the following strategy:
            - Detects tables and processes each as a complete chunk.
            - If markdown contains '##' sections, splits based on these while respecting chunk_size and chunk_overlap.
            - If no headers are present, splits sequentially by size with overlap for continuity.
    """

    def __init__(self, markdown_path):
        """Initialize the DocumentProcessor with file path."""
        self.markdown_path = markdown_path
        self.collection = chroma_db.collection
        self.filename = os.path.basename(markdown_path)
        self.kw_model = KeyBERT()
        self.keyphrase_ngram_range = (2, 3)
        self.top_n = 5
        self.headers_to_split_on = [("##", "Section")]
        self.chunk_size = 750
        self.chunk_overlap = 150
        self.min_content_size = 75
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        logger.info(f"Initialized DocumentProcessor for file: {self.markdown_path}")

    def read_markdown_file(self):
        """Read the markdown file and return its content."""
        logger.info(f"Reading file {self.markdown_path}")
        try:
            with open(self.markdown_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Failed to read file {self.markdown_path}: {str(e)}")
            raise

    def detect_tables(self, markdown_text: str) -> tuple[List[str], str]:
        """Detect and extract tables from markdown text, including header rows, and return tables and cleaned markdown."""
        logger.info("Detecting tables in markdown text")
        # Match full table including header, separator, and content
        table_pattern = r'(\|(?:[^|\n]*\|)+\n\|[-:\s|]*\|\n(?:.*?))(?=\n\n|\Z)'
        matches = re.finditer(table_pattern, markdown_text, re.DOTALL)
        
        # Extract full table text as-is
        tables = [match.group(0) for match in matches]
        new_md = markdown_text
        for table in tables:
            new_md = new_md.replace(table, "")
        
        # Clean up extra newlines and whitespace
        new_md = re.sub(r'\n\s*\n+', '\n\n', new_md.strip())
        logger.debug(f"Text without tables: '{new_md[:100]}...'")  # Debug to inspect leftovers
        logger.info(f"Found {len(tables)} tables")
        return tables, new_md
    
    
    def split_by_headers_and_tables(self, markdown_text: str) -> List[Document]:
        """
        Split markdown text into chunks based on the following strategy:
            - Detects tables and processes each as a complete chunk.
            - If markdown contains '##' sections, splits based on these while respecting chunk_size and chunk_overlap.
            - If no headers are present, splits sequentially by size with overlap for continuity.
        """

        logger.info("Starting split by headers and tables")
        all_splits = []

        tables, text_without_tables = self.detect_tables(markdown_text)
        logger.info(f"Detected {len(tables)} tables in the markdown")
        if tables:
            for table in tables:
                all_splits.append(self._create_document(table))

        text_without_tables = text_without_tables.strip()
        if not text_without_tables:
            logger.info("No additional text after tables, returning table chunks only")
            logger.info(f"Total splits: {len(all_splits)}")
            return all_splits

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on, strip_headers=False
        )
        header_splits = markdown_splitter.split_text(text_without_tables)
        logger.info(f"Split remaining text into {len(header_splits)} sections using headers")

        if header_splits:
            logger.info("Headers found, processing with size enforcement and merging")
            current_chunk = ""
            for split in header_splits:
                content_length = len(split.page_content)
                if content_length < self.min_content_size and current_chunk:
                    current_chunk += "\n\n" + split.page_content
                else:
                    if current_chunk:
                        if len(current_chunk) > self.chunk_size:
                            sub_chunks = self.text_splitter.split_text(current_chunk)
                            all_splits.extend([self._create_document(sub_chunk) for sub_chunk in sub_chunks])
                        else:
                            all_splits.append(self._create_document(current_chunk))
                    current_chunk = split.page_content
            if current_chunk:
                if len(current_chunk) > self.chunk_size:
                    sub_chunks = self.text_splitter.split_text(current_chunk)
                    all_splits.extend([self._create_document(sub_chunk) for sub_chunk in sub_chunks])
                else:
                    all_splits.append(self._create_document(current_chunk))
        else:
            logger.info("No headers found, splitting text sequentially")
            if text_without_tables.strip():
                text_splits = self.text_splitter.split_text(text_without_tables)
                all_splits.extend([self._create_document(text_split) for text_split in text_splits])

        logger.info(f"Total splits: {len(all_splits)}")
        return all_splits
    
    
    def _create_document(self, content: str) -> Document:
        """Helper to create a Document object from content with filename in metadata."""
        logger.debug(f"Creating document for chunk of size {len(content)}")
        return Document(page_content=content, metadata={"filename": self.filename})


    def enrich_chunk_metadata(self, chunk: Document) -> None:
        """Enrich a single chunk with keywords, summary, and LLM description using API."""
        logger.info(f"Enriching chunk of size {len(chunk.page_content)}")
        
        # Keywords
        keywords = self.kw_model.extract_keywords(
            chunk.page_content,
            keyphrase_ngram_range=self.keyphrase_ngram_range,
            top_n=self.top_n
        )
        sec_keywords = [kw[0] for kw in keywords]
        chunk.metadata["section_keywords"] = ', '.join(sec_keywords)

        # Summary
        summary = self.kw_model.extract_keywords(
            chunk.page_content,
            keyphrase_ngram_range=(3, 5),
            top_n=1
        )
        chunk.metadata["summary"] = summary[0][0] if summary else ""

        prompt = PromptTemplate.from_template(template=emb_prompt)
        formatted_prompt = prompt.format(
            page_content = chunk.page_content
        )

        llm_response = execute_prompt(formatted_prompt)
        llm_description = llm_response.get('response', 'Error: No response from API')
        chunk.metadata["description"] = llm_description

    def enrich_chunks(self, chunks: List[Document]) -> List[Document]:
        """Enrich all chunks with metadata."""
        logger.info(f"Enriching {len(chunks)} chunks")
        for chunk in chunks:
            self.enrich_chunk_metadata(chunk)
        return chunks
    
    def embed(self, chunks: List[Document]) -> None:
        """Embed chunks and store them in the vector database."""
        logger.info(f"Embedding and storing {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            try:
                embedding = embed_texts([chunk.page_content], 'document')
                if embedding:
                    logger.info(f"Storing {self.filename}_chunk_{i} documents in VectorDB")
                    self.collection.add(
                        documents=chunk.page_content,
                        metadatas=chunk.metadata,
                        ids=f"{self.filename}_chunk_{i}",
                        embeddings=embedding
                    )
                    logger.info("Data successfully stored in VectorDB!")
                else:
                    logger.warning("No embeddings returned")
            except Exception as e:
                logger.error(f"Failed to embed or store chunks: {str(e)}")
                raise
        logger.info(f"Successfully processed embeddings")
        return 

    def process(self) -> tuple:
        """Execute the full document processing pipeline and return enriched chunks with embeddings."""
        logger.info("Starting document processing pipeline")
        markdown_text = self.read_markdown_file()
        initial_splits = self.split_by_headers_and_tables(markdown_text)
        enriched_splits = self.enrich_chunks(initial_splits)
        embeddings = self.embed(enriched_splits)
        logger.info("Processing complete")
        return enriched_splits, embeddings


# Example usage
if __name__ == "__main__":
    files = [
        "output_md/0664411829.md",
        "output_md/Company OKRs.md",
        "output_md/Scan EVB IT-Cloud Vertrag.md",
        "output_md/Übermittlung Finanzamt.md",
        "output_md/CLA_filled.md",
        "output_md/NDA_filled.md",
        "output_md/Scan 10.08.2023.md",
        "output_md/Scan Stromtarif.md",
        "output_md/WG Anfrage Veröffentlichung Gerichtsurteile.md"
    ]
    for filepath in files:
        processor = EmbedService(markdown_path=filepath)
        enriched_chunks = processor.process()