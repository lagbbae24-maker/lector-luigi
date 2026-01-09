import streamlit as st
import PyPDF2
from PIL import Image
import pytesseract
import edge_tts
import asyncio
import tempfile
import base64

# Configuración de página ancha para ver mejor el PDF
st.set_page_config(page_title="Lector Luigi Pro", page_icon="🧠", layout="wide")

st.title("🧠 Lector Luigi: Vista Profesional")

# --- BARRA LATERAL ---
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
    modo_lectura = st.radio(
        "Modo de Lectura",
        ["Página por página", "Lectura Continua"],
        index=0
    )
    
    st.info("ℹ️ Nota: El resaltado 'Karaoke' no es posible en esta versión web, pero aquí puedes ver el documento original para seguir la lectura.")

# --- FUNCIONES ---

# Función para mostrar el PDF visualmente
def mostrar_pdf_visual(file_obj):
    base64_pdf = base64.b64encode(file_obj.read()).decode('utf-8')
    # Volvemos el puntero al inicio para que PyPDF2 lo pueda leer después
    file_obj.seek(0) 
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

async def generar_audio(texto, voz):
    if not texto.strip():
        return None
    comunicador = edge_tts.Communicate(texto, voz)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        await comunicador.save(fp.name)
        return fp.name

# --- INTERFAZ PRINCIPAL (Columnas) ---

col_izq, col_der = st.columns([1, 1]) # Mitad y Mitad

# Cargador de Archivo (Arriba de las columnas)
archivo = st.file_uploader("📂 Sube PDF o Imagen", type=["pdf", "png", "jpg", "jpeg"])

if archivo is not None:
    tipo_archivo = archivo.type
    
    # --- COLUMNA IZQUIERDA: EL DOCUMENTO VISUAL ---
    with col_izq:
        st.subheader("📄 Tu Documento")
        if "pdf" in tipo_archivo:
            mostrar_pdf_visual(archivo)
        else:
            imagen = Image.open(archivo)
            st.image(imagen, use_container_width=True)

    # --- COLUMNA DERECHA: EL AUDIO Y TEXTO ---
    with col_der:
        st.subheader("🎧 Reproductor")
        
        # ==============================
        # CASO PDF - LÓGICA DE AUDIO
        # ==============================
        if "pdf" in tipo_archivo:
            lector_pdf = PyPDF2.PdfReader(archivo)
            total_paginas = len(lector_pdf.pages)
            
            # --- MODO 1: PÁGINA POR PÁGINA ---
            if modo_lectura == "Página por página":
                if 'pagina_actual' not in st.session_state:
                    st.session_state.pagina_actual = 0
                
                # Slider de navegación
                st.slider("Selecciona Página:", 0, total_paginas - 1, key="pagina_actual")
                
                # Botones de navegación rápida
                c1, c2 = st.columns(2)
                if c1.button("⬅️ Anterior"):
                    if st.session_state.pagina_actual > 0:
                        st.session_state.pagina_actual -= 1
                        st.rerun()
                if c2.button("Siguiente ➡️"):
                    if st.session_state.pagina_actual < total_paginas - 1:
                        st.session_state.pagina_actual += 1
                        st.rerun()

                # Proceso de lectura
                try:
                    pagina = lector_pdf.pages[st.session_state.pagina_actual]
                    texto_a_leer = pagina.extract_text()
                    
                    st.success(f"Página {st.session_state.pagina_actual + 1} lista.")
                    
                    with st.expander("Ver texto extraído"):
                        st.write(texto_a_leer)
                    
                    if st.button("▶️ ESCUCHAR PÁGINA", type="primary", use_container_width=True):
                        with st.spinner("Generando audio..."):
                            audio_path = asyncio.run(generar_audio(texto_a_leer, voz_elegida))
                            if audio_path:
                                st.audio(audio_path, format='audio/mp3')
                except Exception as e:
                    st.error("Error al leer página.")

            # --- MODO 2: LECTURA CONTINUA ---
            else:
                st.markdown("### 🎙️ Lectura de Rango")
                c1, c2 = st.columns(2)
                inicio = c1.number_input("Desde pág:", 1, total_paginas, 1)
                fin = c2.number_input("Hasta pág:", 1, total_paginas, min(5, total_paginas))
                
                if st.button("▶️ REPRODUCIR TODO EL RANGO", type="primary", use_container_width=True):
                    texto_completo = ""
                    progreso = st.progress(0)
                    with st.spinner(f"Procesando de pág {inicio} a {fin}..."):
                        rango = range(inicio - 1, fin)
                        for i, p in enumerate(rango):
                            try:
                                txt = lector_pdf.pages[p].extract_text()
                                if txt: texto_completo += f" ... Página {p+1} ... {txt}"
                            except: pass
                            progreso.progress((i + 1) / len(rango))
                    
                    if texto_completo:
                        audio_path = asyncio.run(generar_audio(texto_completo, voz_elegida))
                        st.audio(audio_path, format='audio/mp3')
                        st.success("¡Reproduciendo!")

        # ==============================
        # CASO IMAGEN
        # ==============================
        else:
            # Para imagen, la imagen ya se ve a la izquierda
            if st.button("▶️ LEER IMAGEN", type="primary"):
                with st.spinner("Analizando imagen..."):
                    texto = pytesseract.image_to_string(Image.open(archivo), lang='spa')
                    if texto.strip():
                        audio_path = asyncio.run(generar_audio(texto, voz_elegida))
                        st.audio(audio_path, format='audio/mp3')
                    else:
                        st.error("No encontré texto.")

else:
    st.info("Sube tu archivo para ver la magia.")
