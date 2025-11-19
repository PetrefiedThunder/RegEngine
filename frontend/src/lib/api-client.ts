import axios, { AxiosInstance } from 'axios';
import { getServiceURL } from './api-config';
import type {
  HealthCheckResponse,
  APIKeyResponse,
  IngestURLRequest,
  IngestURLResponse,
  ComplianceChecklist,
  ValidationRequest,
  ValidationResult,
  OpportunityArbitrage,
  ComplianceGap,
  Industry,
} from '@/types/api';

class APIClient {
  private adminClient: AxiosInstance;
  private ingestionClient: AxiosInstance;
  private opportunityClient: AxiosInstance;
  private complianceClient: AxiosInstance;

  constructor() {
    this.adminClient = axios.create({
      baseURL: getServiceURL('admin'),
      timeout: 30000,
    });

    this.ingestionClient = axios.create({
      baseURL: getServiceURL('ingestion'),
      timeout: 30000,
    });

    this.opportunityClient = axios.create({
      baseURL: getServiceURL('opportunity'),
      timeout: 30000,
    });

    this.complianceClient = axios.create({
      baseURL: getServiceURL('compliance'),
      timeout: 30000,
    });
  }

  // Admin API
  async getAdminHealth(): Promise<HealthCheckResponse> {
    const { data } = await this.adminClient.get('/health');
    return data;
  }

  async createAPIKey(adminKey: string, description?: string): Promise<APIKeyResponse> {
    const { data } = await this.adminClient.post(
      '/admin/keys',
      { description },
      { headers: { 'X-Admin-Key': adminKey } }
    );
    return data;
  }

  async listAPIKeys(adminKey: string): Promise<APIKeyResponse[]> {
    const { data } = await this.adminClient.get('/admin/keys', {
      headers: { 'X-Admin-Key': adminKey },
    });
    return data;
  }

  async revokeAPIKey(adminKey: string, keyId: string): Promise<void> {
    await this.adminClient.delete(`/admin/keys/${keyId}`, {
      headers: { 'X-Admin-Key': adminKey },
    });
  }

  // Ingestion API
  async getIngestionHealth(): Promise<HealthCheckResponse> {
    const { data } = await this.ingestionClient.get('/health');
    return data;
  }

  async ingestURL(apiKey: string, url: string): Promise<IngestURLResponse> {
    const { data } = await this.ingestionClient.post<IngestURLResponse>(
      '/ingest/url',
      { url },
      { headers: { 'X-RegEngine-API-Key': apiKey } }
    );
    return data;
  }

  // Opportunity API
  async getOpportunityHealth(): Promise<HealthCheckResponse> {
    const { data } = await this.opportunityClient.get('/health');
    return data;
  }

  async getArbitrageOpportunities(params: {
    j1?: string;
    j2?: string;
    concept?: string;
    rel_delta?: number;
    limit?: number;
    since?: string;
  }): Promise<OpportunityArbitrage[]> {
    const { data } = await this.opportunityClient.get('/opportunities/arbitrage', { params });
    return data;
  }

  async getComplianceGaps(params: {
    j1?: string;
    j2?: string;
    limit?: number;
  }): Promise<ComplianceGap[]> {
    const { data } = await this.opportunityClient.get('/opportunities/gaps', { params });
    return data;
  }

  // Compliance API
  async getComplianceHealth(): Promise<HealthCheckResponse> {
    const { data } = await this.complianceClient.get('/health');
    return data;
  }

  async getChecklists(industry?: string): Promise<ComplianceChecklist[]> {
    const { data } = await this.complianceClient.get('/checklists', {
      params: industry ? { industry } : undefined,
    });
    return data;
  }

  async getChecklist(checklistId: string): Promise<ComplianceChecklist> {
    const { data } = await this.complianceClient.get(`/checklists/${checklistId}`);
    return data;
  }

  async validateConfig(request: ValidationRequest): Promise<ValidationResult> {
    const { data } = await this.complianceClient.post('/validate', request);
    return data;
  }

  async getIndustries(): Promise<Industry[]> {
    const { data } = await this.complianceClient.get('/industries');
    return data;
  }
}

export const apiClient = new APIClient();
