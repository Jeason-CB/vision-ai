# VISION AI — Plataforma inteligente de monitoreo visual

Versión integrada basada en **VISION_AI_PROFESIONAL_MONITOREO_VIDEO**, con la galería 2D del proyecto `VISION_AI_Web_v2_Galeria_Escenarios` y un centro persistente de alertas.

## Qué incluye

- Cámara web y archivos de video locales; selección de origen, inicio y detención.
- Captura periódica de fotogramas en el navegador y envío por WebSocket.
- Backend FastAPI con OpenCV, YOLO y ByteTrack.
- Modos de detección y segmentación YOLO (la disponibilidad de máscaras depende del modelo; la vista en vivo sigue priorizando cajas y tracking).
- Cajas delimitadoras, clase, confianza, latencia, contador de fotogramas e ID de seguimiento.
- Sesiones y eventos guardados en SQLite.
- **Alertas automáticas:** se crean a partir de entidades detectadas. Personas generan alerta de presencia; vehículos, alerta de circulación; otras clases, alerta de objeto detectado. Se aplica un intervalo de 30 segundos por entidad/track para evitar repetición excesiva.
- **Centro de alertas:** estados Pendiente, En atención, Resuelta y Descartada; las alertas atendidas permanecen en el historial. Exportación CSV.
- **Galería 2D:** almacén inteligente, planta industrial y control de calidad. Permite pausar/reanudar y generar alertas de demostración para probar el flujo completo.
- Grabación local WEBM desde el navegador y exportación CSV de eventos/sesiones/alertas.
- Configuración de URL API para producción mediante `VITE_API_URL`.

## Transparencia del sistema

La cámara y el motor YOLO del primer proyecto realizan procesamiento real si el backend está iniciado y los pesos del modelo se descargan correctamente. La galería 2D es una simulación gráfica: sus actores, objetos y alertas llevan identificación DEMO. Las reglas automáticas actuales son reglas iniciales por clase detectada, no una validación de EPP, intención, defectos industriales ni incumplimientos reales de zonas. Para esas capacidades se necesita un modelo especializado, zonas calibradas y datos etiquetados. La confianza de YOLO no es precisión medida. Precision, Recall, IoU y mAP requieren un conjunto de evaluación anotado.

## Requisitos locales

- Windows 10/11, macOS o Linux.
- Python 3.11 de 64 bits recomendado.
- Node.js 20 o superior y npm.
- Cámara web o archivo MP4/WEBM/MOV.
- Internet en el primer arranque para instalar dependencias y descargar pesos YOLO.
- 8 GB de RAM recomendados. CPU funciona, GPU compatible acelera el análisis.

## Ejecutar desde cero en Windows

### 1. Descomprimir

Extrae `VISION_AI_LOCAL` en una carpeta, por ejemplo `C:\Proyectos\VISION_AI_LOCAL`.

### 2. Backend

Abre PowerShell en la carpeta `backend` y ejecuta:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Si PowerShell bloquea la activación, ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a activar. Mantén esta terminal abierta. La API estará en `http://127.0.0.1:8000` y su documentación en `/docs`.

### 3. Frontend

Abre una segunda terminal en `frontend`:

```powershell
npm install
npm run dev
```

Abre `http://localhost:5173`. Mantén ambas terminales abiertas. En el navegador concede el permiso de cámara cuando lo solicite.

### 4. Probar los módulos

1. En **Monitoreo en vivo**, selecciona Cámara o Archivo.
2. Escoge Detección o Segmentación, ajusta la confianza e inicia.
3. Observa las cajas y los IDs de tracking.
4. En **Alertas e historial**, toma una alerta en atención, márcala atendida o descártala. Las alertas cerradas permanecen en la lista y en CSV.
5. En **Galería de escenarios**, cambia entre almacén, planta y calidad. Usa “Generar alerta de prueba” para comprobar el circuito sin cámara; esas alertas quedan marcadas como DEMO.
6. En **Eventos detectados** y **Sesiones**, consulta la trazabilidad.

## Estructura principal

```text
VISION_AI_LOCAL/
├── frontend/                 # React + Vite + TypeScript
│   ├── src/app/App.tsx        # Monitoreo, galería, alertas, eventos y sesiones
│   ├── src/style.css
│   ├── .env.example
│   └── vercel.json
├── backend/                  # FastAPI + OpenCV + YOLO + SQLite
│   ├── app/main.py
│   └── requirements.txt
├── render.yaml               # Blueprint de despliegue API
└── README.md
```

