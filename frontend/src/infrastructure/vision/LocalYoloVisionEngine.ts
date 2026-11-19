/**
 * Adaptador de infraestructura: el backend FastAPI ejecuta Ultralytics YOLO.
 * Sustituible por otro proveedor sin acoplarlo a los módulos de presentación.
 */
export const LOCAL_VISION_API = 'http://127.0.0.1:8000/api';
