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
st.set_page_config(page_title="Lector Luigi Navegable", page_icon="🎧", layout="wide")

st.title("🎧 Lector Luigi: Escucha y Navega")

# --- GESTIÓN DE ESTADO (MEMORIA) ---
# Aquí guardamos el audio para que NO se borre al navegar
if 'audio_actual' not in st.session_state:
    st.session_state.audio_actual = None
if 'pagina_vista' not in st.session_state:
    st.session_state.pagina_vista = 0

# --- BARRA LATERAL (CONFIGURACIÓN Y REPRODUCTOR) ---
with st.sidebar:
    st.header("🎛️ Configuración")
    
    # 1. EL REPRODUCTOR (Ahora vive aquí para no desaparecer)
    st.divider()
    st.subheader("🎵 Tu Reproductor")
    if st.session_state.audio_actual:
        st.audio(st.session_state.audio_actual, format='audio/mp3')
        st.success("Reproduciendo...")
    else:
        st.info("Genera un audio para que aparezca aquí.")
    st.divider()

    # 2. Configuración de Voz
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
    col_izq, col_der = st.columns([1, 1])
    archivo_bytes = archivo.read()
    
    # ==================== CASO PDF ====================
    if "pdf" in archivo.type:
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
        total_paginas = len(lector_pdf.pages)
        
        # --- COLUMNA IZQUIERDA: VISOR DEL PDF (NAVEGACIÓN) ---
        with col_izq:
            st.subheader("👁️ Explorar Libro")
            
            # Botones de Navegación Visual
            c_ant, c_info, c_sig = st.columns([1, 2, 1])
            
            with c_ant:
                if st.button("⬅️ Atrás", use_container_width=True):
                    if st.session_state.pagina_vista > 0:
                        st.session_state.pagina_vista -= 1
                        st.rerun() # Recarga solo para mostrar la nueva foto
            
            with c_sig:
                if st.button("Adelante ➡️", use_container_width=True):
                    if st.session_state.pagina_vista < total_paginas - 1:
                        st.session_state.pagina_vista += 1
                        st.rerun() # Recarga solo para mostrar la nueva foto
            
            with c_info:
                st.markdown(f"<div style='text-align: center; font-weight: bold; padding-top: 10px;'>Página {st.session_state.pagina_vista + 1} de {total_paginas}</div>", unsafe_allow_html=True)

            # Mostrar la imagen
            if TIENE_VISUALIZADOR:
                try:
                    with st.spinner("Cargando página..."):
                        imgs = convert_from_bytes(
                            archivo_bytes,
                            first_page=st.session_state.pagina_vista + 1,
                            last_page=st.session_state.pagina_vista + 1
                        )
                        if imgs:
                            st.image(imgs[0], use_container_width=True)
                except:
                    st.warning("Visualización no disponible.")

        # --- COLUMNA DERECHA: GENERADOR DE AUDIO ---
        with col_der:
            st.subheader("🎧 Generar Audio")
            st.write("Configura qué quieres escuchar. El audio aparecerá en la **Barra Lateral** para que no se pierda.")
            
            # Inputs para el rango
            c_inicio, c_fin = st.columns(2)
            inicio = c_inicio.number_input("Desde pág:", 1, total_paginas, value=st.session_state.pagina_vista + 1)
            fin = c_fin.number_input("Hasta pág:", 1, total_paginas, value=min(st.session_state.pagina_vista + 5, total_paginas))
            
            if st.button("▶️ CREAR AUDIO (RANGO)", type="primary", use_container_width=True):
                if inicio > fin:
                    st.error("Error: Inicio mayor que fin.")
                else:
                    texto_completo = ""
                    barra = st.progress(0)
                    rango = range(inicio - 1, fin)
                    
                    with st.spinner(f"Procesando audio..."):
                        for i, p in enumerate(rango):
                            try:
                                txt = lector_pdf.pages[p].extract_text()
                                if txt: 
                                    texto_completo += f"\n... Página {p+1} ...\n{txt}"
                            except: pass
                            barra.progress((i + 1) / len(rango))
                    
                    if texto_completo.strip():
                        # Generamos el audio y lo guardamos en MEMORIA (Session State)
                        ruta = asyncio.run(generar_audio(texto_completo, voz_elegida, tasa_str))
                        if ruta:
                            st.session_state.audio_actual = ruta
                            st.success("¡Audio listo! Mira la barra lateral 👈")
                            st.rerun() # Recargamos para que aparezca el player
                    else:
                        st.warning("No hay texto en esas páginas.")

    # ==================== CASO IMAGEN ====================
    else:
        st.image(archivo, use_container_width=True)
        if st.button("▶️ LEER FOTO", type="primary", use_container_width=True):
            txt = pytesseract.image_to_string(Image.open(archivo), lang='spa')
            if txt:
                ruta = asyncio.run(generar_audio(txt, voz_elegida, tasa_str))
                st.session_state.audio_actual = ruta
                st.rerun()

else:
    st.info("Sube un PDF para comenzar.")