## API principal

- `GET /api/health`
- `POST /api/live/sessions`
- `WS /api/live/ws/{session_id}`
- `POST /api/live/sessions/{session_id}/stop`
- `GET /api/live/sessions`
- `GET /api/live/events` y `GET /api/live/events.csv`
- `GET /api/live/alerts`
- `POST /api/live/alerts/demo`
- `PATCH /api/live/alerts/{alert_id}`
- `GET /api/live/alerts.csv`

## Publicar en GitHub, Render y Vercel

### A. GitHub

1. Crea un repositorio nuevo en GitHub, por ejemplo `vision-ai`.
2. Abre una terminal en la carpeta `VISION_AI_LOCAL` (la raíz que contiene `frontend`, `backend` y `render.yaml`).
3. Ejecuta:

```bash
git init
git add .
git commit -m "Integrate VISION AI camera, scenarios and alerts"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/vision-ai.git
git push -u origin main
```

No subas `.venv`, `node_modules`, `.env`, la base SQLite ni archivos de pesos `.pt`; están excluidos en `.gitignore`.

### B. Render — publicar el backend

1. En Render selecciona **New + → Blueprint** y conecta el repositorio de GitHub.
2. Render detectará `render.yaml`. Revisa el servicio `vision-ai-api` y crea el despliegue.
3. En la configuración del servicio define `CORS_ORIGINS` con el dominio Vercel final, por ejemplo `https://vision-ai-tuusuario.vercel.app` (sin barra final). Para más de un dominio, sepáralos por coma.
4. El blueprint monta un disco persistente en `/var/data` y guarda SQLite en `/var/data/vision_ai.db`. El disco requiere un plan de Render que lo admita; no elimines el disco si deseas conservar alertas/sesiones.
5. Espera a que el servicio esté **Live**. Prueba `https://TU-API.onrender.com/api/health`.

**Nota de rendimiento:** Render ejecutará YOLO en CPU salvo que configures infraestructura compatible. El primer arranque puede tardar mientras se descargan pesos. Un servicio gratuito puede suspenderse y no es apropiado para monitoreo continuo; el WebSocket necesita un servicio activo y estable.

### C. Vercel — publicar el frontend

1. En Vercel selecciona **Add New → Project** e importa el mismo repositorio.
2. Configura **Root Directory** como `frontend`.
3. Framework: Vite. Build command: `npm run build`. Output directory: `dist`.
4. En **Environment Variables** agrega `VITE_API_URL` con la URL del backend Render, por ejemplo `https://vision-ai-api.onrender.com` (sin `/api`).
5. Despliega. Copia el dominio final de Vercel.
6. Regresa a Render y actualiza `CORS_ORIGINS` con ese dominio exacto. Guarda y vuelve a desplegar el backend.
7. Si cambias `VITE_API_URL`, vuelve a desplegar Vercel porque Vite incorpora esa variable durante el build.

### D. Verificación final

- Abre el dominio Vercel y revisa `/api/health` desde la URL Render.
- Prueba galería y alerta DEMO primero.
- Luego prueba cámara real y confirma que aparecen detecciones YOLO.
- Comprueba que el WebSocket conecta, que se guardan alertas y que los cambios de estado sobreviven a una recarga.
- Descarga el CSV de alertas.

## Variables de entorno

Frontend (`frontend/.env.local`, local o Environment Variables de Vercel):

```env
VITE_API_URL=http://127.0.0.1:8000
```

Backend (Render):

```env
CORS_ORIGINS=https://tu-dominio.vercel.app
VISION_DB_PATH=/var/data/vision_ai.db
```

## Limitaciones y próximos pasos

- La cámara web y los archivos de video son compatibles; RTSP/CCTV/NVR no está integrado.
- Las reglas de alerta actuales son genéricas por clase. Para EPP, intrusión en polígonos, permanencia en zona, congestión o defectos se requiere calibración y/o modelos específicos.
- La galería 2D no es un video real ni alimenta YOLO; es un entorno demostrativo independiente.
- No hay reconocimiento facial ni identificación biométrica.
- La grabación WEBM se descarga al dispositivo del operador; no se almacena automáticamente en Render.
- El almacenamiento persistente de SQLite en Render depende del disco contratado. Para una operación multiusuario/productiva conviene migrar a PostgreSQL y almacenamiento de objetos.
- Antes de uso real, añade autenticación, roles, auditoría de usuario, límites de carga y una política formal de retención de datos.
