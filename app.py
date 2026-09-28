"""
Lector Luigi | Estudio Pro — v8.0 (RESTAURADO Y MULTIPLATAFORMA)
Version estable. Compatible con PC local (Windows) y Cloud (Linux).
"""

import streamlit as st
import PyPDF2
import re
import io
import asyncio
import tempfile
import os
import unicodedata
import platform
from typing import Optional

try:
    import fitz
    TIENE_FITZ = True
except ImportError:
    TIENE_FITZ = False

try:
    import pytesseract
    from PIL import Image as PILImage
    
    # ── DETECCIÓN AUTOMÁTICA DE SISTEMA OPERATIVO (WINDOWS vs CLOUD LINUX) ──
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
    else:
        # Ruta estándar para el servidor Linux de Streamlit Cloud
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        
    TIENE_OCR = True
except ImportError:
    TIENE_OCR = False

import edge_tts

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lector Luigi | Estudio Pro",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS MÍNIMO — solo fondo y scrollbar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background-color: #0B1120; }
.block-container { padding-top: 2rem !important; max-width: 1360px !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #1E2D45 !important;
    border-radius: 14px !important;
}
.stProgress > div > div > div {
    background: linear-gradient(90deg, #1E40AF, #3B82F6) !important;
    border-radius: 999px !important;
}
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0B1120; }
::-webkit-scrollbar-thumb { background: #0B1120; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3B82F6; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for _k, _v in {
    "audio_actual":   None,
    "audio_label":    "",
    "pagina_vista":   0,
    "pdf_cargado_id": None,
    "total_paginas":  0,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO DE VOCES
# ─────────────────────────────────────────────────────────────────────────────
VOCES = [
    ("Sebastian — Venezuela",  "es-VE-SebastianNeural"),
    ("Dalia — Mexico",         "es-MX-DaliaNeural"),
    ("Alvaro — Espana",        "es-ES-AlvaroNeural"),
    ("Tomas — Argentina",      "es-AR-TomasNeural"),
    ("Jorge — Mexico",         "es-MX-JorgeNeural"),
    ("Elvira — Espana",        "es-ES-ElviraNeural"),
    ("Elena — Argentina",      "es-AR-ElenaNeural"),
    ("Gonzalo — Colombia",     "es-CO-GonzaloNeural"),
    ("Salome — Colombia",      "es-CO-SalomeNeural"),
    ("Camila — Peru",          "es-PE-CamilaNeural"),
    ("Alonso — EEUU",          "es-US-AlonsoNeural"),
]
VOCES_DICT = {lbl: vid for lbl, vid in VOCES}


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZACIÓN DE TEXTO
# ─────────────────────────────────────────────────────────────────────────────
def normalizar(raw: str) -> str:
    t = unicodedata.normalize("NFKC", raw)
    
    # ── LIMPIEZA DE HTML Y ARTEFACTOS OCR ──
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'(?i)</?p>|/p\b', ' ', t)
    t = re.sub(r'[\[\]\{\}]', ' ', t)
    
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", t)
    t = re.sub("[\uf000-\uffff]", "", t)
    t = re.sub(r"\(cid:\d+\)", "", t)
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    
    MARCA = "\u00b6"
    t = re.sub(r"\n{2,}", MARCA, t)
    mayus = "ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c1\u00c9\u00cd\u00d3\u00da\u00dc\u00d1"
    t = re.compile("([.?!])\n([" + re.escape(mayus) + "])").sub(r"\1" + MARCA + r"\2", t)
    t = re.sub(r"\n", " ", t)
    t = t.replace(MARCA, "\n\n")
    t = re.sub(r"([.?!,;:])([^\s\n])", r"\1 \2", t)
    t = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", t)
    
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES CACHEADAS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, max_entries=3)
def indexar_pdf(pdf_bytes: bytes):
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    total  = len(reader.pages)
    return total, []


@st.cache_data(show_spinner=False, max_entries=12)
def renderizar_pagina(pdf_bytes: bytes, pag_0: int) -> Optional[bytes]:
    if not TIENE_FITZ:
        return None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if pag_0 < len(doc):
            pagina_pdf = doc.load_page(pag_0)
            pix = pagina_pdf.get_pixmap(dpi=150)
            return pix.tobytes("png")
    except Exception:
        pass
    return None


