import streamlit as st
import heapq
from collections import Counter
from PIL import Image
import io
import fitz
from streamlit_option_menu import option_menu

# Custom CSS for styling
custom_css = """
    <style>
    /* Mengubah background sidebar */
    [data-testid="stSidebar"] {
        background-color: #999DA0;
    }
    /* Sidebar styling */
    [data-testid="stSidebar"] {
    transition: transform 0.3s ease-in-out;
    }

    /* Sidebar styling for mobile */
    @media (max-width: 768px) {
    [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(-100%);
    }
    }
    @media only screen and (max-width: 768px) {
    [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(0px);
    }
    /* Mengubah background halaman utama */
    .css-1d391kg {
        background-color: #006666;
        color: #FFFFFF;  /* Mengubah warna teks menjadi putih */
    }
    /* Mengubah warna tombol */
    if st.button("Klik di sini untuk Mengunduh Dokumen yang Didekompresi"):
    st.download_button(label="Download Dokumen yang Didekompresi", data=decompressed_pdf, file_name="decompressed_document.pdf", mime="application/pdf")
    }
    </style>
    """

# Menggunakan custom CSS di dalam Streamlit
st.markdown(custom_css, unsafe_allow_html=True)

# Define Node class for Huffman coding
class Node:
    def __init__(self, freq, char=None, left=None, right=None):
        self.freq = freq
        self.char = char
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq

# Build Huffman Tree
def build_huffman_tree(data):
    if not data:
        return None

    frequency = Counter(data)
    priority_queue = [Node(freq, char) for char, freq in frequency.items()]
    heapq.heapify(priority_queue)

    while len(priority_queue) > 1:
        left = heapq.heappop(priority_queue)
        right = heapq.heappop(priority_queue)
        merged = Node(left.freq + right.freq, left=left, right=right)
        heapq.heappush(priority_queue, merged)

    return priority_queue[0]

# Build Huffman Codes
def build_codes(node, prefix='', codebook=None):
    if codebook is None:
        codebook = {}

    if node:
        if node.char is not None:
            codebook[node.char] = prefix
        else:
            build_codes(node.left, prefix + '0', codebook)
            build_codes(node.right, prefix + '1', codebook)

    return codebook

# Huffman Compression
def huffman_compress(data):
    tree = build_huffman_tree(data)
    codebook = build_codes(tree)
    compressed_data = ''.join(codebook[char] for char in data)
    return compressed_data, tree, codebook

# Huffman Decompression
def huffman_decompress(compressed_data, tree):
    result = []
    node = tree
    for bit in compressed_data:
        node = node.left if bit == '0' else node.right
        if node.char is not None:
            result.append(node.char)
            node = tree
    return bytes(result)

# Image Compression
def compress_image(uploaded_file):
    try:
        if uploaded_file.type != "image/jpeg":
            st.error("Hanya gambar dengan format JPEG dan JPG yang dapat diproses.")
            return

        image = Image.open(uploaded_file)
        quality = st.slider("Pilih kualitas kompresi gambar (semakin rendah semakin terkompresi)", 1, 100, 18)
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        compressed_image_data = buf.getvalue()
        original_size = uploaded_file.size
        compressed_size = len(compressed_image_data)
        ratio = compressed_size / original_size

        st.success(f"Gambar berhasil dikompresi! Rasio kompresi: {ratio:.2%}")

        # Download button
        st.download_button(label="Download Gambar yang Dikompresi", data=compressed_image_data, file_name="compressed_image.jpeg")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengompresi gambar: {e}")

# Image Decompression
def decompress_image(uploaded_file):
    try:
        # Membaca data gambar yang diunggah
        compressed_image_data = uploaded_file.read()
        buf = io.BytesIO(compressed_image_data)
        decompressed_image = Image.open(buf)

        # Menampilkan gambar yang didekompresi
        st.image(decompressed_image, caption="Gambar Didekompresi", width=300) 

        # Simpan gambar yang didekompresi ke dalam bytes
        buf = io.BytesIO()
        decompressed_image.save(buf, format="JPEG")
        byte_im = buf.getvalue()

        # Tombol untuk mengunduh gambar yang didekompresi
        st.download_button(label="Download Gambar yang Didekompresi", data=byte_im, file_name="decompressed_image.jpeg")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat mendekompresi gambar: {e}")


