// API Response Types for RegEngine

export interface HealthCheckResponse {
  status: string;
  service: string;
}

export interface APIKeyResponse {
  key_id: string;
  api_key?: string;
  created_at: string;
  description?: string;
}

export interface IngestURLRequest {
  url: string;
}

export interface IngestURLResponse {
  doc_id: string;
  status: string;
  message: string;
}

export interface ComplianceChecklist {
  id: string;
  name: string;
  description: string;
  industry: string;
  version: string;
  items: ComplianceChecklistItem[];
}

export interface ComplianceChecklistItem {
  id: string;
  requirement: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
}

export interface ValidationRequest {
  checklist_id: string;
  config: Record<string, unknown>;
}

export interface ValidationResult {
  checklist_id: string;
  passed: boolean;
  failures: ValidationFailure[];
  warnings: ValidationWarning[];
}

export interface ValidationFailure {
  item_id: string;
  requirement: string;
  message: string;
  severity: string;
}

export interface ValidationWarning {
  item_id: string;
  requirement: string;
  message: string;
}

export interface OpportunityArbitrage {
  concept: string;
  jurisdiction1: string;
  jurisdiction2: string;
  delta: number;
  description: string;
}

export interface ComplianceGap {
  jurisdiction1: string;
  jurisdiction2: string;
  gap_type: string;
  description: string;
  severity: string;
}

export interface Industry {
  id: string;
  name: string;
  description: string;
  checklist_count: number;
}