@st.cache_data(show_spinner=False, max_entries=12)
def ocr_pagina(pdf_bytes: bytes, pag_0: int) -> str:
    if not (TIENE_FITZ and TIENE_OCR):
        return ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if pag_0 < len(doc):
            pagina_pdf = doc.load_page(pag_0)
            pix = pagina_pdf.get_pixmap(dpi=150)
            img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return pytesseract.image_to_string(img, lang="spa") or ""
    except Exception:
        pass
    return ""


def ocr_pagina_diagnostico(pdf_bytes: bytes, pag_0: int):
    if not TIENE_FITZ:
        return "", "PyMuPDF no está instalado.\nEjecuta: pip install PyMuPDF"
    if not TIENE_OCR:
        return "", "pytesseract no está instalado."
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if pag_0 >= len(doc):
            return "", "La página solicitada no existe en el documento."
        pagina_pdf = doc.load_page(pag_0)
        pix = pagina_pdf.get_pixmap(dpi=150)
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
    except Exception as ex:
        return "", f"Error al renderizar PDF — {type(ex).__name__}: {ex}"

    try:
        texto = pytesseract.image_to_string(img, lang="spa") or ""
        return texto, None
    except pytesseract.TesseractNotFoundError:
        return "", "Tesseract no está instalado o no se encuentra en el PATH del sistema."
    except Exception as ex:
        return "", f"Error en OCR — {type(ex).__name__}: {ex}"


def obtener_texto(pdf_bytes, idx, textos_cache):
    ocr_raw = ocr_pagina(pdf_bytes, idx)
    return normalizar(ocr_raw), bool(ocr_raw.strip())


# ─────────────────────────────────────────────────────────────────────────────
# SÍNTESIS DE VOZ
# ─────────────────────────────────────────────────────────────────────────────
async def _tts(texto: str, voz: str, tasa: str, pitch: str) -> Optional[bytes]:
    if not texto.strip():
        return None
    try:
        texto_limpio = texto.strip()
        com = edge_tts.Communicate(texto_limpio, voice=voz, rate=tasa, pitch=pitch)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            ruta = fp.name
        await com.save(ruta)
        with open(ruta, "rb") as f:
            data = f.read()
        os.unlink(ruta)
        return data
    except Exception as ex:
        st.error(f"Error TTS: {ex}")
        return None


def generar_audio(texto, voz, tasa, pitch) -> Optional[bytes]:
    return asyncio.run(_tts(texto, voz, tasa, pitch))


# ═════════════════════════════════════════════════════════════════════════════
#  INTERFAZ
# ═════════════════════════════════════════════════════════════════════════════

st.title("📖 Lector Luigi · Estudio Pro")
st.caption("Síntesis de voz neural · OCR automático · v8.0")
st.divider()

with st.expander("🎙️  Configuración de Voz y Prosodia", expanded=True):
    c1, c2, c3 = st.columns([1.4, 1, 1], gap="medium")

    with c1:
        st.markdown("**Narrador**")
        voz_label = st.selectbox("Voz", [v[0] for v in VOCES], label_visibility="collapsed")
        voz_id   = VOCES_DICT[voz_label]
        narrador = voz_label.split(" — ")[0]

    with c2:
        st.markdown("**Velocidad de Lectura**")
        velocidad = st.slider("Velocidad", -50, 50, -8, 1, format="%d%%", label_visibility="collapsed")
        tasa_str = f"{velocidad:+d}%"
        st.caption(f"**{tasa_str}** — " + ("Natural ✓" if -20 <= velocidad <= 5 else ("Muy lenta" if velocidad < -20 else "Rápida")))

    with c3:
        st.markdown("**Tono (Pitch)**")
        pitch_val = st.slider("Pitch", -20, 20, 0, 1, format="%d Hz", label_visibility="collapsed")
        pitch_str = f"{pitch_val:+d}Hz"
        st.caption(f"**{pitch_str}** — " + ("Original" if pitch_val == 0 else ("Grave ▼" if pitch_val < 0 else "Agudo ▲")))

st.write("")

