'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Header } from '@/components/layout/header';
import { PageContainer } from '@/components/layout/page-container';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { useIngestURL } from '@/hooks/use-api';
import { Database, CheckCircle, AlertCircle, Link2 } from 'lucide-react';

export default function IngestPage() {
  const [url, setUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const ingestMutation = useIngestURL();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !apiKey) return;

    try {
      await ingestMutation.mutateAsync({ apiKey, url });
    } catch (error) {
      console.error('Ingestion failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <Header />
      <PageContainer>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-4xl mx-auto"
        >
          {/* Page Header */}
          <div className="flex items-center gap-4 mb-8">
            <div className="p-3 rounded-lg bg-blue-100 dark:bg-blue-900">
              <Database className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold">Document Ingestion</h1>
              <p className="text-muted-foreground mt-1">
                Submit regulatory document URLs for processing
              </p>
            </div>
          </div>

          {/* Ingestion Form */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Ingest New Document</CardTitle>
              <CardDescription>
                Provide a URL to a regulatory document. Our system will fetch, normalize, and extract regulatory entities.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">API Key</label>
                  <Input
                    type="password"
                    placeholder="Enter your API key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    disabled={ingestMutation.isPending}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Document URL</label>
                  <div className="relative">
                    <Link2 className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="url"
                      placeholder="https://example.com/regulatory-document.pdf"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      className="pl-10"
                      disabled={ingestMutation.isPending}
                    />
                  </div>
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={!url || !apiKey || ingestMutation.isPending}
                >
                  {ingestMutation.isPending ? (
                    <>
                      <Spinner size="sm" className="mr-2" />
                      Processing...
                    </>
                  ) : (
                    'Ingest Document'
                  )}
                </Button>
              </form>

              {/* Success Message */}
              {ingestMutation.isSuccess && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
                >
                  <div className="flex items-start gap-3">
                    <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-green-900 dark:text-green-100">
                        Document Ingested Successfully
                      </h4>
                      <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                        Document ID: <code className="font-mono">{ingestMutation.data?.doc_id}</code>
                      </p>
                      <p className="text-sm text-green-700 dark:text-green-300">
                        {ingestMutation.data?.message}
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Error Message */}
              {ingestMutation.isError && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                >
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-red-900 dark:text-red-100">
                        Ingestion Failed
                      </h4>
                      <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                        {ingestMutation.error?.message || 'An error occurred during ingestion'}
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <h3 className="font-semibold mb-2">OCR Processing</h3>
                <p className="text-sm text-muted-foreground">
                  Automatic optical character recognition for scanned documents
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <h3 className="font-semibold mb-2">NLP Extraction</h3>
                <p className="text-sm text-muted-foreground">
                  Extract regulatory entities, obligations, and thresholds
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <h3 className="font-semibold mb-2">Graph Storage</h3>
                <p className="text-sm text-muted-foreground">
                  Store in Neo4j with bitemporal modeling for compliance tracking
                </p>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </PageContainer>
    </div>
  );
}
