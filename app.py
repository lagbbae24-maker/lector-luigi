import streamlit as st
import PyPDF2
from gtts import gTTS
import io

# Configuración de la página para que parezca App de celular
st.set_page_config(page_title="Lector Luigi", page_icon="🎧", layout="centered")

# Título y estilo
st.title("🎧 Mi Lector de Libros")
st.markdown("---")

# --- LÓGICA DE LA APP ---

# 1. Subir el libro
archivo_pdf = st.file_uploader("📂 Sube tu libro (PDF)", type=["pdf"])

if archivo_pdf is not None:
    # Leer el PDF
    lector_pdf = PyPDF2.PdfReader(archivo_pdf)
    total_paginas = len(lector_pdf.pages)
    
    st.success(f"Libro cargado: {total_paginas} páginas detectadas.")

    # 2. Control de navegación (Memoria de dónde te quedaste)
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = 0

    # Selector de página (Slider para saltar rápido)
    pagina_seleccionada = st.slider("Ir a la página:", 0, total_paginas - 1, st.session_state.pagina_actual)
    st.session_state.pagina_actual = pagina_seleccionada

    # Extraer texto de la página actual
    pagina = lector_pdf.pages[st.session_state.pagina_actual]
    texto = pagina.extract_text()

    # Mostrar texto en pantalla (para que puedas seguir la lectura)
    st.info(f"📖 Página {st.session_state.pagina_actual + 1} de {total_paginas}")
    with st.expander("Ver texto de esta página"):
        st.write(texto)

    # 3. Botón para LEER
    if st.button("▶️ Leer esta página ahora", type="primary", use_container_width=True):
        if texto.strip():
            with st.spinner("Procesando voz..."):
                # Convertir a audio
                tts = gTTS(text=texto, lang='es')
                # Guardar en memoria virtual (no en disco duro) para rapidez
                audio_bytes = io.BytesIO()
                tts.write_to_fp(audio_bytes)
                audio_bytes.seek(0)
                
                # Reproductor
                st.audio(audio_bytes, format='audio/mp3')
        else:
            st.warning("Esta página parece estar vacía o son solo imágenes.")

    # 4. Botones de Siguiente / Anterior grandes para el dedo
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True):
            if st.session_state.pagina_actual > 0:
                st.session_state.pagina_actual -= 1
                st.rerun()
    with col2:
        if st.button("Siguiente ➡️", use_container_width=True):
            if st.session_state.pagina_actual < total_paginas - 1:
                st.session_state.pagina_actual += 1
                st.rerun()

else:
    st.info("Sube un PDF para comenzar.")
