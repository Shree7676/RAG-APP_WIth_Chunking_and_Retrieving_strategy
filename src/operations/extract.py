import logging
from pdf2image import convert_from_path
from PIL import Image
import os
from pathlib import Path
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
import extract_msg

# Set up logging
logger = logging.getLogger('markdown-extractor')

class MarkdownExtractor:
    """
        A class to extract Markdown content from various file types (PDF, DOCX, XLSX, MSG).
        Processing strategy:
            - PDFs: Converted to images, then to a new PDF, then to Markdown using Docling. 
               - pdf -> image -> pdf (improves text extraction, if the pdf contains mixture of text and image)
            - DOCX/XLSX: Converted directly to Markdown using Docling.
            - MSG: Converted to Markdown with metadata (subject, sender, etc.) preserved.
    """
    def __init__(self):
        logger.info('MarkdownExtractor initialized')
        self.output_images_dir = "output_images"
        self.output_pdf_dir = "converted_pdf"
        self.output_md_dir = "output_md"
        os.makedirs(self.output_images_dir, exist_ok=True)
        os.makedirs(self.output_pdf_dir, exist_ok=True)
        os.makedirs(self.output_md_dir, exist_ok=True)

    def pdf_to_images(self, pdf_path: str) -> list[str]:
        """Convert PDF pages to images and save them."""
        logger.info(f"Converting PDF to images: {pdf_path}")
        images = convert_from_path(pdf_path)
        image_paths = []
        
        for i, img in enumerate(images):
            img_path = os.path.join(self.output_images_dir, f"page_{i+1}.png")
            img.save(img_path, "PNG")
            image_paths.append(img_path)
            logger.debug(f"Saved image: {img_path}")

        logger.info(f"Converted {len(image_paths)} pages to images")
        return image_paths

    def images_to_pdf(self, image_paths: list[str], output_pdf: str) -> None:
        """Convert a list of image paths back to a PDF."""
        logger.info(f"Converting images to PDF: {output_pdf}")
        images = [Image.open(img).convert("RGB") for img in image_paths]
        
        images[0].save(output_pdf, save_all=True, append_images=images[1:])
        logger.info(f"New PDF created: {output_pdf}")

    def convert_to_markdown(self, input_path: str, output_md_path: str) -> None:
        """Convert a PDF, DOCX, or XLSX file to Markdown using Docling."""
        logger.info(f"Converting file to Markdown: {input_path}")
        
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        conv_result = doc_converter.convert(input_path)
        with open(output_md_path, "w", encoding="utf-8") as fp:
            fp.write(conv_result.document.export_to_markdown())
        logger.info(f"Markdown file created: {output_md_path}")

    def msg_to_markdown(self, msg_path: str, output_md_path: str) -> None:
        """Convert .msg email file to a .md (Markdown) file."""
        logger.info(f"Converting MSG to Markdown: {msg_path}")
        
        msg = extract_msg.Message(msg_path)
        msg_subject = msg.subject.replace(" ", "_").replace("/", "-")
        msg_body = msg.body
        msg_date = msg.date
        msg_sender = msg.sender
        msg_recipients = msg.to

        md_content = f"""# {msg_subject}

        **From:** {msg_sender}  
        **To:** {msg_recipients}  
        **Date:** {msg_date}  

        ---

        {msg_body}
        """

        with open(output_md_path, "w", encoding="utf-8") as md_file:
            md_file.write(md_content)
        logger.info(f"Markdown file created: {output_md_path}")

    def extract(self, file_path: str) -> None:
        """Process a file based on its type: PDF, DOCX, XLSX, or MSG."""
        logger.info(f"Starting extraction for: {file_path}")
        
        file_name = Path(file_path).stem
        file_ext = Path(file_path).suffix.lower()
        output_md = os.path.join(self.output_md_dir, f"{file_name}.md")

        if file_ext == ".pdf":
            # PDF: Convert to images, back to PDF, then to Markdown
            output_pdf = os.path.join(self.output_pdf_dir, f"{file_name}.pdf")
            image_paths = self.pdf_to_images(file_path)
            self.images_to_pdf(image_paths, output_pdf)
            self.convert_to_markdown(output_pdf, output_md)
        elif file_ext in [".docx", ".xlsx"]:
            # DOCX/XLSX: Convert directly to Markdown
            self.convert_to_markdown(file_path, output_md)
        elif file_ext == ".msg":
            # MSG: Use custom MSG-to-Markdown conversion
            self.msg_to_markdown(file_path, output_md)
        else:
            logger.warning(f"Unsupported file type: {file_ext} for {file_path}")
            return

        logger.info(f"Extraction complete for: {file_path}")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    extractor = MarkdownExtractor()
    
    # List of files from the documents folder
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

    # Skip README.md or any other non-processable files
    for file in files:
        if Path(file).suffix.lower() not in [".md"]:
            extractor.extract(file)