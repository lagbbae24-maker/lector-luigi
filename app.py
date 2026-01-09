import streamlit as st
import PyPDF2
from gtts import gTTS
import io

# Configuración de la página
st.set_page_config(page_title="Lector Luigi", page_icon="🎧", layout="centered")

# Título
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

    # 2. Control de navegación (Memoria)
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = 0

    # --- CORRECCIÓN IMPORTANTE AQUÍ ---
    # Usamos 'key' para vincular el slider directamente a la memoria
    # Esto evita que los botones y la barra se peleen.
    st.slider("Ir a la página:", 0, total_paginas - 1, key="pagina_actual")
    # ----------------------------------

    # Extraer texto con seguridad
    try:
        pagina = lector_pdf.pages[st.session_state.pagina_actual]
        texto = pagina.extract_text()
    except:
        texto = "Error al leer esta página."

    # Mostrar texto
    st.info(f"📖 Página {st.session_state.pagina_actual + 1} de {total_paginas}")
    with st.expander("Ver texto de esta página", expanded=True):
        st.write(texto)

    # 3. Botón para LEER
    if st.button("▶️ Leer esta página ahora", type="primary", use_container_width=True):
        if texto and texto.strip():
            with st.spinner("Procesando voz..."):
                try:
                    tts = gTTS(text=texto, lang='es')
                    audio_bytes = io.BytesIO()
                    tts.write_to_fp(audio_bytes)
                    audio_bytes.seek(0)
                    st.audio(audio_bytes, format='audio/mp3')
                except Exception as e:
                    st.error(f"Error de conexión con Google: {e}")
        else:
            st.warning("Esta página parece estar vacía o son solo imágenes.")

    # 4. Botones de Navegación
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True):
            if st.session_state.pagina_actual > 0:
                st.session_state.pagina_actual -= 1
                st.rerun() # Recarga para actualizar la página
    with col2:
        if st.button("Siguiente ➡️", use_container_width=True):
            if st.session_state.pagina_actual < total_paginas - 1:
                st.session_state.pagina_actual += 1
                st.rerun() # Recarga para actualizar la página

else:
    st.info("Sube un PDF para comenzar.")
