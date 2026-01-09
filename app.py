import streamlit as st
import PyPDF2
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import edge_tts
import asyncio
import tempfile
import io

# Configuración
st.set_page_config(page_title="Lector Luigi Móvil", page_icon="📱", layout="centered")

st.title("📱 Lector Luigi: Versión Móvil")
st.write("Visualización garantizada en celular y voces humanas.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración")
    
    # Selector de Voz
    opcion_voz = st.selectbox(
        "Elige la Voz:",
        [
            ("es-VE-SebastianNeural", "Sebastián (Venezolano)"),
            ("es-MX-DaliaNeural", "Dalia (Mexicana)"),
            ("es-AR-TomasNeural", "Tomás (Argentino)"),
            ("es-ES-AlvaroNeural", "Álvaro (Español)")
        ],
        format_func=lambda x: x[1]
    )
    voz_elegida = opcion_voz[0]

# --- FUNCIONES ---
async def generar_audio(texto, voz):
    if not texto.strip(): return None
    comunicador = edge_tts.Communicate(texto, voz)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        await comunicador.save(fp.name)
        return fp.name

# --- APP PRINCIPAL ---
archivo = st.file_uploader("📂 Sube tu PDF o Foto", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    # 1. ES UN PDF
    if "pdf" in archivo.type:
        # Leemos el archivo para texto y para imagen
        archivo_bytes = archivo.read() 
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
        total_paginas = len(lector_pdf.pages)
        
        st.info(f"📘 Libro de {total_paginas} páginas")

        # Control de navegación
        if 'pagina_actual' not in st.session_state: st.session_state.pagina_actual = 0
        
        # Botones grandes para celular
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("⬅️"):
                if st.session_state.pagina_actual > 0:
                    st.session_state.pagina_actual -= 1
                    st.rerun()
        with c3:
            if st.button("➡️"):
                if st.session_state.pagina_actual < total_paginas - 1:
                    st.session_state.pagina_actual += 1
                    st.rerun()
        
        with c2:
            st.write(f"Pág **{st.session_state.pagina_actual + 1}** de {total_paginas}")

        # --- VISUALIZACIÓN (La magia para que se vea en celular) ---
        with st.spinner("Cargando imagen de la página..."):
            try:
                # Convertimos SOLO la página actual a imagen
                # poppler_path=None asume que está en el PATH del sistema (packages.txt)
                imagenes = convert_from_bytes(
                    archivo_bytes, 
                    first_page=st.session_state.pagina_actual + 1, 
                    last_page=st.session_state.pagina_actual + 1
                )
                if imagenes:
                    st.image(imagenes[0], caption=f"Página {st.session_state.pagina_actual + 1}", use_container_width=True)
            except Exception as e:
                st.error("No se pudo visualizar la imagen. Verifica que 'poppler-utils' esté en packages.txt")

        # --- LECTURA ---
        try:
            pagina_obj = lector_pdf.pages[st.session_state.pagina_actual]
            texto = pagina_obj.extract_text()
            
            if st.button("▶️ ESCUCHAR PÁGINA (Voz Humana)", type="primary", use_container_width=True):
                if texto and texto.strip():
                    with st.spinner("Generando voz neural..."):
                        ruta_audio = asyncio.run(generar_audio(texto, voz_elegida))
                        st.audio(ruta_audio, format='audio/mp3')
                else:
                    st.warning("Esta página parece ser solo una imagen sin texto seleccionable.")
        except:
            st.error("Error al extraer texto.")

    # 2. ES UNA IMAGEN
    else:
        imagen = Image.open(archivo)
        st.image(imagen, use_container_width=True)
        
        if st.button("▶️ Leer Foto", type="primary", use_container_width=True):
            with st.spinner("Analizando..."):
                texto = pytesseract.image_to_string(imagen, lang='spa')
                if texto.strip():
                    ruta = asyncio.run(generar_audio(texto, voz_elegida))
                    st.audio(ruta, format='audio/mp3')

else:
    st.info("Sube un archivo para comenzar.")
