import streamlit as st
import PyPDF2
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import edge_tts
import asyncio
import tempfile
import io

# Configuración WIDE para que quepa "al lado" en pantallas grandes
st.set_page_config(page_title="Lector Luigi Pro", page_icon="🧠", layout="wide")

st.title("🧠 Lector Luigi: Completo")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🎛️ Configuración")
    
    # 1. Selector de Voz
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
    st.subheader("Modo de Lectura")
    modo_lectura = st.radio(
        "¿Cómo quieres leer?",
        ["Página por página (Manual)", "Lectura Continua (Rango)"],
        index=0
    )

# --- FUNCIÓN DE AUDIO ---
async def generar_audio(texto, voz):
    if not texto.strip(): return None
    comunicador = edge_tts.Communicate(texto, voz)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        await comunicador.save(fp.name)
        return fp.name

# --- INTERFAZ PRINCIPAL ---
archivo = st.file_uploader("📂 Sube PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    # Crear columnas: Izquierda (Visual) - Derecha (Controles)
    col_izq, col_der = st.columns([1, 1])
    
    archivo_bytes = archivo.read()
    tipo_archivo = archivo.type

    # ==============================
    # CASO PDF
    # ==============================
    if "pdf" in tipo_archivo:
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
        total_paginas = len(lector_pdf.pages)

        # Variable de estado para navegación
        if 'pagina_actual' not in st.session_state:
            st.session_state.pagina_actual = 0

        # --- COLUMNA IZQUIERDA: VISUALIZACIÓN (Imagen para compatibilidad móvil) ---
        with col_izq:
            st.subheader("📄 Documento")
            with st.spinner("Cargando vista previa..."):
                try:
                    # Convertimos la página actual a Imagen (funciona en todos los celulares)
                    # Usamos la página que esté en el slider o la actual
                    imagenes = convert_from_bytes(
                        archivo_bytes, 
                        first_page=st.session_state.pagina_actual + 1, 
                        last_page=st.session_state.pagina_actual + 1
                    )
                    if imagenes:
                        st.image(imagenes[0], caption=f"Página {st.session_state.pagina_actual + 1}", use_container_width=True)
                except Exception as e:
                    st.error("No se pudo generar la vista previa. Asegúrate de tener 'poppler-utils' en packages.txt")

        # --- COLUMNA DERECHA: CONTROLES ---
        with col_der:
            st.subheader("🎧 Controles")
            
            # >>> MODO 1: PÁGINA POR PÁGINA <<<
            if modo_lectura == "Página por página (Manual)":
                # Slider y Botones
                st.slider("Ir a página:", 0, total_paginas - 1, key="pagina_actual")
                
                c1, c2 = st.columns(2)
                if c1.button("⬅️ Anterior", use_container_width=True):
                    if st.session_state.pagina_actual > 0:
                        st.session_state.pagina_actual -= 1
                        st.rerun()
                if c2.button("Siguiente ➡️", use_container_width=True):
                    if st.session_state.pagina_actual < total_paginas - 1:
                        st.session_state.pagina_actual += 1
                        st.rerun()

                # Botón de Leer
                try:
                    texto = lector_pdf.pages[st.session_state.pagina_actual].extract_text()
                    if st.button("▶️ LEER ESTA PÁGINA", type="primary", use_container_width=True):
                        if texto and texto.strip():
                            with st.spinner("Generando audio..."):
                                audio = asyncio.run(generar_audio(texto, voz_elegida))
                                st.audio(audio, format='audio/mp3')
                        else:
                            st.warning("Página vacía o sin texto.")
                except:
                    st.error("Error al leer página.")

            # >>> MODO 2: LECTURA CONTINUA (LO QUE PEDISTE) <<<
            else:
                st.info("🎙️ Genera un audio largo de varias páginas.")
                
                c_inicio, c_fin = st.columns(2)
                inicio = c_inicio.number_input("Desde pág:", 1, total_paginas, 1)
                fin = c_fin.number_input("Hasta pág:", 1, total_paginas, min(5, total_paginas))

                if st.button("▶️ GENERAR AUDIO DE CORRIDO", type="primary", use_container_width=True):
                    if inicio > fin:
                        st.error("El inicio no puede ser mayor al final.")
                    else:
                        texto_completo = ""
                        barra = st.progress(0)
                        
                        with st.spinner(f"Procesando páginas {inicio} a {fin}..."):
                            rango = range(inicio - 1, fin)
                            for i, p in enumerate(rango):
                                try:
                                    txt = lector_pdf.pages[p].extract_text()
                                    if txt: 
                                        texto_completo += f"\n\n--- Página {p+1} ---\n\n{txt}"
                                except: pass
                                barra.progress((i + 1) / len(rango))
                        
                        if texto_completo.strip():
                            with st.spinner("Convirtiendo a voz humana (esto puede tardar unos segundos)..."):
                                audio_largo = asyncio.run(generar_audio(texto_completo, voz_elegida))
                                st.success("¡Audio listo! Dale play abajo.")
                                st.audio(audio_largo, format='audio/mp3')
                        else:
                            st.warning("No encontré texto en ese rango.")

    # ==============================
    # CASO IMAGEN
    # ==============================
    else:
        # En imagen, mostramos todo junto
        imagen = Image.open(archivo)
        st.image(imagen, use_container_width=True)
        if st.button("▶️ LEER IMAGEN", type="primary", use_container_width=True):
            with st.spinner("Leyendo..."):
                txt = pytesseract.image_to_string(imagen, lang='spa')
                if txt.strip():
                    audio = asyncio.run(generar_audio(txt, voz_elegida))
                    st.audio(audio, format='audio/mp3')

else:
    st.info("Sube un archivo para comenzar.")
