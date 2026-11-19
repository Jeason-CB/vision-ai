# VISION AI — Arquitectura actualizada

## Propósito
Plataforma local para monitoreo visual basado en transmisiones de video. La interfaz ya no depende de la carga de imágenes como flujo principal.

## Flujo de datos
Fuente (cámara web o video) → captura de fotogramas → WebSocket → OpenCV → YOLO → ByteTrack → overlay y lista de detecciones → registro de eventos/sesiones SQLite.

## Componentes
- React + TypeScript + Vite: interfaz de monitoreo.
- MediaDevices / MediaRecorder: acceso a cámara y grabación descargable en WEBM.
- FastAPI: API REST y WebSocket.
- OpenCV: decodificación de fotogramas.
- Ultralytics YOLO: inferencia real.
- ByteTrack: seguimiento multiobjeto.
- SQLite: trazabilidad de sesiones y eventos.

## Persistencia
Cada sesión registra fecha de inicio/fin, fuente, fotogramas procesados y detecciones acumuladas. Los eventos guardan fecha UTC, fuente, clase, confianza, track ID y bounding box.

## Alcance
Fuentes implementadas: cámara web local y archivo de video compatible con el navegador. La integración RTSP/NVR queda como extensión pendiente y se declara expresamente en README para no confundir una fuente compatible con una integración aún no implementada.
