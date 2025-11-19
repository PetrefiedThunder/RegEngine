'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/layout/header';
import { PageContainer } from '@/components/layout/page-container';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinner';
import { useArbitrageOpportunities, useComplianceGaps } from '@/hooks/use-api';
import { TrendingUp, AlertTriangle, Globe, ArrowRight } from 'lucide-react';

type ViewMode = 'arbitrage' | 'gaps';

export default function OpportunitiesPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('arbitrage');
  const [j1, setJ1] = useState('');
  const [j2, setJ2] = useState('');
  const [concept, setConcept] = useState('');

  const { data: arbitrageData, isLoading: arbitrageLoading } = useArbitrageOpportunities({
    j1: j1 || undefined,
    j2: j2 || undefined,
    concept: concept || undefined,
    limit: 50,
  });

  const { data: gapsData, isLoading: gapsLoading } = useComplianceGaps({
    j1: j1 || undefined,
    j2: j2 || undefined,
    limit: 50,
  });

  const isLoading = viewMode === 'arbitrage' ? arbitrageLoading : gapsLoading;
  const data = viewMode === 'arbitrage' ? arbitrageData : gapsData;

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <Header />
      <PageContainer>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Page Header */}
          <div className="flex items-center gap-4 mb-8">
            <div className="p-3 rounded-lg bg-purple-100 dark:bg-purple-900">
              <TrendingUp className="h-8 w-8 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold">Regulatory Opportunities</h1>
              <p className="text-muted-foreground mt-1">
                Discover arbitrage opportunities and compliance gaps across jurisdictions
              </p>
            </div>
          </div>

          {/* View Mode Toggle */}
          <Card className="mb-8">
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex gap-2">
                  <Button
                    variant={viewMode === 'arbitrage' ? 'default' : 'outline'}
                    onClick={() => setViewMode('arbitrage')}
                  >
                    <TrendingUp className="h-4 w-4 mr-2" />
                    Arbitrage Opportunities
                  </Button>
                  <Button
                    variant={viewMode === 'gaps' ? 'default' : 'outline'}
                    onClick={() => setViewMode('gaps')}
                  >
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    Compliance Gaps
                  </Button>
                </div>

                <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-2">
                  <Input
                    placeholder="Jurisdiction 1"
                    value={j1}
                    onChange={(e) => setJ1(e.target.value)}
                  />
                  <Input
                    placeholder="Jurisdiction 2"
                    value={j2}
                    onChange={(e) => setJ2(e.target.value)}
                  />
                  {viewMode === 'arbitrage' && (
                    <Input
                      placeholder="Concept (optional)"
                      value={concept}
                      onChange={(e) => setConcept(e.target.value)}
                    />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          {isLoading ? (
            <div className="flex justify-center items-center py-16">
              <Spinner size="lg" />
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={viewMode}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                {data && data.length > 0 ? (
                  viewMode === 'arbitrage' ? (
                    // Arbitrage Opportunities
                    arbitrageData?.map((opportunity, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <Card className="card-hover">
                          <CardHeader>
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <Badge variant="secondary">{opportunity.concept}</Badge>
                                  <Badge variant={opportunity.delta > 0.5 ? 'warning' : 'outline'}>
                                    Δ {opportunity.delta.toFixed(2)}
                                  </Badge>
                                </div>
                                <CardTitle className="text-xl mb-2">
                                  Regulatory Arbitrage Opportunity
                                </CardTitle>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <Globe className="h-4 w-4" />
                                  <span>{opportunity.jurisdiction1}</span>
                                  <ArrowRight className="h-4 w-4" />
                                  <span>{opportunity.jurisdiction2}</span>
                                </div>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-muted-foreground">{opportunity.description}</p>
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))
                  ) : (
                    // Compliance Gaps
                    gapsData?.map((gap, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <Card className="card-hover">
                          <CardHeader>
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <Badge variant="destructive">{gap.gap_type}</Badge>
                                  <Badge variant="outline">{gap.severity}</Badge>
                                </div>
                                <CardTitle className="text-xl mb-2">
                                  Compliance Gap Detected
                                </CardTitle>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <Globe className="h-4 w-4" />
                                  <span>{gap.jurisdiction1}</span>
                                  <ArrowRight className="h-4 w-4" />
                                  <span>{gap.jurisdiction2}</span>
                                </div>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-muted-foreground">{gap.description}</p>
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))
                  )
                ) : (
                  <div className="text-center py-16">
                    <TrendingUp className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
                    <h3 className="text-xl font-semibold mb-2">No opportunities found</h3>
                    <p className="text-muted-foreground">
                      Try adjusting your search criteria or ensure data has been ingested
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          )}

          {/* Info Section */}
          <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Regulatory Arbitrage</CardTitle>
                <CardDescription>
                  Identify differences in regulatory requirements across jurisdictions that could represent business opportunities
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Compare requirements across jurisdictions</li>
                  <li>• Quantify regulatory deltas</li>
                  <li>• Discover cost-saving opportunities</li>
                </ul>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Compliance Gaps</CardTitle>
                <CardDescription>
                  Find areas where your compliance posture may have gaps when operating across multiple jurisdictions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Identify missing requirements</li>
                  <li>• Prioritize by severity</li>
                  <li>• Maintain compliance across regions</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </PageContainer>
    </div>
  );
}
