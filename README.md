
## Info

| Name                     | xxxxx        |
|--------------------------|--------------|
| E-Mail:                  | shreekantnandiyawar@gmail.com |
| Approx. Time To Complete | 10+ hours     |
| My github:               | [shree7676](https://github.com/shree7676)      |

## The task

The task is to build a very simple [RAG](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) that is able to answer questions on the provided demo documents. The documents represent what a lawyer will be working with on a day-to-day basis - although some will be harder to parse than others.

> The final application should provide an interface to talk to the assistant about the documents, ask questions, and retreive facts. For a lawyer's  job it's important that every piece of information they work with should be backed by sources, so every answer should be as specific as possible, pointing not only to the source document, but ideally to the sentence or paragraph where the information is located.

This repository already has a basic structure to help you get started and point you in the right direction. Your tasks are to:

- [✅] Familiarize yourself with the codebase and the parts that need changes 
- [✅] Complete the **extraction script** to embed the information from the documents in markdown format
- [✅] Complete the **embedding script** to embed the documents' information for later retreival
- [✅] Complete the **search script** to retreive the embedded documents that most closely resemble the search query
- [✅] Complete the **ask script** to ask questions about the documents
- [✅] Complete the **tests** and make sure they run

## Solution 

### Text Extraction Strategy:
- PDFs: Converted to images, then to a new PDF, then to Markdown using Docling. 
    - pdf -> image -> pdf (improves text extraction, if the pdf contains mixture of text and image which has text in it)
- DOCX/XLSX: Converted directly to Markdown using Docling.
- MSG: Converted to Markdown with metadata (subject, sender, etc.) preserved.

### Embeding Strategy :
- Detects tables and processes each as a complete chunk.
- If markdown contains '##' sections, splits based on these while respecting chunk_size and chunk_overlap.
- If no headers are present, splits sequentially by size with overlap for continuity.

### Retrieval strategy:
- Embeds the query and retrieves initial matches via vector similarity.
- Refines results using metadata (keywords, summary, description, filename).
- Combines vector similarity and metadata scores to rank and return top-k chunks.

### Query :
- Retrieves top_k chunks from the vector database, optionally filtered by filename.
- Builds context from chunk content, metadata, and similarity scores.
- Queries the LLM with the formatted context and question.
- Falls back to a no-context query if retrieval fails.
        
## Setup

```bash
pip install -r requirements.txt
```

## API

We've provided an API access for you that allows you to embed text and prompt an LLM. The API is running at [https://assessment.silvrnova.ai](https://assessment.silvrnova.ai). 

You can find the OpenAPI specification here: [OpenAPI Specification](https://assessment.silvernova.ai/swagger).

You have to authenticate at the API. Use your assigned **API Key** for that purpose. Put it into a `.env` file located in the root of the project.

## 

## Run the below commands in order as the vectordb is not updated by default
```bash
# Get the file's content as markdown
./associate --mode=get-markdown

# Index the documents
./associate --mode=index-files

# Search for documents based on similarity
./associate --mode=search "[question]"

# Ask a question about the documents
./associate "[question]"

# UI Interface to chat
./associate --mode=gradio
```
