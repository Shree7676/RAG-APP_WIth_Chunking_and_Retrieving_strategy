import logging
from src.operations.ask import LLMAsker
from src.operations.search import SearchEngine
from src.operations.embed import EmbedService
from src.operations.extract import MarkdownExtractor
import argparse
import os
from pathlib import Path
import gradio as gr


class App:
    """The main class of the application."""

    def __init__(self):
        """Initialize the App class."""
        pass

    def run(self):
        """Parse command-line arguments and execute the specified mode."""
        parser = argparse.ArgumentParser(description='Ask questions about the files of a case.')
        
        parser.add_argument(
            '--mode',
            choices=['index-files', 'ask-question', 'search', 'get-markdown', 'gradio'],  # Add 'gradio'
            default='ask-question',
            help='The mode of the application.'
        )
        
        parser.add_argument(
            'query',
            nargs='?',
            type=str,
            help='The question or query for ask-question or search modes.'
        )
        
        args = parser.parse_args()
        
        if args.mode == 'index-files':
            print("Indexing files...")
            self.index_files()
            print("Indexing complete.")
        elif args.mode == 'ask-question':
            if not args.query:
                parser.error('The query argument is required in "ask-question" mode.')
            print("Asking question...")
            self.ask_question(args.query)
        elif args.mode == 'search':
            if not args.query:
                parser.error('The query argument is required in "search" mode.')
            print("Searching...")
            self.search(args.query)
        elif args.mode == 'get-markdown':
            print("Converting files to markdown...")
            self.get_markdown()
            print("Conversion complete.")
        elif args.mode == 'gradio':
            print("Launching Gradio interface...")
            self.launch_gradio()

    def index_files(self):
        """Index markdown files from output_md directory into the vector database."""
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
        print(f"Processed {len(files)} markdown files.")

    def get_markdown(self):
        """Convert supported files from documents directory to markdown."""
        extractor = MarkdownExtractor()
        files = [
            "documents/0664411829.pdf",
            "documents/Company OKRs.xlsx",
            "documents/Scan EVB IT-Cloud Vertrag.pdf",
            "documents/Übermittlung Finanzamt.pdf",
            "documents/CLA_filled.docx",
            "documents/NDA_filled.docx",
            "documents/Scan 10.08.2023.pdf",
            "documents/Scan Stromtarif.pdf",
            "documents/WG Anfrage Veröffentlichung Gerichtsurteile.msg"
        ]
        for file in files:
            if Path(file).suffix.lower() not in [".md"]:
                extractor.extract(file)
        print(f"Converted {len(files)} files to markdown.")

    def search(self, query):
        """Search the indexed files for chunks relevant to the query."""
        search_engine = SearchEngine()
        results = search_engine.retrieve(query, top_k=3)
        for i, result in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"Content: {result['content']}")
            print(f"Metadata: {result['metadata']}")
            print(f"Vector Similarity: {result['vector_similarity']:.4f}")
            print(f"Metadata Score: {result['metadata_score']}")
            print(f"Combined Score: {result['combined_score']:.4f}\n")

    def ask_question(self, question):
        """Ask a question using the LLM with context from the vector database."""
        asker = LLMAsker()
        response,context = asker.ask(question, top_k=3)
        print(f"Answer: {response}")
        return response, context
      
    def launch_gradio(self):
        """Launch a simple Gradio interface for asking questions."""
        import gradio as gr
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Launching Gradio interface")

        # Define the function to handle the question and return both answer and context
        def gradio_ask(question):
            answer, context = self.ask_question(question)  # Unpacks the tuple returned by ask_question
            return answer, context

        iface = gr.Interface(
            fn=gradio_ask,  # Directly use the function, no lambda needed here
            inputs=gr.Textbox(
                label="Ask a question about the documents",
                placeholder="e.g., What are the backup service terms in the cloud contract?"
            ),
            outputs=[
                gr.Markdown(label="Answer"),  # Display answer in Markdown
                gr.Textbox(label="Context", lines=5)  # Display context in Textbox
            ],
            title="Document Q&A",
            description="Ask questions about indexed documents and get answers from an LLM.",
            allow_flagging="never"
        )
        
        iface.launch(share=True, server_name="0.0.0.0", server_port=7860)

    

if __name__ == "__main__":
    app = App()
    app.run()