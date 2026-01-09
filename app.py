import streamlit as st
import PyPDF2
try:
    from pdf2image import convert_from_bytes
    TIENE_VISUALIZADOR = True
except ImportError:
    TIENE_VISUALIZADOR = False

from PIL import Image
import pytesseract
import edge_tts
import asyncio
import tempfile
import io

# Configuración
st.set_page_config(page_title="Lector Luigi Final", page_icon="🎧", layout="wide")
st.title("🎧 Lector Luigi: Audio Continuo")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🎛️ Configuración")
    
    # 1. Voces
    opcion_voz = st.selectbox(
        "Narrador:",
        [
            ("es-VE-SebastianNeural", "Sebastián (Vzla - Calmado)"),
            ("es-MX-DaliaNeural", "Dalia (Mex - Profesional)"),
            ("es-ES-AlvaroNeural", "Álvaro (Esp - Profundo)"),
            ("es-AR-TomasNeural", "Tomás (Arg - Suave)"),
        ],
        format_func=lambda x: x[1]
    )
    voz_elegida = opcion_voz[0]

    st.divider()

    # 2. Velocidad
    st.caption("Ajuste de Velocidad:")
    velocidad = st.slider("Ritmo:", -50, 50, -10, format="%d%%")
    tasa_str = f"{velocidad:+d}%"

# --- FUNCIÓN AUDIO ---
async def generar_audio(texto, voz, tasa):
    if not texto.strip(): return None
    try:
        comunicador = edge_tts.Communicate(texto, voz, rate=tasa)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            await comunicador.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"Error generando audio: {e}")
        return None

# --- APP PRINCIPAL ---
archivo = st.file_uploader("📂 Sube tu PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    col_izq, col_der = st.columns([1, 1])
    archivo_bytes = archivo.read()
    
    # ==================== CASO PDF ====================
    if "pdf" in archivo.type:
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
        total_paginas = len(lector_pdf.pages)
        
        # Variable para controlar QUÉ PÁGINA ESTAMOS MIRANDO (Solo visual)
        if 'pagina_vista' not in st.session_state: 
            st.session_state.pagina_vista = 0

        # --- COLUMNA IZQUIERDA: VISOR DEL PDF ---
        with col_izq:
            st.subheader("👁️ Explorar Libro")
            
            # Botones de Navegación Visual
            c_ant, c_info, c_sig = st.columns([1, 2, 1])
            
            with c_ant:
                if st.button("⬅️", use_container_width=True):
                    if st.session_state.pagina_vista > 0:
                        st.session_state.pagina_vista -= 1
                        st.rerun()
            
            with c_sig:
                if st.button("➡️", use_container_width=True):
                    if st.session_state.pagina_vista < total_paginas - 1:
                        st.session_state.pagina_vista += 1
                        st.rerun()
            
            with c_info:
                st.markdown(f"<div style='text-align: center; font-weight: bold;'>Página {st.session_state.pagina_vista + 1} de {total_paginas}</div>", unsafe_allow_html=True)

            # Mostrar la imagen de la página actual
            if TIENE_VISUALIZADOR:
                try:
                    with st.spinner("Cargando vista..."):
                        imgs = convert_from_bytes(
                            archivo_bytes,
                            first_page=st.session_state.pagina_vista + 1,
                            last_page=st.session_state.pagina_vista + 1
                        )
                        if imgs:
                            st.image(imgs[0], use_container_width=True)
                except:
                    st.warning("No se puede ver la imagen, pero el audio funciona.")
            else:
                st.warning("Instala poppler para ver las imágenes.")

        # --- COLUMNA DERECHA: REPRODUCTOR (LECTURA CONTINUA) ---
        with col_der:
            st.subheader("🎧 Reproductor")
            st.info("Selecciona el rango de páginas que quieres escuchar de corrido.")
            
            # Inputs para el rango
            c_inicio, c_fin = st.columns(2)
            # Por defecto, sugiere empezar donde estás mirando
            inicio = c_inicio.number_input("Desde pág:", 1, total_paginas, value=st.session_state.pagina_vista + 1)
            fin = c_fin.number_input("Hasta pág:", 1, total_paginas, value=min(st.session_state.pagina_vista + 5, total_paginas))
            
            if st.button("▶️ REPRODUCIR RANGO SELECCIONADO", type="primary", use_container_width=True):
                if inicio > fin:
                    st.error("Error: La página final debe ser mayor a la inicial.")
                else:
                    texto_completo = ""
                    barra = st.progress(0)
                    rango = range(inicio - 1, fin)
                    
                    with st.spinner(f"Procesando páginas {inicio} a {fin}..."):
                        for i, p in enumerate(rango):
                            try:
                                txt = lector_pdf.pages[p].extract_text()
                                if txt: 
                                    # Añadimos una pequeña pausa en texto entre páginas
                                    texto_completo += f"\n... Página {p+1} ...\n{txt}"
                            except: pass
                            barra.progress((i + 1) / len(rango))
                    
                    if texto_completo.strip():
                        with st.spinner("Generando narración humana..."):
                            ruta = asyncio.run(generar_audio(texto_completo, voz_elegida, tasa_str))
                            if ruta:
                                st.success("¡Audio listo!")
                                st.audio(ruta, format='audio/mp3')
                    else:
                        st.warning("No encontré texto legible en esas páginas.")

    # ==================== CASO IMAGEN ====================
    else:
        st.image(archivo, use_container_width=True)
        if st.button("▶️ LEER FOTO", type="primary", use_container_width=True):
            txt = pytesseract.image_to_string(Image.open(archivo), lang='spa')
            if txt:
                ruta = asyncio.run(generar_audio(txt, voz_elegida, tasa_str))
                st.audio(ruta, format='audio/mp3')

else:
    st.info("Sube un PDF para comenzar.")
