import streamlit as st
import PyPDF2
from PIL import Image
import pytesseract
import edge_tts
import asyncio
import tempfile

# Configuración
st.set_page_config(page_title="Lector Luigi Neural", page_icon="🧠", layout="centered")

st.title("🧠 Lector Luigi: Voces Humanas")
st.markdown("Ahora con tecnología **Neural** (No suena robotizado).")

# --- CONFIGURACIÓN DE VOZ ---
st.sidebar.header("configuración de Voz")
opcion_voz = st.sidebar.selectbox(
    "Elige quién lee:",
    [
        ("es-VE-SebastianNeural", "Sebastián (Hombre - Venezuela)"),
        ("es-MX-DaliaNeural", "Dalia (Mujer - México)"),
        ("es-AR-TomasNeural", "Tomás (Hombre - Argentina)"),
        ("es-ES-AlvaroNeural", "Álvaro (Hombre - España)")
    ],
    format_func=lambda x: x[1] # Muestra solo el nombre amigable
)
voz_elegida = opcion_voz[0] # El código real de la voz

# --- LÓGICA DE AUDIO (Función Asíncrona) ---
async def generar_audio(texto, voz):
    comunicador = edge_tts.Communicate(texto, voz)
    # Crear un archivo temporal para guardar el audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        await comunicador.save(fp.name)
        return fp.name

# --- INTERFAZ PRINCIPAL ---

archivo = st.file_uploader("📂 Sube PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    texto_a_leer = ""
    tipo_archivo = archivo.type
    
    # 1. Procesar PDF
    if "pdf" in tipo_archivo:
        lector_pdf = PyPDF2.PdfReader(archivo)
        total_paginas = len(lector_pdf.pages)
        st.success(f"📘 PDF: {total_paginas} páginas.")

        if 'pagina_actual' not in st.session_state:
            st.session_state.pagina_actual = 0
            
        st.slider("Página:", 0, total_paginas - 1, key="pagina_actual")
        
        try:
            pagina = lector_pdf.pages[st.session_state.pagina_actual]
            texto_a_leer = pagina.extract_text()
            st.info(f"📖 Leyendo página {st.session_state.pagina_actual + 1}")
        except:
            st.error("Error leyendo esta página.")

    # 2. Procesar Imagen
    else:
        imagen = Image.open(archivo)
        st.image(imagen, caption="Tu foto", use_container_width=True)
        with st.spinner("👀 Extrayendo texto..."):
            try:
                texto_a_leer = pytesseract.image_to_string(imagen, lang='spa')
            except:
                st.error("Error de OCR. Revisa 'packages.txt'.")

    # --- REPRODUCTOR NEURAL ---
    if texto_a_leer:
        with st.expander("Ver texto"):
            st.write(texto_a_leer)
            
        if st.button("▶️ Narrar con voz humana", type="primary", use_container_width=True):
            if texto_a_leer.strip():
                with st.spinner("Generando voz neural... (esto toma unos segundos)"):
                    try:
                        # Ejecutar la función asíncrona
                        archivo_audio = asyncio.run(generar_audio(texto_a_leer, voz_elegida))
                        
                        # Reproducir
                        st.audio(archivo_audio, format='audio/mp3')
                        st.success("¡Audio generado con éxito!")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("No hay texto para leer.")
    else:
        st.warning("No se detectó texto.")

else:
    st.info("Sube un archivo para probar las nuevas voces.")
