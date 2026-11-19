
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import io, json, time, uuid, sqlite3, csv, os
from datetime import datetime, timezone, timedelta
from typing import Optional

from ultralytics import YOLO

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("VISION_DB_PATH", str(APP_DIR.parent / "vision_ai.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 15 * 1024 * 1024
MODELS = {"detection": "yolov8n.pt", "segmentation": "yolov8n-seg.pt"}
_loaded = {}

app = FastAPI(title="VISION AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, filename TEXT NOT NULL,
            mode TEXT NOT NULL, model TEXT NOT NULL, duration_ms REAL NOT NULL,
            image_width INTEGER NOT NULL, image_height INTEGER NOT NULL,
            detection_count INTEGER NOT NULL, average_confidence REAL NOT NULL,
            results_json TEXT NOT NULL
        )""")

@app.on_event("startup")
def startup():
    init_db()

def get_model(mode):
    name = MODELS[mode]
    if name not in _loaded:
        _loaded[name] = YOLO(name)
    return _loaded[name]

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "VISION AI", "database": str(DB_PATH)}

@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    mode: str = Form("detection"),
    confidence_threshold: float = Form(0.25),
    reference_height_cm: Optional[float] = Form(None),
    reference_height_px: Optional[float] = Form(None)
):
    if mode not in MODELS:
        raise HTTPException(400, "Modo no válido.")
    if not 0.01 <= confidence_threshold <= 0.99:
        raise HTTPException(400, "El umbral debe estar entre 0.01 y 0.99.")
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "Formato no compatible. Usa JPG, PNG o WEBP.")
    raw = await image.read()
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(413, "La imagen está vacía o supera 15 MB.")
    try:
        pil = Image.open(io.BytesIO(raw)).convert("RGB")
        pil.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "No se pudo leer la imagen. Puede estar dañada.")
    width, height = pil.size
    start = time.perf_counter()
    try:
        model = get_model(mode)
        prediction = model.predict(source=pil, conf=confidence_threshold, verbose=False)[0]
    except Exception as e:
        raise HTTPException(500, f"Falló el motor de visión: {str(e)[:250]}")
    duration_ms = (time.perf_counter() - start) * 1000
    detections = []
    names = prediction.names
    boxes = prediction.boxes
    if boxes is not None:
        for idx, box in enumerate(boxes):
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)
            bw, bh = max(0, x2-x1), max(0, y2-y1)
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            item = {
                "id": idx + 1, "class_id": cls_id, "label": names.get(cls_id, str(cls_id)),
                "confidence": round(conf, 4),
                "box": {"x": round(x1, 2), "y": round(y1, 2), "width": round(bw, 2), "height": round(bh, 2)},
                "center": {"x": round((x1+x2)/2, 2), "y": round((y1+y2)/2, 2)},
                "area_px2": round(bw*bh, 2),
                "aspect_ratio": round(bw/bh, 3) if bh else None,
                "height_cm_estimate": round((bh/reference_height_px)*reference_height_cm, 2)
                    if reference_height_cm and reference_height_px and reference_height_cm > 0 and reference_height_px > 0 else None
            }
            if mode == "segmentation" and prediction.masks is not None and idx < len(prediction.masks.data):
                import numpy as np
                mask = prediction.masks.data[idx].cpu().numpy()
                item["mask"] = {
                    "width": int(mask.shape[1]), "height": int(mask.shape[0]),
                    "data": (mask > 0.5).astype("uint8").flatten().tolist()
                }
            detections.append(item)
    avg_conf = sum(d["confidence"] for d in detections)/len(detections) if detections else 0
    class_counts = {}
    for d in detections:
        class_counts[d["label"]] = class_counts.get(d["label"], 0) + 1
    result = {
        "id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat(),
        "filename": Path(image.filename or "imagen").name, "mode": mode,
        "model": MODELS[mode], "duration_ms": round(duration_ms, 2),
        "image": {"width": width, "height": height},
        "detection_count": len(detections), "average_confidence": round(avg_conf, 4),
        "class_counts": class_counts, "detections": detections,
        "evaluation": {
            "precision": None, "recall": None, "iou": None, "map": None,
            "note": "Precision, Recall, IoU y mAP requieren anotaciones de referencia y un dataset etiquetado."
        }
    }
    with db() as con:
        con.execute("""INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
            result["id"], result["created_at"], result["filename"], mode, MODELS[mode],
            result["duration_ms"], width, height, len(detections), avg_conf, json.dumps(result)
        ))
    return result

