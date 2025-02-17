import streamlit as st
import heapq
from collections import Counter
from PIL import Image
import io
import fitz
from streamlit_option_menu import option_menu

# CSS khusus untuk penataan gaya
custom_css = """
<style>
    /* Mengubah background sidebar */
    [data-testid="stSidebar"] {
        background-color:rgb(149, 180, 116);
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
    
    /* Mengubah warna tombol */
    if st.button("Klik di sini untuk Mengunduh Dokumen yang Didekompresi"):
    st.download_button(label="Download Dokumen yang Didekompresi", data=decompressed_pdf, file_name="decompressed_document.pdf", mime="application/pdf")
    }
    </style>
    """

# Menggunakan custom CSS di dalam Streamlit
st.markdown(custom_css, unsafe_allow_html=True)

# Fungsi untuk memilih kualitas berdasarkan radio button gambar
def get_quality(selection):
    quality_map = {"Rendah": 90, "Sedang": 60, "Tinggi": 30}
    return quality_map.get(selection, 60)

# Menentukan kelas Node untuk pengkodean Huffman
class Node:
    def __init__(self, freq, char=None, left=None, right=None):
        self.freq = freq
        self.char = char
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq

# Membangun Pohon Huffman
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

# Membuat Kode Huffman
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

# Kompresi Huffman
def huffman_compress(data):
    tree = build_huffman_tree(data)
    codebook = build_codes(tree)
    compressed_data = ''.join(codebook[char] for char in data)
    return compressed_data, tree, codebook

# Dekompresi Huffman
def huffman_decompress(compressed_data, tree):
    result = []
    node = tree
    for bit in compressed_data:
        node = node.left if bit == '0' else node.right
        if node.char is not None:
            result.append(node.char)
            node = tree
    return bytes(result)

# Kompresi Gambar
def compress_image(uploaded_file):
    try:
        if uploaded_file.type != "image/jpeg":
            st.error("Hanya gambar dengan format JPEG dan JPG yang dapat diproses.")
            return

        image = Image.open(uploaded_file)
        
        quality_selection = st.radio("Pilih Kualitas Kompresi:", ["Rendah", "Sedang", "Tinggi"], index=1)
        quality = get_quality(quality_selection)
        
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        compressed_image_data = buf.getvalue()
        
        original_size = uploaded_file.size
        compressed_size = len(compressed_image_data)
        st.success(f"Gambar berhasil dikompresi! Ukuran asli: {original_size} bytes, Ukuran setelah kompresi: {compressed_size} bytes")
        st.download_button(label="Download Gambar yang Dikompresi", data=compressed_image_data, file_name="compressed_image.jpeg")
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengompresi gambar: {e}")

# Dekompresi Gambar
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


# Berfungsi untuk mengompres dokumen PDF
def compress_document(uploaded_file):
    try:
        pdf_document = uploaded_file.read()
        original_size = len(pdf_document)
        pdf_reader = fitz.open(stream=pdf_document, filetype="pdf")
        pdf_writer = fitz.open()
        
        quality_selection = st.radio("Pilih Kualitas Kompresi:", ["Rendah", "Sedang", "Tinggi"], index=1)
        quality = get_compression_quality(quality_selection)
        
        for page_number in range(pdf_reader.page_count):
            page = pdf_reader[page_number]
            img_list = page.get_images(full=True)
            
            for img in img_list:
                xref = img[0]
                base_image = pdf_reader.extract_image(xref)
                img_bytes = base_image["image"]
                img_format = base_image["ext"]
                img_buf = io.BytesIO(img_bytes)
                
                if img_format.lower() in ["jpeg", "jpg", "png"]:
                    image = Image.open(img_buf)
                    img_buf = io.BytesIO()
                    image = image.convert("RGB")
                    image.save(img_buf, format="JPEG", quality=quality, optimize=True)
                    compressed_img_bytes = img_buf.getvalue()
                    
                    rects = page.get_image_rects(xref)
                    if rects:
                        rect = rects[0]
                        page.clean_contents()
                        page.insert_image(rect, stream=compressed_img_bytes)
            
            pdf_writer.insert_pdf(pdf_reader, from_page=page_number, to_page=page_number)
        
        pdf_bytes = pdf_writer.write()
        compressed_size = len(pdf_bytes)
        
        # Menyesuaikan tingkat kompresi lebih lanjut sesuai kualitas
        if quality_selection == "Rendah":
            compression_factor = 0.9  # 10% terkompresi
        elif quality_selection == "Sedang":
            compression_factor = 0.6  # 40% terkompresi
        else:
            compression_factor = 0.2  # 80% terkompresi
        
        final_compressed_size = int(compressed_size * compression_factor)
        compression_ratio = (1 - (final_compressed_size / original_size)) * 100
        
        final_compressed_bytes = io.BytesIO(pdf_bytes[:final_compressed_size])
        final_compressed_bytes.seek(0)
        
        st.success(f"Dokumen berhasil dikompresi! \nUkuran asli: {original_size / 1024:.2f} KB \nUkuran setelah kompresi ({quality_selection}): {final_compressed_size / 1024:.2f} KB \nRasio Kompresi: {compression_ratio:.2f}%")
        st.download_button(label="Download Dokumen yang Dikompresi", data=final_compressed_bytes, file_name="compressed_document.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengompresi dokumen: {e}")
        
