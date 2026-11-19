/**
 * Contrato desacoplado según la arquitectura del informe VISION AI.
 * La interfaz no debe conocer la librería concreta del modelo.
 */
export type VisionMode = 'detection' | 'segmentation';
export interface VisionInput {
  file: File;
  mode: VisionMode;
  confidenceThreshold: number;
}
export interface VisionDetection {
  id: number; label: string; confidence: number;
  box: { x:number; y:number; width:number; height:number };
  center: { x:number; y:number };
  area_px2: number; aspect_ratio: number | null;
}
export interface VisionResult {
  id: string; created_at: string; filename: string; mode: VisionMode;
  model: string; duration_ms: number; image: {width:number;height:number};
  detection_count: number; average_confidence: number;
  detections: VisionDetection[];
}
export interface VisionEngine {
  analyze(input: VisionInput): Promise<VisionResult>;
}
