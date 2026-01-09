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
st.set_page_config(page_title="Lector Luigi Pro", page_icon="🎧", layout="wide")

st.title("🎧 Lector Luigi: Visualización y Audio")

# --- GESTIÓN DE MEMORIA ---
if 'audio_actual' not in st.session_state:
    st.session_state.audio_actual = None
if 'pagina_vista' not in st.session_state:
    st.session_state.pagina_vista = 0

# --- BARRA LATERAL (Solo Configuración) ---
with st.sidebar:
    st.header("🎛️ Configuración")
    
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

    velocidad = st.slider("Velocidad:", -50, 50, -10, format="%d%%")
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
        st.error(f"Error: {e}")
        return None

# --- APP PRINCIPAL ---
archivo = st.file_uploader("📂 Sube tu PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    # Definimos columnas: Izquierda (Visual) | Derecha (Audio y Controles)
    col_izq, col_der = st.columns([1, 1])
    archivo_bytes = archivo.read()
    
    # ==================== CASO PDF ====================
    if "pdf" in archivo.type:
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
        total_paginas = len(lector_pdf.pages)
        
        # --- COLUMNA IZQUIERDA: VISUALIZACIÓN ---
        with col_izq:
            st.subheader("👁️ Visualizador")
            
            # Botones de navegación (Visual)
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
                st.markdown(f"<div style='text-align: center; font-weight: bold;'>Página {st.session_state.pagina_vista + 1}</div>", unsafe_allow_html=True)

            # Imagen de la página
            if TIENE_VISUALIZADOR:
                try:
                    imgs = convert_from_bytes(
                        archivo_bytes,
                        first_page=st.session_state.pagina_vista + 1,
                        last_page=st.session_state.pagina_vista + 1
                    )
                    if imgs:
                        st.image(imgs[0], use_container_width=True)
                except:
                    st.warning("Visualización no disponible.")

        # --- COLUMNA DERECHA: REPRODUCTOR Y GENERADOR ---
        with col_der:
            st.subheader("🎧 Reproductor")
            
            # 1. EL REPRODUCTOR (Siempre visible arriba)
            st.markdown("---")
            if st.session_state.audio_actual:
                st.audio(st.session_state.audio_actual, format='audio/mp3')
                st.success("✅ Audio cargado. Dale Play.")
            else:
                st.info("Genera un audio abajo para escuchar.")
            st.markdown("---")

            # 2. GENERADOR (Controles)
            st.write("📖 **Crear nuevo audio**")
            
            # Usamos el estado de visualización como sugerencia de inicio
            pg_inicio = st.session_state.pagina_vista + 1
            
            c1, c2 = st.columns(2)
            inicio = c1.number_input("Desde pág:", 1, total_paginas, value=pg_inicio)
            fin = c2.number_input("Hasta pág:", 1, total_paginas, value=min(pg_inicio + 5, total_paginas))
            
            if st.button("▶️ GENERAR AUDIO", type="primary", use_container_width=True):
                if inicio > fin:
                    st.error("Error en rango.")
                else:
                    texto_completo = ""
                    barra = st.progress(0)
                    rango = range(inicio - 1, fin)
                    
                    with st.spinner("Procesando..."):
                        for i, p in enumerate(rango):
                            try:
                                txt = lector_pdf.pages[p].extract_text()
                                if txt: texto_completo += f"\n... Pág {p+1} ...\n{txt}"
                            except: pass
                            barra.progress((i + 1) / len(rango))
                    
                    if texto_completo.strip():
                        ruta = asyncio.run(generar_audio(texto_completo, voz_elegida, tasa_str))
                        if ruta:
                            st.session_state.audio_actual = ruta # Guardamos en memoria
                            st.rerun() # Recargamos para que aparezca arriba
                    else:
                        st.warning("No hay texto.")

    # ==================== CASO IMAGEN ====================
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.image(archivo, use_container_width=True)
        with c2:
            if st.button("▶️ LEER FOTO", type="primary"):
                txt = pytesseract.image_to_string(Image.open(archivo), lang='spa')
                if txt:
                    ruta = asyncio.run(generar_audio(txt, voz_elegida, tasa_str))
                    st.session_state.audio_actual = ruta
                    st.rerun()
            
            if st.session_state.audio_actual:
                st.audio(st.session_state.audio_actual, format='audio/mp3')

else:
    st.info("Sube un archivo para comenzar.")