# Function to compress PDF document
def compress_document(uploaded_file):
    try:
        pdf_document = uploaded_file.read()
        original_size = len(pdf_document)

        # Quality selection for image compression
        quality = st.slider("Pilih Kualitas Kompresi Gambar Dalam Dokumen (semakin rendah semakin terkompresi)", 1, 100, 50)

        # Initialize PDF reader
        pdf_reader = fitz.open(stream=pdf_document, filetype="pdf")

        # Initialize PDF writer for compressed output
        pdf_writer = fitz.open()

        for page_number in range(pdf_reader.page_count):
            page = pdf_reader.load_page(page_number)

            # Get images in the page
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = pdf_reader.extract_image(xref)
                image_bytes = base_image["image"]

                # Compress the image
                img_buf = io.BytesIO(image_bytes)
                image = Image.open(img_buf)
                
                # Convert image to JPEG with specified quality
                img_buf = io.BytesIO()
                image.save(img_buf, format="JPEG", quality=quality)
                compressed_image_bytes = img_buf.getvalue()

                # Replace the image in the page
                rect = page.get_image_rects(xref)[0]
                page.insert_image(rect, stream=compressed_image_bytes)

            # Insert the processed page into the writer
            pdf_writer.insert_pdf(pdf_reader, from_page=page_number, to_page=page_number)

        # Optimize the PDF by compressing images and fonts
        pdf_writer.save("compressed.pdf", garbage=4, deflate=True, clean=True, linear=True)

        # Read the compressed PDF back
        with open("compressed.pdf", "rb") as f:
            compressed_pdf = f.read()

        compressed_size = len(compressed_pdf)
        ratio = compressed_size / original_size if original_size > 0 else 0

        st.success(f"Dokumen berhasil dikompresi! Ukuran asli: {original_size} bytes, Ukuran setelah kompresi: {compressed_size} bytes, Rasio kompresi: {ratio:.2%}")

        st.download_button(label="Download Dokumen yang Dikompresi", data=compressed_pdf, file_name="compressed_document.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengompresi dokumen: {e}")

# Streamlit interface
def main():
    st.title("PDF Document Compression")

    uploaded_file = st.file_uploader("Upload a PDF document to compress", type=["pdf"])

    if uploaded_file is not None:
        compress_document(uploaded_file)
# Document Decompression
def decompress_document(uploaded_file):
    try:
        compressed_pdf = uploaded_file.read()

        pdf_reader = fitz.open(stream=compressed_pdf)

        # Create a new PDF to store the decompressed content
        pdf_writer = fitz.open()

        for page_number in range(pdf_reader.page_count):
            page = pdf_reader.load_page(page_number)
            pdf_writer.insert_pdf(pdf_reader, from_page=page_number, to_page=page_number)

        # Save the decompressed PDF
        decompressed_pdf_path = "decompressed.pdf"
        pdf_writer.save(decompressed_pdf_path, garbage=4, deflate=True, clean=True, linear=True)

        # Read the decompressed PDF
        with open(decompressed_pdf_path, "rb") as f:
            decompressed_pdf = f.read()

        st.success("Dokumen berhasil didekompresi!")
        st.download_button(label="Download Dokumen yang Didekompresi", data=decompressed_pdf, file_name="decompressed_document.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat mendekompresi dokumen: {e}")

