import type {Analysis} from '../domain/entities/Analysis';
export interface AnalysisRepository {
  list(): Promise<Analysis[]>;
  getById(id: string): Promise<Analysis | null>;
}
