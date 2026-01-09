import streamlit as st
import PyPDF2
from gtts import gTTS
from PIL import Image
import pytesseract
import io

# Configuración de la página
st.set_page_config(page_title="Lector Luigi", page_icon="🎧", layout="centered")

st.title("🎧 Lector Luigi 2.0")
st.markdown("### Lee PDFs y también Imágenes 📸")
st.markdown("---")

# --- LÓGICA DE LA APP ---

# 1. Subir archivo (PDF o Imagen)
archivo = st.file_uploader("📂 Sube tu libro (PDF) o Foto (JPG/PNG)", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    texto_a_leer = ""
    tipo_archivo = archivo.type
    
    # CASO 1: Es un PDF
    if "pdf" in tipo_archivo:
        lector_pdf = PyPDF2.PdfReader(archivo)
        total_paginas = len(lector_pdf.pages)
        st.success(f"📘 PDF cargado: {total_paginas} páginas.")

        # Control de páginas del PDF
        if 'pagina_actual' not in st.session_state:
            st.session_state.pagina_actual = 0
            
        st.slider("Ir a la página:", 0, total_paginas - 1, key="pagina_actual")
        
        try:
            pagina = lector_pdf.pages[st.session_state.pagina_actual]
            texto_a_leer = pagina.extract_text()
            st.info(f"📖 Página {st.session_state.pagina_actual + 1}")
        except:
            st.error("Error al leer esta página del PDF.")

    # CASO 2: Es una Imagen
    else:
        st.success("📸 Imagen cargada correctamente.")
        # Mostrar la imagen que subió
        imagen = Image.open(archivo)
        st.image(imagen, caption="Tu foto subida", use_container_width=True)
        
        # Usar los "ojos" (OCR) para leer el texto
        with st.spinner("👀 Luigi está leyendo la imagen..."):
            try:
                # Extraer texto de la imagen (en español)
                texto_a_leer = pytesseract.image_to_string(imagen, lang='spa')
            except Exception as e:
                st.error("Error: No pude leer el texto. Asegúrate de haber creado el archivo 'packages.txt'.")

    # --- MOSTRAR Y LEER EL TEXTO (Común para ambos) ---
    
    if texto_a_leer:
        with st.expander("Ver texto detectado", expanded=True):
            st.write(texto_a_leer)
            
        if st.button("▶️ Escuchar texto", type="primary", use_container_width=True):
            if texto_a_leer.strip():
                with st.spinner("Procesando voz..."):
                    try:
                        tts = gTTS(text=texto_a_leer, lang='es')
                        audio_bytes = io.BytesIO()
                        tts.write_to_fp(audio_bytes)
                        audio_bytes.seek(0)
                        st.audio(audio_bytes, format='audio/mp3')
                    except Exception as e:
                        st.error(f"Error de audio: {e}")
            else:
                st.warning("No encontré texto legible. ¿La imagen está borrosa?")
    else:
        st.warning("No se pudo extraer texto. Intenta con otra página o foto.")

else:
    st.info("Sube un archivo para comenzar.")
