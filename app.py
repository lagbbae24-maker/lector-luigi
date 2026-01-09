import streamlit as st
import PyPDF2
# Intentamos importar, si falla, no pasa nada
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
st.set_page_config(page_title="Lector Luigi Seguro", page_icon="🛡️", layout="wide")

st.title("🛡️ Lector Luigi (Modo Seguro)")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración")
    
    opcion_voz = st.selectbox(
        "Narrador:",
        [
            ("es-VE-SebastianNeural", "Sebastián (Hombre - Venezuela)"),
            ("es-MX-DaliaNeural", "Dalia (Mujer - México)"),
            ("es-AR-TomasNeural", "Tomás (Hombre - Argentina)"),
            ("es-ES-AlvaroNeural", "Álvaro (Hombre - España)")
        ],
        format_func=lambda x: x[1]
    )
    voz_elegida = opcion_voz[0]
    
    modo_lectura = st.radio("Modo:", ["Manual (Pág por pág)", "Continuo (Rango)"])

# --- FUNCIÓN AUDIO ---
async def generar_audio(texto, voz):
    if not texto.strip(): return None
    try:
        comunicador = edge_tts.Communicate(texto, voz)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            await comunicador.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"Error generando audio: {e}")
        return None

# --- APP PRINCIPAL ---
archivo = st.file_uploader("📂 Sube PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    col_izq, col_der = st.columns([1, 1])
    archivo_bytes = archivo.read()
    tipo = archivo.type

    # ==================== CASO PDF ====================
    if "pdf" in tipo:
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
        total_paginas = len(lector_pdf.pages)
        
        if 'pagina_actual' not in st.session_state: st.session_state.pagina_actual = 0

        # 1. INTENTO DE VISUALIZACIÓN (IZQUIERDA)
        with col_izq:
            st.subheader("📄 Vista")
            imagen_mostrada = False
            
            # Solo intentamos si la librería cargó y el archivo es válido
            if TIENE_VISUALIZADOR:
                try:
                    with st.spinner("Cargando imagen..."):
                        imagenes = convert_from_bytes(
                            archivo_bytes,
                            first_page=st.session_state.pagina_actual + 1,
                            last_page=st.session_state.pagina_actual + 1
                        )
                        if imagenes:
                            st.image(imagenes[0], caption=f"Pág {st.session_state.pagina_actual + 1}", use_container_width=True)
                            imagen_mostrada = True
                except Exception:
                    # Si falla, no hacemos nada, pasamos al 'else' de abajo
                    pass
            
            if not imagen_mostrada:
                st.warning("⚠️ No se pudo generar la vista previa (falta Poppler).")
                st.info("Pero no te preocupes, **el audio funcionará igual**.")
                st.markdown(f"**Estás en la página {st.session_state.pagina_actual + 1} de {total_paginas}**")

        # 2. CONTROLES DE AUDIO (DERECHA)
        with col_der:
            st.subheader("🎧 Reproductor")
            
            # MODO MANUAL
            if modo_lectura == "Manual (Pág por pág)":
                c1, c2 = st.columns(2)
                if c1.button("⬅️ Ant."):
                    if st.session_state.pagina_actual > 0:
                        st.session_state.pagina_actual -= 1
                        st.rerun()
                if c2.button("Sig. ➡️"):
                    if st.session_state.pagina_actual < total_paginas - 1:
                        st.session_state.pagina_actual += 1
                        st.rerun()
                
                # Extraer texto (Esto usa PyPDF2, es muy robusto)
                try:
                    texto = lector_pdf.pages[st.session_state.pagina_actual].extract_text()
                    if st.button("▶️ ESCUCHAR PÁGINA", type="primary"):
                        if texto:
                            audio = asyncio.run(generar_audio(texto, voz_elegida))
                            if audio: st.audio(audio, format='audio/mp3')
                        else:
                            st.warning("Página vacía (puede ser una imagen escaneada).")
                except:
                    st.error("Error leyendo texto del PDF.")

            # MODO CONTINUO
            else:
                st.info("Lectura de corrido")
                ini = st.number_input("Desde:", 1, total_paginas, 1)
                fin = st.number_input("Hasta:", 1, total_paginas, min(5, total_paginas))
                
                if st.button("▶️ REPRODUCIR RANGO", type="primary"):
                    txt_completo = ""
                    prog = st.progress(0)
                    rango = range(ini-1, fin)
                    for i, p in enumerate(rango):
                        try:
                            t = lector_pdf.pages[p].extract_text()
                            if t: txt_completo += f"\n Pág {p+1}. {t}"
                        except: pass
                        prog.progress((i+1)/len(rango))
                    
                    if txt_completo:
                        audio = asyncio.run(generar_audio(txt_completo, voz_elegida))
                        if audio: st.audio(audio, format='audio/mp3')

    # ==================== CASO IMAGEN ====================
    else:
        st.image(archivo, use_container_width=True)
        if st.button("▶️ LEER FOTO"):
            txt = pytesseract.image_to_string(Image.open(archivo), lang='spa')
            if txt:
                audio = asyncio.run(generar_audio(txt, voz_elegida))
                st.audio(audio, format='audio/mp3')
else:
    st.info("Sube un archivo.")
