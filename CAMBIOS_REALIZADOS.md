# VISION AI — archivos corregidos

## Archivos modificados

- `frontend/src/app/App.tsx`: vista previa de cámara/archivo separada de la conexión IA; espera reproducción y carga de fotogramas; valida HTTPS, permisos, archivo, sesión HTTP y WebSocket; controla backpressure al enviar fotogramas; mejora mensajes de error; valida respuestas de creación/actualización de alertas; anima los objetos de la galería mediante clases.
- `frontend/src/style.css`: recorridos continuos para trabajadores y objetos, barrido visual y animación de aparición de alertas. Pausar quita la clase de movimiento.
- `backend/app/main.py`: inicializa datos DEMO hasta completar 10 alertas, 10 eventos y 10 sesiones cuando falten; los registros quedan identificados como DEMO.
- `frontend/package.json`: agrega `@types/react` y `@types/react-dom`, necesarios para compilar TSX con TypeScript.
- `render.yaml`: cambia a instancia `free` y base SQLite temporal en `/tmp`; no configura disco de pago.
- `.gitignore`: excluye archivos temporales, bases SQLite, pesos YOLO y dependencias.

## Rutas exactas

```text
VISION_AI_LOCAL/
├── frontend/
│   ├── package.json
│   └── src/
│       ├── app/App.tsx
│       └── style.css
├── backend/
│   ├── requirements.txt
│   └── app/main.py
├── render.yaml
└── .gitignore
```

## Cámara y video

La cámara requiere HTTPS (Vercel lo proporciona) o localhost y permiso concedido en el navegador. Para video, el usuario elige un archivo local; el navegador lo reproduce y captura fotogramas para enviarlos al WebSocket. El archivo entero no se carga a Render. Prueba primero MP4 H.264 o WEBM en Chrome/Edge.

## Alertas e historial

El backend crea alertas automáticas al detectar clases en el flujo YOLO y permite crear alertas DEMO desde la galería. Los registros iniciales son demostrativos. Al usar una base nueva, se insertan registros hasta alcanzar al menos 10 filas por cada sección (alertas, eventos y sesiones). No son evidencia de detección real.

## Importante para Render Free

El plan gratuito no tiene disco persistente; `/tmp/vision_ai.db` puede borrarse al reiniciar/suspender/redeploy. YOLO puede superar los 512 MB de RAM del plan gratuito. Este paquete mejora el frontend y los endpoints, pero no puede garantizar inferencia real en Render Free: comprueba los logs y `/api/health`. Para conservar registros se necesita almacenamiento persistente o una base de datos externa; para inferencia estable, un servicio con más memoria.

## Después de reemplazar los archivos

1. Reemplaza la carpeta del proyecto por esta versión.
2. En `frontend`, ejecuta `npm install` y luego `npm run build`.
3. Envía los cambios a GitHub (`git add .`, `git commit -m "Fix VISION AI camera scenarios alerts"`, `git push`).
4. Vercel vuelve a desplegar el frontend; Render vuelve a desplegar el backend.
5. En Vercel define `VITE_API_URL` con la URL de Render (sin `/api`).
6. En Render define `CORS_ORIGINS` con el dominio exacto de Vercel.
