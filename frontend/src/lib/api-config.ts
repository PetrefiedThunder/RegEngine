export const API_CONFIG = {
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost',
  ports: {
    admin: process.env.NEXT_PUBLIC_ADMIN_PORT || '8400',
    ingestion: process.env.NEXT_PUBLIC_INGESTION_PORT || '8000',
    opportunity: process.env.NEXT_PUBLIC_OPPORTUNITY_PORT || '8300',
    compliance: process.env.NEXT_PUBLIC_COMPLIANCE_PORT || '8500',
  },
  timeout: 30000,
};

export const getServiceURL = (service: keyof typeof API_CONFIG.ports): string => {
  return `${API_CONFIG.baseURL}:${API_CONFIG.ports[service]}`;
};
