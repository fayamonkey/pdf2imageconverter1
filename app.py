import streamlit as st
import fitz  # PyMuPDF
import easyocr
import zipfile
from io import BytesIO
import tempfile
import os

# Initialize EasyOCR reader once
@st.cache_resource
def get_reader():
    return easyocr.Reader(['en'])

reader = get_reader()

def process_pdf(pdf_bytes):
    """Process PDF and return markdown content with OCR results"""
    doc = fitz.open(stream=pdf_bytes)
    markdown = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Extract text
        text = page.get_text()
        markdown.append(f"## Page {page_num+1}\n\n{text}")
        
        # Process images
        img_list = page.get_images(full=True)
        if img_list:
            markdown.append(f"### Images on Page {page_num+1}")
            
        for img_idx, img in enumerate(img_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                f.write(image_bytes)
                temp_path = f.name
            
            try:
                ocr_results = reader.readtext(temp_path, detail=0)
                ocr_text = " ".join(ocr_results)
                markdown.append(f"**Image {img_idx+1} OCR:**\n{ocr_text}\n")
            except Exception as e:
                markdown.append(f"⚠️ OCR Error for image {img_idx+1}: {str(e)}")
            finally:
                os.unlink(temp_path)
    
    doc.close()
    return "\n\n".join(markdown)

# Streamlit UI
st.title("📄 PDF to Markdown Converter with OCR")
st.write("Extract text and OCR images from PDF files to Markdown")

uploaded_files = st.file_uploader(
    "Upload PDF files", 
    type=["pdf"],
    accept_multiple_files=True
)

if st.button("✨ Process Files") and uploaded_files:
    zip_buffer = BytesIO()
    total_files = len(uploaded_files)
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, uploaded_file in enumerate(uploaded_files):
            with st.spinner(f"Processing {uploaded_file.name} ({i+1}/{total_files})..."):
                try:
                    md_content = process_pdf(uploaded_file.getvalue())
                    filename = f"{os.path.splitext(uploaded_file.name)[0]}.md"
                    zipf.writestr(filename, md_content.encode('utf-8'))
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    st.success("✅ Processing complete!")
    st.download_button(
        label="📥 Download Markdown Files",
        data=zip_buffer.getvalue(),
        file_name="processed_documents.zip",
        mime="application/zip"
    )