with st.container(border=True):
    archivo = st.file_uploader("Sube tu PDF o imagen de trabajo", type=["pdf", "png", "jpg", "jpeg"])

st.write("")

if archivo is None:
    with st.container(border=True):
        st.write("")
        _, centro, _ = st.columns([1, 2, 1])
        with centro:
            st.markdown("## 📂")
            st.markdown("#### Sube un documento para comenzar")
            st.caption("PDF o imagen · El audio persiste mientras navegas las páginas")
        st.write("")
    st.stop()

archivo_bytes = archivo.read()
file_id        = hash(archivo_bytes)
tam_mb        = round(len(archivo_bytes) / 1_048_576, 1)

if st.session_state.pdf_cargado_id != file_id:
    st.session_state.pdf_cargado_id = file_id
    st.session_state.pagina_vista   = 0
    st.session_state.audio_actual   = None
    st.session_state.audio_label    = ""
    st.session_state.total_paginas  = 0


if "pdf" in archivo.type:
    with st.spinner("Indexando documento…"):
        total, textos = indexar_pdf(archivo_bytes)

    st.session_state.total_paginas = total
    pag = min(st.session_state.pagina_vista, total - 1)
    st.session_state.pagina_vista  = pag

    if tam_mb > 15 or total > 80:
        st.warning(f"⚠️ Archivo grande ({tam_mb} MB · {total} páginas). Genera el audio en bloques de ≤ 10 páginas.")
        st.write("")

    col_visor, col_audio = st.columns([1.1, 1.0], gap="large")

    with col_visor:
        with st.container(border=True):
            st.markdown("### 👁 Visor del Documento")
            nav1, nav2, nav3 = st.columns([1, 2, 1])
            with nav1:
                if st.button("← Anterior", key="ant", use_container_width=True, disabled=(pag == 0)):
                    st.session_state.pagina_vista = pag - 1
                    st.rerun()
            with nav2:
                st.markdown(f"<div style='text-align:center;font-weight:700;font-size:0.9rem;color:#60A5FA;padding:6px 0;border:1.5px solid #1E2D45;border-radius:999px;background:#0F172A'>Página {pag + 1} de {total}</div>", unsafe_allow_html=True)
            with nav3:
                if st.button("Siguiente →", key="sig", use_container_width=True, disabled=(pag >= total - 1)):
                    st.session_state.pagina_vista = pag + 1
                    st.rerun()

            st.write("")
            txt_pag, uso_ocr = obtener_texto(archivo_bytes, pag, textos)
            if uso_ocr:
                st.caption("🔍 OCR aplicado automáticamente en esta página")

            img = renderizar_pagina(archivo_bytes, pag)
            if img:
                st.image(img, use_container_width=True)
            else:
                st.markdown(f"<div style='font-size:0.85rem;color:#94A3B8;line-height:1.75;white-space:pre-wrap;max-height:560px;overflow-y:auto;padding:0.5rem 0'>{txt_pag or 'Sin contenido extraíble en esta página.'}</div>", unsafe_allow_html=True)

    with col_audio:
        with st.container(border=True):
            st.markdown("### 📻 Reproductor")
            if st.session_state.audio_actual:
                st.success(f"▶  {st.session_state.audio_label}")
                st.audio(st.session_state.audio_actual, format="audio/mp3")
            else:
                st.write("")
                _, mc, _ = st.columns([1, 3, 1])
                with mc:
                    st.markdown("**🎵  Sin audio generado**")
                    st.caption("Configura el rango y pulsa Generar")
                st.write("")

        st.write("")

        with st.container(border=True):
            st.markdown("### ⚙️ Generar Audio")
            g1, g2 = st.columns(2)
            desde = g1.number_input("Desde página", 1, total, value=pag + 1, key="desde")
            hasta = g2.number_input("Hasta página", 1, total, value=min(pag + 10, total), key="hasta")

            if hasta - desde + 1 > 10:
                st.warning("Rango mayor a 10 páginas puede tardar varios minutos.")

            st.write("")
            st.caption(f"Voz: **{narrador}**  ·  Velocidad: **{tasa_str}**  ·  Tono: **{pitch_str}**")

            btn_gen = st.button("🎙️  Generar Audio", type="primary", use_container_width=True, key="btn_gen")

        st.write("")

        with st.expander("📊 Estadísticas del documento"):
            col_s1, col_s2 = st.columns(2)
            col_s1.metric("Páginas", total)
            col_s2.metric("Tamaño", f"{tam_mb} MB")
            st.caption("Modo 100% OCR activo.")

    if btn_gen:
        if desde > hasta:
            st.error("La página inicial no puede superar a la final.")
        else:
            acum, con_ocr, errores_ocr = "", [], []
            rango  = list(range(desde - 1, hasta))
            prog   = st.progress(0)
            estado = st.empty()

            estado.info("🔍 Verificando estado del motor OCR…")
            _, error_previo = ocr_pagina_diagnostico(archivo_bytes, rango[0])
            if error_previo:
                prog.empty()
                estado.empty()
                st.error(f"**❌ El OCR no está disponible:**\n\n{error_previo}")
                st.stop()

            for i, p in enumerate(rango):
                estado.info(f"⏳ Extrayendo página {p + 1} de {hasta} (OCR)…")
                texto_ocr, error_ocr = ocr_pagina_diagnostico(archivo_bytes, p)
                if error_ocr:
                    errores_ocr.append((p + 1, error_ocr))
                elif texto_ocr.strip():
                    texto_ocr = re.sub(r'([^\.\!\?])\n([^\n])', r'\1 \2', texto_ocr)
                    acum += normalizar(texto_ocr) + "\n\n"
                    con_ocr.append(p + 1)
                prog.progress((i + 1) / len(rango))

            prog.empty()
            estado.empty()

            if errores_ocr:
                pags_err = [str(pn) for pn, _ in errores_ocr]
                _, primer_err = errores_ocr[0]
                st.error(f"**❌ OCR falló en {len(errores_ocr)} página(s): {', '.join(pags_err)}**\n\n{primer_err}")

            if acum.strip():
                with st.spinner("🎙️ Sintetizando voz…"):
                    audio = generar_audio(acum, voz_id, tasa_str, pitch_str)
                if audio:
                    st.session_state.audio_actual = audio
                    st.session_state.audio_label  = f"Págs {desde}–{hasta} · {narrador} (100% OCR)"
                    st.rerun()
            elif not errores_ocr:
                st.warning("No se detectó texto legible por OCR en ese rango.")
