import io
import fitz  # PyMuPDF
import streamlit as st
from PIL import Image


def compress_pdf_deep(input_bytes: bytes, image_quality: int = 40) -> bytes:
    """
    Decompresses the PDF, downscales/re-compresses images inside it,
    and optimizes the layout to dramatically reduce file size.
    """
    doc = fitz.open(stream=input_bytes, filetype="pdf")

    # Loop through every page to find and compress images
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        for img in image_list:
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            # Load image into PIL to compress it
            try:
                pil_img = Image.open(io.BytesIO(image_bytes))

                # Convert RGBA to RGB if necessary (JPEG doesn't support alpha channels)
                if pil_img.mode in ("RGBA", "P"):
                    pil_img = pil_img.convert("RGB")

                # Re-compress image to JPEG with lower quality
                compressed_img_io = io.BytesIO()
                pil_img.save(compressed_img_io, format="JPEG", quality=image_quality, optimize=True)

                # Replace the massive image with the compressed one
                page.replace_image(xref, stream=compressed_img_io.getvalue())
            except Exception:
                # If an image format fails to convert, skip it safely
                continue

    output_buffer = io.BytesIO()
    # Deep garbage collection and stream compression
    doc.save(
        output_buffer,
        garbage=4,
        deflate=True,
        clean=True
    )
    doc.close()
    return output_buffer.getvalue()


# --- Streamlit Frontend ---
st.set_page_config(page_title="Deep PDF Compressor", page_icon="📄")
st.title("⚡ Deep PDF Compressor")
st.write("Drastically shrink PDF sizes by optimizing internal images.")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    initial_size = len(file_bytes) / 1024  # KB
    st.info(f"Original Size: **{initial_size:.2f} KB**")

    # Let user control the aggressive compression slider if needed
    quality = st.slider("Image Quality (Lower = Smaller File Size)", min_value=10, max_value=90, value=40)

    if st.button("🚀 Compress PDF Now"):
        with st.spinner("Deep compressing images..."):
            compressed_bytes = compress_pdf_deep(file_bytes, image_quality=quality)
            final_size = len(compressed_bytes) / 1024  # KB

        savings = initial_size - final_size
        percent_saved = (savings / initial_size) * 100 if initial_size > 0 else 0

        if final_size > initial_size:
            st.warning("This PDF is already highly optimized!")
        else:
            st.success(f"Compressed Size: **{final_size:.2f} KB** (Saved **{percent_saved:.1f}%**)")

            st.download_button(
                label="📥 Download Compressed PDF",
                data=compressed_bytes,
                file_name=f"compressed_{uploaded_file.name}",
                mime="application/pdf"
            )