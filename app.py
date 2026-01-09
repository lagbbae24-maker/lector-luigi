import streamlit as st
import PyPDF2
# Importación segura de la herramienta de imagen
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

# Configuración de página ancha
st.set_page_config(page_title="Lector Luigi Free", page_icon="🎧", layout="wide")

st.title("🎧 Lector Luigi: Edición Gratuita")

# --- BARRA LATERAL (AJUSTES DE VOZ) ---
with st.sidebar:
    st.header("🎛️ Panel de Control")
    
    # 1. Voces Gratuitas (Microsoft Edge)
    st.subheader("1. Narrador")
    opcion_voz = st.selectbox(
        "Elige tu voz favorita:",
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

    # 2. Velocidad (Truco de Humanización)
    st.subheader("2. Velocidad")
    st.caption("Baja la velocidad para que suene más real.")
    velocidad = st.slider("Ritmo:", -50, 50, -10, format="%d%%")
    tasa_str = f"{velocidad:+d}%"
    
    st.divider()
    
    # 3. Modo de Lectura
    modo_lectura = st.radio("Modo:", ["Manual (Página por página)", "Continuo (Leer rango)"])

# --- FUNCIÓN DE AUDIO ---
async def generar_audio(texto, voz, tasa):
    if not texto.strip(): return None
    try:
        # Generamos el audio con la velocidad ajustada
        comunicador = edge_tts.Communicate(texto, voz, rate=tasa)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            await comunicador.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"Error de audio: {e}")
        return None

# --- APLICACIÓN PRINCIPAL ---
archivo = st.file_uploader("📂 Sube tu PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    # Columnas: Izquierda (Imagen) | Derecha (Controles)
    col_izq, col_der = st.columns([1, 1])
    archivo_bytes = archivo.read()
    
    # ==================== CASO PDF ====================
    if "pdf" in archivo.type:
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
        total_paginas = len(lector_pdf.pages)
        
        # Inicializar memoria de página
        if 'pagina_actual' not in st.session_state: 
            st.session_state.pagina_actual = 0

        # --- COLUMNA DERECHA: CONTROLES DE NAVEGACIÓN ---
        # (Ponemos esto antes para procesar los clics primero)
        with col_der:
            st.subheader("🕹️ Control de Lectura")
            
            if modo_lectura == "Manual (Página por página)":
                # 1. BARRA DESLIZANTE (SLIDER)
                # Vinculada directamente a la memoria 'pagina_actual'
                pag_seleccionada = st.slider(
                    "Ir a página:", 
                    0, 
                    total_paginas - 1, 
                    key="slider_pagina", 
                    value=st.session_state.pagina_actual
                )
                
                # Si movemos el slider, actualizamos el estado
                if pag_seleccionada != st.session_state.pagina_actual:
                    st.session_state.pagina_actual = pag_seleccionada
                    st.rerun()

                # 2. BOTONES ANTERIOR / SIGUIENTE
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("⬅️ Anterior", use_container_width=True):
                        if st.session_state.pagina_actual > 0:
                            st.session_state.pagina_actual -= 1
                            st.rerun()
                with c2:
                    if st.button("Siguiente ➡️", use_container_width=True):
                        if st.session_state.pagina_actual < total_paginas - 1:
                            st.session_state.pagina_actual += 1
                            st.rerun()

                st.write(f"Estás en la página **{st.session_state.pagina_actual + 1}** de {total_paginas}")

                # 3. BOTÓN DE LEER
                try:
                    texto_pag = lector_pdf.pages[st.session_state.pagina_actual].extract_text()
                    if st.button("▶️ ESCUCHAR ESTA PÁGINA", type="primary", use_container_width=True):
                        if texto_pag:
                            with st.spinner("Generando voz..."):
                                ruta_audio = asyncio.run(generar_audio(texto_pag, voz_elegida, tasa_str))
                                if ruta_audio: 
                                    st.audio(ruta_audio, format='audio/mp3')
                        else:
                            st.warning("Esta página no tiene texto reconocible.")
                except:
                    st.error("Error al leer el texto de la página.")

            # MODO CONTINUO (RANGO)
            else:
                st.info("📖 Lectura de varias páginas seguidas")
                ini = st.number_input("Desde página:", 1, total_paginas, 1)
                fin = st.number_input("Hasta página:", 1, total_paginas, min(5, total_paginas))
                
                if st.button("▶️ REPRODUCIR TODO DE CORRIDO", type="primary"):
                    if ini > fin:
                        st.error("El inicio no puede ser mayor al final.")
                    else:
                        texto_completo = ""
                        progreso = st.progress(0)
                        rango = range(ini-1, fin)
                        
                        for i, p in enumerate(rango):
                            try:
                                txt = lector_pdf.pages[p].extract_text()
                                if txt: texto_completo += f"\n\n--- Pág {p+1} ---\n{txt}"
                            except: pass
                            progreso.progress((i+1)/len(rango))
                        
                        if texto_completo:
                            with st.spinner("Creando audiolibro..."):
                                ruta_audio = asyncio.run(generar_audio(texto_completo, voz_elegida, tasa_str))
                                if ruta_audio: 
                                    st.audio(ruta_audio, format='audio/mp3')

        # --- COLUMNA IZQUIERDA: VISUALIZACIÓN ---
        with col_izq:
            st.subheader("📄 Vista Previa")
            if TIENE_VISUALIZADOR:
                try:
                    with st.spinner("Cargando imagen..."):
                        # Convertimos SOLO la página actual (basada en el estado actualizado)
                        imagenes = convert_from_bytes(
                            archivo_bytes,
                            first_page=st.session_state.pagina_actual + 1,
                            last_page=st.session_state.pagina_actual + 1
                        )
                        if imagenes:
                            st.image(imagenes[0], caption=f"Página {st.session_state.pagina_actual + 1}", use_container_width=True)
                except Exception as e:
                    st.warning("No se pudo visualizar la página (pero el audio funciona).")
            else:
                st.warning("Herramientas de imagen no instaladas.")

    # ==================== CASO IMAGEN ====================
    else:
        st.image(archivo, caption="Imagen cargada", use_container_width=True)
        if st.button("▶️ LEER IMAGEN", type="primary", use_container_width=True):
            texto = pytesseract.image_to_string(Image.open(archivo), lang='spa')
            if texto:
                ruta_audio = asyncio.run(generar_audio(texto, voz_elegida, tasa_str))
                st.audio(ruta_audio, format='audio/mp3')

else:
    st.info("Sube un archivo PDF o Imagen para empezar.")