else:
    col_i, col_a = st.columns([1, 1], gap="large")

    with col_i:
        with st.container(border=True):
            st.markdown("### 🖼 Imagen")
            if TIENE_OCR:
                st.image(PILImage.open(io.BytesIO(archivo_bytes)), use_container_width=True)
            else:
                st.image(archivo_bytes, use_container_width=True)

    with col_a:
        with st.container(border=True):
            st.markdown("### 📻 Reproductor")
            if st.session_state.audio_actual:
                st.success(f"▶  {st.session_state.audio_label}")
                st.audio(st.session_state.audio_actual, format="audio/mp3")
            else:
                st.write("")
                st.markdown("**🎵  Sin audio generado**")
                st.caption("Pulsa el botón de abajo para leer la imagen")
                st.write("")

        st.write("")

        with st.container(border=True):
            st.markdown("### 🎙️ Leer Imagen")
            if TIENE_OCR:
                if st.button("🎙️  Leer imagen con OCR", type="primary", use_container_width=True, key="btn_img"):
                    with st.spinner("Extrayendo texto…"):
                        try:
                            raw_img   = pytesseract.image_to_string(PILImage.open(io.BytesIO(archivo_bytes)), lang="spa")
                            texto_img = normalizar(raw_img)
                        except Exception as ex:
                            st.error(f"Error OCR: {ex}")
                            texto_img = ""
                    if texto_img:
                        with st.spinner("🎙️ Sintetizando…"):
                            audio = generar_audio(texto_img, voz_id, tasa_str, pitch_str)
                        if audio:
                            st.session_state.audio_actual = audio
                            st.session_state.audio_label  = f"Imagen · {narrador}"
                            st.rerun()
                    else:
                        st.warning("No se detectó texto legible en la imagen.")
            else:
                st.warning("Instala `pytesseract` para habilitar esta función.")
