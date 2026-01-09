import streamlit as st
import PyPDF2
from PIL import Image
import pytesseract
import edge_tts
import asyncio
import tempfile
import os

# Configuración
st.set_page_config(page_title="Lector Luigi Neural", page_icon="🧠", layout="centered")

st.title("🧠 Lector Luigi: Voces Humanas")

# --- BARRA LATERAL (Configuración) ---
with st.sidebar:
    st.header("🎛️ Configuración")
    
    # 1. Selector de Voz
    st.subheader("1. Elige la Voz")
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

    st.divider()

    # 2. Selector de Modo
    st.subheader("2. Modo de Lectura")
    modo_lectura = st.radio(
        "¿Cómo quieres leer?",
        ["Página por página", "Lectura Continua (Todo de corrido)"],
        index=0
    )

# --- FUNCIONES ---
async def generar_audio(texto, voz):
    if not texto.strip():
        return None
    comunicador = edge_tts.Communicate(texto, voz)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        await comunicador.save(fp.name)
        return fp.name

# --- INTERFAZ PRINCIPAL ---
archivo = st.file_uploader("📂 Sube PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    tipo_archivo = archivo.type
    
    # ==============================
    # CASO PDF
    # ==============================
    if "pdf" in tipo_archivo:
        lector_pdf = PyPDF2.PdfReader(archivo)
        total_paginas = len(lector_pdf.pages)
        st.success(f"📘 PDF cargado: {total_paginas} páginas disponibles.")

        # --- MODO 1: PÁGINA POR PÁGINA ---
        if modo_lectura == "Página por página":
            if 'pagina_actual' not in st.session_state:
                st.session_state.pagina_actual = 0
            
            # Navegación
            st.slider("Ir a página:", 0, total_paginas - 1, key="pagina_actual")
            
            # Extraer texto de UNA página
            try:
                pagina = lector_pdf.pages[st.session_state.pagina_actual]
                texto_a_leer = pagina.extract_text()
                st.info(f"📖 Estás en la página {st.session_state.pagina_actual + 1}")
                
                with st.expander("Ver texto de esta página"):
                    st.write(texto_a_leer)
                
                if st.button("▶️ Leer esta página"):
                    with st.spinner("Generando audio..."):
                        audio_path = asyncio.run(generar_audio(texto_a_leer, voz_elegida))
                        if audio_path:
                            st.audio(audio_path, format='audio/mp3')
                        else:
                            st.warning("Página vacía.")
            except Exception as e:
                st.error(f"Error leyendo página: {e}")

        # --- MODO 2: LECTURA CONTINUA ---
        else:
            st.info("🎙️ Modo Continuo: Generaré un solo audio con todas las páginas que elijas.")
            
            col1, col2 = st.columns(2)
            with col1:
                inicio = st.number_input("Desde la página:", min_value=1, max_value=total_paginas, value=1)
            with col2:
                fin = st.number_input("Hasta la página:", min_value=1, max_value=total_paginas, value=min(5, total_paginas)) # Default a 5 pags para no saturar de inicio
            
            if inicio > fin:
                st.error("La página de inicio no puede ser mayor que la final.")
            else:
                if st.button("▶️ Generar Audio Completo (De corrido)", type="primary"):
                    texto_completo = ""
                    barra_progreso = st.progress(0)
                    
                    # Loop para extraer texto de todas las páginas seleccionadas
                    with st.spinner(f"Extrayendo texto de la pág {inicio} a la {fin}..."):
                        rango_paginas = range(inicio - 1, fin)
                        total_rango = len(rango_paginas)
                        
                        for i, num_pag in enumerate(rango_paginas):
                            try:
                                pagina = lector_pdf.pages[num_pag]
                                txt = pagina.extract_text()
                                if txt:
                                    texto_completo += f"\n\n --- Página {num_pag + 1} --- \n\n" + txt
                            except:
                                pass
                            # Actualizar barra
                            barra_progreso.progress((i + 1) / total_rango)
                    
                    # Generar audio
                    if texto_completo.strip():
                        st.success(f"Texto extraído ({len(texto_completo)} caracteres). Generando voz humana, espera un momento...")
                        try:
                            audio_path = asyncio.run(generar_audio(texto_completo, voz_elegida))
                            st.audio(audio_path, format='audio/mp3')
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error al generar audio: {e}. Intenta con menos páginas.")
                    else:
                        st.warning("No se encontró texto en el rango seleccionado.")

    # ==============================
    # CASO IMAGEN
    # ==============================
    else:
        # Imágenes siempre son "de corrido" porque es una sola cosa
        imagen = Image.open(archivo)
        st.image(imagen, caption="Imagen cargada", use_container_width=True)
        
        if st.button("▶️ Leer Imagen"):
            with st.spinner("Leyendo imagen y generando audio..."):
                texto = pytesseract.image_to_string(imagen, lang='spa')
                if texto.strip():
                    audio_path = asyncio.run(generar_audio(texto, voz_elegida))
                    st.audio(audio_path, format='audio/mp3')
                else:
                    st.warning("No pude leer texto en la imagen.")

else:
    st.info("Sube un archivo para comenzar.")