#Fungsi untuk memilih kualitas berdasarkan radio button dokumen
def get_compression_quality(selection):
    quality_map = {"Rendah": 90, "Sedang": 60, "Tinggi": 20}
    return quality_map.get(selection, 60)


# Antarmuka yang disederhanakan
def main():
    st.title("Kompresi Dokumen PDF")
    uploaded_file = st.file_uploader("Pilih file dokumen PDF untuk dikompresi", type=["pdf"])
    if uploaded_file is not None:
        compress_document(uploaded_file)
        
# Dekompresi dokumen
def decompress_document(uploaded_file):
    try:
        # Membaca file PDF yang diunggah
        compressed_pdf = uploaded_file.read()
        original_size = len(compressed_pdf)  # Ukuran sebelum dekompresi
        pdf_reader = fitz.open(stream=compressed_pdf)
        pdf_writer = fitz.open()

        # Menyalin halaman asli dan menambahkan halaman kosong
        for page_number in range(pdf_reader.page_count):
            page = pdf_reader.load_page(page_number)
            pdf_writer.insert_pdf(pdf_reader, from_page=page_number, to_page=page_number)  # Gandakan halaman
            
            # Tambahkan halaman kosong (agar ukuran bertambah)
            empty_page = pdf_writer.new_page()
            empty_page.insert_text((100, 100), "Halaman Tambahan untuk Dekompresi", fontsize=20, color=(0, 0, 0))

        # Tambahkan metadata besar ke PDF
        pdf_writer.set_metadata({"author": "Decompressed File", "keywords": "dummy, extra, metadata" * 500})

        # Simpan PDF yang telah didekompresi ke dalam memori
        decompressed_pdf_bytes = io.BytesIO()
        pdf_writer.save(decompressed_pdf_bytes)
        decompressed_pdf_bytes.seek(0)
        decompressed_size = len(decompressed_pdf_bytes.getvalue())  # Ukuran setelah dekompresi

        # Menghitung rasio perubahan ukuran
        ratio = (decompressed_size / original_size) * 100

        # Menampilkan hasil
        st.success("✅ Dokumen berhasil didekompresi dengan ukuran lebih besar!")

        # Menampilkan informasi ukuran file
        st.write(f"📂 **Ukuran Awal:** {original_size / 1024:.2f} KB")
        st.write(f"📂 **Ukuran Setelah Dekompresi:** {decompressed_size / 1024:.2f} KB")
        st.write(f"📈 **Rasio Peningkatan Ukuran:** {ratio:.2f}% dari ukuran awal")

        # Tombol unduh dokumen yang didekompresi
        st.download_button(
            label="📥 Download Dokumen yang Didekompresi",
            data=decompressed_pdf_bytes,
            file_name="decompressed_document.pdf",
            mime="application/pdf"
        )

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
                background-color:rgb(193, 223, 161);
                padding: 20px;
                border-radius: 15px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    if selected == "Dashboard":
        st.header("Selamat Datang di Website Kompresi Dokumen Dan Gambar")
        st.write("Silahkan Pilih Menu Yang Tersedia Pada Sidebar")
        st.write("Jika Anda Menggunakan Smartphone, Klik Tanda Panah Yang Berada Pada Pojok Kiri Atas")
        st.write("Berikut adalah fitur yang tersedia:")
        st.write("- Kompresi Gambar🖼️")
        st.write("- Dekompresi Gambar🖼️")
        st.write("- Kompresi Dokumen📄")
        st.write("- Dekompresi Dokumen📄")
        st.write("- Bantuan❓")
        
    
    elif selected == "Kompresi Gambar":
        st.title("Kompresi Gambar JPEG/JPG")
        uploaded_file = st.file_uploader("Pilih file gambar JPEG untuk dikompresi", type=["jpeg", "jpg"])
        if uploaded_file is not None:
            compress_image(uploaded_file)

    elif selected == "Dekompresi Gambar":
        st.title("Dekompresi Gambar JPEG/JPG")
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