def main():
    with st.sidebar:
        selected = option_menu(
            menu_title="Selamat Datang Di Website Kompresi Data",
            options=["Dashboard", "Kompresi Gambar", "Dekompresi Gambar", "Kompresi Dokumen", "Dekompresi Dokumen", "Bantuan"],
            icons=["house", "image", "image", "file-text", "file-text", "info-circle"],
            menu_icon="cast",
            default_index=0,
        )

    # Menambahkan CSS kustom untuk tampilan aplikasi
    st.markdown(
        """
        <style>
            .main {
                background-color: #B9BBB6;
                padding: 20px;
                border-radius: 15px;
            }
            .stButton>button {
                background-color: #B3DED1;
                color: Blue;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    if selected == "Dashboard":
        st.header("Selamat Datang di Website Kompresi Dokumen Dan Gambar")
        st.write("Silahkan Pilih Menu Yang Tersedia Pada Sidebar.")
        st.write("Berikut adalah fitur yang tersedia:")
        st.write("- Kompresi Gambar🖼️")
        st.write("- Dekompresi Gambar🖼️")
        st.write("- Kompresi Dokumen📄")
        st.write("- Dekompresi Dokumen📄")
        st.write("- Bantuan❓")
        
    
    elif selected == "Kompresi Gambar":
        st.title("Kompresi Gambar JPEG dan JPG")
        uploaded_file = st.file_uploader("Pilih file gambar JPEG untuk dikompresi", type=["jpeg", "jpg"])
        if uploaded_file is not None:
            compress_image(uploaded_file)

    elif selected == "Dekompresi Gambar":
        st.title("Dekompresi Gambar JPEG dan JPG")
        uploaded_file = st.file_uploader("Pilih file gambar JPEG untuk didekompresi", type=["jpeg", "jpg"])
        if uploaded_file is not None:
            decompress_image(uploaded_file)

    elif selected == "Kompresi Dokumen":
        st.title("Kompresi Dokumen PDF")
        uploaded_file = st.file_uploader("Pilih file dokumen PDF untuk dikompresi", type=["pdf"])
        if uploaded_file is not None:
            compress_document(uploaded_file)

    elif selected == "Dekompresi Dokumen":
        st.title("Dekompresi Dokumen PDF")
        uploaded_file = st.file_uploader("Pilih file dokumen PDF untuk didekompresi", type=["pdf"])
        if uploaded_file is not None:
            decompress_document(uploaded_file)

    elif selected == "Bantuan":
     st.header("Bantuan❓")
     st.subheader("Bantuan Aplikasi Kompresi Data Dokumen Dan Foto.")

     st.markdown(
        """
        <div style="text-align: justify;">
            Aplikasi ini memungkinkan Anda untuk melakukan kompresi dan dekompresi data teks<br/>(dokumen) serta data foto (gambar) secara mudah.
            <br/>
            <strong>Berikut adalah cara menggunakan setiap fitur:</strong>
            <br/><br/>
            <strong>1. Kompresi dan Dekompresi Foto (Gambar)</strong><br/>
            - Untuk melakukan kompresi gambar, unggah file gambar JPEG yang ingin Anda kompresi.<br/>
            - Pilih kualitas kompresi yang diinginkan menggunakan slider.<br/>
            - Klik tombol 'Kompres Foto' untuk memulai proses kompresi.<br/>  
            Gambar yang telah dikompresi akan ditampilkan dan dapat diunduh.<br/>
            - Untuk melakukan dekompresi gambar, unggah file gambar JPEG yang telah dikompresi.<br/>
            - Klik tombol 'Dekompresi Foto' untuk mendapatkan gambar asli kembali.<br/>
            <strong>2. Kompresi dan Dekompresi Dokumen (PDF)</strong><br/>
            - Untuk melakukan kompresi dokumen PDF, unggah file dokumen PDF yang ingin Anda kompresi.<br/>
            - Pilih kualitas kompresi gambar dalam dokumen menggunakan slider.<br/>
            - Klik tombol 'Kompres Dokumen' untuk memulai proses kompresi. Dokumen yang telah dikompresi<br/> akan ditampilkan dan dapat diunduh.<br/>
            - Untuk melakukan dekompresi dokumen PDF, unggah file dokumen PDF yang telah dikompresi.<br/>
            - Klik tombol 'Dekompresi Dokumen' untuk mendapatkan dokumen asli kembali.<br/>
        </div>
        """,
        unsafe_allow_html=True
     )

if __name__ == "__main__":
    main()
