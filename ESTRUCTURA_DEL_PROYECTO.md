# Estructura de VISION AI

- `frontend/src/app/App.tsx`: aplicación de monitoreo, selección de fuente, reproducción, overlay, controles y vistas de eventos/sesiones.
- `frontend/src/style.css`: sistema visual empresarial responsive.
- `backend/app/main.py`: API REST, WebSocket de fotogramas, inferencia YOLO, tracking ByteTrack y persistencia SQLite.
- `backend/app/services/`: espacio para separar servicios de aplicación en futuras iteraciones.
- `backend/vision_ai.db`: base SQLite creada automáticamente al iniciar.
- `INICIAR_WINDOWS.bat`: instalación e inicio local.
- `README.md`: instalación, operación, arquitectura, API y limitaciones.

## Capas lógicas

1. Presentación: React + TypeScript.
2. Captura: MediaDevices / HTMLVideoElement / Canvas.
3. Transporte: WebSocket local.
4. Servicio IA: FastAPI + OpenCV + Ultralytics YOLO + ByteTrack.
5. Persistencia: SQLite.
6. Exportación: CSV.
