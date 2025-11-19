'use client';

import Link from 'next/link';
import {
  Activity,
  Database,
  TrendingUp,
  CheckCircle,
  Key
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  useAdminHealth,
  useIngestionHealth,
  useOpportunityHealth,
  useComplianceHealth,
} from '@/hooks/use-api';

export function Header() {
  const adminHealth = useAdminHealth();
  const ingestionHealth = useIngestionHealth();
  const opportunityHealth = useOpportunityHealth();
  const complianceHealth = useComplianceHealth();

  const allHealthy =
    adminHealth.data?.status === 'healthy' &&
    ingestionHealth.data?.status === 'healthy' &&
    opportunityHealth.data?.status === 'healthy' &&
    complianceHealth.data?.status === 'healthy';

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur-lg dark:bg-gray-900/80">
      <div className="container flex h-16 items-center justify-between px-6">
        <Link href="/" className="flex items-center space-x-2 smooth-transition hover:scale-105">
          <Activity className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">RegEngine</span>
        </Link>

        <nav className="flex items-center space-x-1">
          <Link
            href="/ingest"
            className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-accent smooth-transition"
          >
            <Database className="h-4 w-4" />
            <span>Ingest</span>
          </Link>
          <Link
            href="/compliance"
            className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-accent smooth-transition"
          >
            <CheckCircle className="h-4 w-4" />
            <span>Compliance</span>
          </Link>
          <Link
            href="/opportunities"
            className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-accent smooth-transition"
          >
            <TrendingUp className="h-4 w-4" />
            <span>Opportunities</span>
          </Link>
          <Link
            href="/admin"
            className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-accent smooth-transition"
          >
            <Key className="h-4 w-4" />
            <span>Admin</span>
          </Link>
        </nav>

        <div className="flex items-center space-x-4">
          <Badge variant={allHealthy ? 'success' : 'warning'}>
            {allHealthy ? 'All Systems Operational' : 'Checking...'}
          </Badge>
        </div>
      </div>
    </header>
  );
}