@app.get("/api/history")
def history(limit: int = 100):
    limit = max(1, min(limit, 500))
    with db() as con:
        rows = con.execute("""SELECT id,created_at,filename,mode,model,duration_ms,image_width,image_height,
        detection_count,average_confidence FROM analyses ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/history/{analysis_id}")
def history_detail(analysis_id: str):
    with db() as con:
        row = con.execute("SELECT results_json FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Análisis no encontrado.")
    return json.loads(row["results_json"])

@app.get("/api/export.csv")
def export_csv():
    with db() as con:
        rows = con.execute("SELECT id,created_at,filename,mode,model,duration_ms,image_width,image_height,detection_count,average_confidence FROM analyses ORDER BY created_at DESC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","fecha","archivo","modo","modelo","latencia_ms","ancho_px","alto_px","objetos","confianza_media"])
    for row in rows:
        writer.writerow(list(row))
    data = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(io.BytesIO(data), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=vision_ai_historial.csv"})

# --- MONITOREO EN TIEMPO REAL: WebSocket de fotogramas ---
import base64
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
import cv2
import numpy as np

@app.on_event("startup")
def init_live_tables():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS live_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            created_at TEXT NOT NULL, source TEXT NOT NULL, track_id INTEGER,
            label TEXT NOT NULL, confidence REAL NOT NULL, box_json TEXT NOT NULL,
            snapshot_path TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS live_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            source TEXT NOT NULL, session_id TEXT, track_id INTEGER, label TEXT NOT NULL, confidence REAL NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS live_sessions (
            id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT,
            source TEXT NOT NULL, frames INTEGER DEFAULT 0, detections INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active')""")
        # Datos iniciales DEMO: completar hasta 10 registros por vista, una sola vez.
        # Están etiquetados explícitamente como DEMO y NO son detecciones reales.
        now = datetime.now(timezone.utc)
        labels = ["persona", "pallet", "carretilla", "caja", "casco", "persona", "vehículo", "pieza", "pallet", "persona"]
        demo_sources = ["Cámara almacén · DEMO", "Video planta · DEMO", "Escenario calidad · DEMO"]
        demo_sessions = []
        for i in range(10):
            sid = f"demo-session-{i+1:02d}"
            started = (now - timedelta(hours=i+1)).isoformat()
            ended = (now - timedelta(hours=i+1) + timedelta(minutes=8+i)).isoformat()
            source = demo_sources[i % len(demo_sources)]
            con.execute("INSERT OR IGNORE INTO live_sessions(id,started_at,ended_at,source,frames,detections,status) VALUES(?,?,?,?,?,?,?)",
                (sid, started, ended, source, 420 + i*37, 12 + i*3, "completed"))
            demo_sessions.append((sid, started, source))

        alert_count = con.execute("SELECT COUNT(*) FROM live_alerts").fetchone()[0]
        for i in range(max(0, 10-alert_count)):
            sid, started, source = demo_sessions[i]
            created = (now - timedelta(minutes=10*i+2)).isoformat()
            label = labels[i]
            track = 100 + i
            status = ["pending", "in_review", "resolved", "dismissed", "resolved"][i % 5]
            severity = "critical" if label == "persona" else ("warning" if label in ("pallet", "casco") else "info")
            title = ["Persona detectada en zona operativa", "Objeto en ruta de circulación", "Verificación de equipo móvil", "Elemento en área de inspección", "Revisión preventiva de seguridad"][i % 5]
            description = f"DEMO: registro inicial de ejemplo para probar el historial. Entidad: {label}; escenario: {source}. No corresponde a una detección real."
            con.execute("INSERT INTO live_alerts(created_at,updated_at,title,description,severity,status,source,session_id,track_id,label,confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (created, created, title, description, severity, status, source, sid, track, label, round(.78 + (i%4)*.04, 2)))

        event_count = con.execute("SELECT COUNT(*) FROM live_events").fetchone()[0]
        for i in range(max(0, 10-event_count)):
            sid, started, source = demo_sessions[i]
            created = (now - timedelta(minutes=10*i+2)).isoformat()
            label = labels[i]
            box = {"x": 80+i*12, "y": 60+i*7, "width": 110, "height": 180}
            con.execute("INSERT INTO live_events(session_id,created_at,source,track_id,label,confidence,box_json,snapshot_path) VALUES(?,?,?,?,?,?,?,?)",
                (sid, created, source, 100+i, label, round(.78 + (i%4)*.04, 2), json.dumps(box), None))

@app.post('/api/live/sessions')
def create_live_session(payload: dict):
    sid = str(uuid.uuid4())
    source = str(payload.get('source', 'webcam'))[:120]
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        con.execute('INSERT INTO live_sessions(id,started_at,source,status) VALUES(?,?,?,?)', (sid,now,source,'active'))
    return {'id': sid, 'started_at': now, 'source': source}

@app.post('/api/live/sessions/{session_id}/stop')
def stop_live_session(session_id: str):
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute("UPDATE live_sessions SET ended_at=?,status='completed' WHERE id=?", (now,session_id))
        if cur.rowcount == 0: raise HTTPException(404, 'Sesión no encontrada.')
    return {'id':session_id,'status':'completed','ended_at':now}

@app.get('/api/live/sessions')
def list_live_sessions(limit: int = 100):
    with db() as con:
        rows = con.execute('SELECT * FROM live_sessions ORDER BY started_at DESC LIMIT ?', (max(1,min(limit,500)),)).fetchall()
    return [dict(r) for r in rows]

@app.get('/api/live/events')
def list_live_events(limit: int = 200):
    with db() as con:
        rows = con.execute('SELECT * FROM live_events ORDER BY created_at DESC LIMIT ?', (max(1,min(limit,1000)),)).fetchall()
    out=[]
    for r in rows:
        item=dict(r); item['box']=json.loads(item.pop('box_json')); out.append(item)
    return out



@app.get('/api/live/alerts')
def list_live_alerts(limit: int = 500):
    with db() as con:
        rows = con.execute('SELECT * FROM live_alerts ORDER BY created_at DESC LIMIT ?', (max(1,min(limit,1000)),)).fetchall()
    return [dict(r) for r in rows]

@app.post('/api/live/alerts/demo')
def create_demo_alert(payload: dict):
    title = str(payload.get('title', 'Evento de simulación'))[:120]
    description_raw = str(payload.get('description', 'Evento sintético para validar el flujo de alertas.'))[:400]
    description = description_raw if description_raw.startswith('DEMO:') else 'DEMO: ' + description_raw
    severity = str(payload.get('severity', 'info'))
    if severity not in ('info', 'warning', 'critical'): severity = 'info'
    label = str(payload.get('label', 'Entidad simulada'))[:80]
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute('INSERT INTO live_alerts(created_at,updated_at,title,description,severity,status,source,session_id,track_id,label,confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (now,now,title,description,severity,'pending','Galería de escenarios · DEMO',None,None,label,0.0))
        row = con.execute('SELECT * FROM live_alerts WHERE id=?', (cur.lastrowid,)).fetchone()
    return dict(row)

@app.patch('/api/live/alerts/{alert_id}')
def update_live_alert(alert_id: int, payload: dict):
    status = str(payload.get('status', ''))
    if status not in ('pending', 'in_review', 'resolved', 'dismissed'):
        raise HTTPException(400, 'Estado de alerta no válido.')
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute('UPDATE live_alerts SET status=?, updated_at=? WHERE id=?', (status, now, alert_id))
        if cur.rowcount == 0: raise HTTPException(404, 'Alerta no encontrada.')
        row = con.execute('SELECT * FROM live_alerts WHERE id=?', (alert_id,)).fetchone()
    return dict(row)

@app.get('/api/live/alerts.csv')
def export_live_alerts():
    with db() as con:
        rows = con.execute('SELECT id,created_at,updated_at,title,description,severity,status,source,session_id,track_id,label,confidence FROM live_alerts ORDER BY created_at DESC').fetchall()
    output=io.StringIO(); writer=csv.writer(output)
    writer.writerow(['id','creada','actualizada','alerta','detalle','severidad','estado','fuente','sesion','track_id','entidad','confianza'])
    for row in rows: writer.writerow(list(row))
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type='text/csv; charset=utf-8', headers={'Content-Disposition':'attachment; filename=vision_ai_alertas.csv'})

@app.websocket('/api/live/ws/{session_id}')
async def live_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    last_event = {}
    last_alert = {}
    frame_count = 0
    try:
        while True:
            message = await websocket.receive_json()
            encoded = message.get('frame','')
            if not encoded: continue
            try:
                raw = base64.b64decode(encoded.split(',',1)[-1], validate=True)
                arr = np.frombuffer(raw, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None: continue
            except Exception:
                await websocket.send_json({'type':'error','message':'Fotograma inválido.'}); continue
            threshold = float(message.get('confidence',0.35))
            threshold = min(.95,max(.05,threshold))
            mode = message.get('mode','detection')
            model_key = 'segmentation' if mode == 'segmentation' else 'detection'
            started=time.perf_counter()
            try:
                model=get_model(model_key)
                results=model.track(frame, persist=True, tracker='bytetrack.yaml', conf=threshold, verbose=False)
                pred=results[0]
            except Exception as exc:
                await websocket.send_json({'type':'error','message':f'Error del motor IA: {str(exc)[:180]}'})
                continue
            duration=(time.perf_counter()-started)*1000
            h,w=frame.shape[:2]; detections=[]
            if pred.boxes is not None:
                for i,b in enumerate(pred.boxes):
                    x1,y1,x2,y2=[float(v) for v in b.xyxy[0].cpu().tolist()]
                    cls=int(b.cls[0].item()); conf=float(b.conf[0].item())
                    track_id=int(b.id[0].item()) if b.id is not None else None
                    detections.append({'id':i+1,'track_id':track_id,'label':pred.names.get(cls,str(cls)),'confidence':round(conf,4),'box':{'x':round(x1,1),'y':round(y1,1),'width':round(x2-x1,1),'height':round(y2-y1,1)}})
            frame_count += 1
            # Evitar registrar el mismo track continuamente: un evento por track cada 10 segundos.
            now=time.time(); events=[]
            for d in detections:
                key=f"{d['track_id']}:{d['label']}"
                if key not in last_event or now-last_event[key] >= 10:
                    last_event[key]=now; events.append(d)
            with db() as con:
                con.execute('UPDATE live_sessions SET frames=frames+1,detections=detections+? WHERE id=?',(len(detections),session_id))
                for d in events:
                    created = datetime.now(timezone.utc).isoformat()
                    source_name = str(message.get('source','webcam'))[:120]
                    con.execute('INSERT INTO live_events(session_id,created_at,source,track_id,label,confidence,box_json) VALUES(?,?,?,?,?,?,?)',
                      (session_id,created,source_name,d['track_id'],d['label'],d['confidence'],json.dumps(d['box'])))
                # Reglas iniciales configurables por tipo de entidad: presencia de persona/vehículo u objeto detectado.
                for d in detections:
                    key = f"{d['track_id']}:{d['label']}"
                    if time.time() - last_alert.get(key, 0) < 30: continue
                    label_lower = d['label'].lower()
                    if any(term in label_lower for term in ('person','persona')):
                        title, desc, severity = 'Presencia detectada', f"Se detectó una persona en la escena. Revisar contexto y zona de operación. Track #{d['track_id'] if d['track_id'] is not None else 'N/D'}.", 'warning'
                    elif any(term in label_lower for term in ('car','truck','bus','motorcycle','bicycle')):
                        title, desc, severity = 'Vehículo detectado', f"Se detectó {d['label']} en el campo visual. Verificar circulación y zona permitida.", 'info'
                    else:
                        title, desc, severity = 'Objeto detectado', f"El motor identificó {d['label']}. Revisar si corresponde a una condición operativa relevante.", 'info'
                    now_iso = datetime.now(timezone.utc).isoformat()
                    con.execute('INSERT INTO live_alerts(created_at,updated_at,title,description,severity,status,source,session_id,track_id,label,confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      (now_iso,now_iso,title,desc,severity,'pending',str(message.get('source','webcam'))[:120],session_id,d['track_id'],d['label'],d['confidence']))
                    last_alert[key] = time.time()
            await websocket.send_json({'type':'result','width':w,'height':h,'fps_latency_ms':round(duration,2),'frame':frame_count,'detections':detections,'events':len(events)})
    except WebSocketDisconnect:
        return
    except Exception:
        try: await websocket.close(code=1011)
        except Exception: pass

@app.get('/api/live/events.csv')
def export_live_events():
    with db() as con:
        rows=con.execute('SELECT id,created_at,source,session_id,track_id,label,confidence,box_json FROM live_events ORDER BY created_at DESC').fetchall()
    output=io.StringIO(); writer=csv.writer(output)
    writer.writerow(['id','fecha_utc','fuente','sesion','track_id','objeto','confianza','bounding_box_json'])
    for row in rows: writer.writerow(list(row))
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=vision_ai_eventos.csv'})
