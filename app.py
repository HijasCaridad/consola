import streamlit as st
import importlib
import pkgutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import os
import io
import zipfile

# ===========================
# 🔐 CONFIGURACIÓN
# ===========================
st.set_page_config(page_title="Panel de Procesos", page_icon="⚙️", layout="centered")

PASSWORD = os.getenv("APP_PASS", "1234segura")  # Clave general configurable
LOG_PATH = Path("logs/registros.csv")
OUTPUT_PATH = Path("outputs")

LOG_PATH.parent.mkdir(exist_ok=True, parents=True)
OUTPUT_PATH.mkdir(exist_ok=True, parents=True)

# ===========================
# 🧩 CARGAR MÓDULOS DE PROCESOS
# ===========================
def cargar_procesos():
    procesos = {}
    for _, module_name, _ in pkgutil.iter_modules(["procesos"]):
        module = importlib.import_module(f"procesos.{module_name}")
        if hasattr(module, "run") and hasattr(module, "descripcion"):
            procesos[module_name] = module
    return procesos

PROCESOS = cargar_procesos()

# ===========================
# 🔒 LOGIN SIMPLE
# ===========================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Acceso restringido")
    clave = st.text_input("Introduce la clave de acceso:", type="password")
    if st.button("Entrar"):
        if clave == PASSWORD:
            st.session_state.auth = True
            st.success("✅ Acceso concedido")
            st.rerun()
        else:
            st.error("❌ Clave incorrecta")
    st.stop()

# ===========================
# 🧭 INTERFAZ PRINCIPAL
# ===========================
st.sidebar.title("⚙️ Panel de Procesos")
menu = ["📊 Ver registros"] + [f"🚀 {k}" for k in PROCESOS.keys()]
opcion = st.sidebar.radio("Selecciona una opción:", menu)

usuario = st.text_input("👤 Usuario:", placeholder="Tu nombre o iniciales")

def registrar_uso(usuario, proceso, archivo, resultado):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo = pd.DataFrame([[now, usuario, proceso, archivo, resultado]],
                         columns=["Fecha", "Usuario", "Proceso", "Archivo", "Resultado"])
    if LOG_PATH.exists():
        df = pd.read_csv(LOG_PATH)
        df = pd.concat([df, nuevo], ignore_index=True)
    else:
        df = nuevo
    df.to_csv(LOG_PATH, index=False)

# ===========================
# 📊 VER REGISTROS
# ===========================
if opcion == "📊 Ver registros":
    st.header("📊 Registro de uso")
    if LOG_PATH.exists():
        df = pd.read_csv(LOG_PATH)
        st.dataframe(df)
        if st.button("🧹 Limpiar registros"):
            LOG_PATH.unlink()
            st.success("Registros eliminados.")
    else:
        st.info("No hay registros aún.")
    st.stop()

# ===========================
# ⚙️ EJECUTAR PROCESO SELECCIONADO
# ===========================
proceso_key = opcion.replace("🚀 ", "")
mod = PROCESOS.get(proceso_key)

if not mod:
    st.error("No se encontró el proceso seleccionado.")
    st.stop()

st.header(f"🚀 {proceso_key}")
st.write(mod.descripcion())

archivo = st.file_uploader("Sube un archivo PDF para procesar:", type=["pdf"])

if archivo and usuario:
    pdf_path = Path(archivo.name)
    with open(pdf_path, "wb") as f:
        f.write(archivo.getbuffer())
    out_folder = OUTPUT_PATH / proceso_key
    out_folder.mkdir(exist_ok=True, parents=True)

    with st.spinner("Procesando..."):
        try:
            result = mod.run(pdf_path, out_folder)
            st.success("✅ Proceso completado correctamente.")

            # Mostrar resultados resumidos
            for k, v in result.items():
                st.write(f"**{k}:** {v}")

            # ==============================
            # 📦 CREAR ARCHIVO ZIP DE RESULTADOS
            # ==============================
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                # CSV
                csv_path = out_folder / "comprobantes_refinado" / "operaciones.csv"
                if csv_path.exists():
                    zipf.write(csv_path, arcname=csv_path.name)
                # PDFs
                pdfs_folder = out_folder / "comprobantes_refinado" / "pdfs"
                if pdfs_folder.exists():
                    for pdf in pdfs_folder.glob("*.pdf"):
                        zipf.write(pdf, arcname=f"pdfs/{pdf.name}")

            zip_buffer.seek(0)
            nombre_zip = f"resultados_{proceso_key}.zip"

            st.download_button(
                label="📦 Descargar resultados (.zip)",
                data=zip_buffer,
                file_name=nombre_zip,
                mime="application/zip",
            )

            # Registrar ejecución
            registrar_uso(usuario, proceso_key, archivo.name, "Éxito")

        except Exception as e:
            st.error(f"⚠️ Error: {e}")
            registrar_uso(usuario, proceso_key, archivo.name, f"Error: {e}")

else:
    st.info("🔸 Introduce tu nombre y selecciona un archivo PDF para comenzar.")
