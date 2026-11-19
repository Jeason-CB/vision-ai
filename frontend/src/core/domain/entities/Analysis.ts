export type AnalysisStatus = 'processing' | 'completed' | 'warning' | 'error';
export interface Analysis {
  id: string; createdAt: string; sourceName: string; scenarioId: string | null;
  mode: 'detection' | 'segmentation'; status: AnalysisStatus;
  durationMs: number; averageConfidence: number; detectionCount: number;
}
