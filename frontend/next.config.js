/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost',
    NEXT_PUBLIC_ADMIN_PORT: process.env.NEXT_PUBLIC_ADMIN_PORT || '8400',
    NEXT_PUBLIC_INGESTION_PORT: process.env.NEXT_PUBLIC_INGESTION_PORT || '8000',
    NEXT_PUBLIC_OPPORTUNITY_PORT: process.env.NEXT_PUBLIC_OPPORTUNITY_PORT || '8300',
    NEXT_PUBLIC_COMPLIANCE_PORT: process.env.NEXT_PUBLIC_COMPLIANCE_PORT || '8500',
  },
}

module.exports = nextConfig
