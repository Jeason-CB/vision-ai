export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertState = 'new' | 'reviewed' | 'closed';
export interface Alert {
  id: string; analysisId: string; severity: AlertSeverity; rule: string;
  message: string; createdAt: string; state: AlertState; reviewer?: string;
}
