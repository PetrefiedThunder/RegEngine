'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/layout/header';
import { PageContainer } from '@/components/layout/page-container';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { useChecklists, useIndustries } from '@/hooks/use-api';
import { CheckCircle, Filter, Search, Shield } from 'lucide-react';
import { Input } from '@/components/ui/input';

export default function CompliancePage() {
  const [selectedIndustry, setSelectedIndustry] = useState<string | undefined>();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: industries, isLoading: industriesLoading } = useIndustries();
  const { data: checklists, isLoading: checklistsLoading } = useChecklists(selectedIndustry);

  const filteredChecklists = checklists?.filter((checklist) =>
    checklist.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    checklist.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
            <div className="p-3 rounded-lg bg-green-100 dark:bg-green-900">
              <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold">Compliance Checklists</h1>
              <p className="text-muted-foreground mt-1">
                Browse and validate against industry-specific compliance requirements
              </p>
            </div>
          </div>

          {/* Filters */}
          <Card className="mb-8">
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                {/* Search */}
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search checklists..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Industry Filter */}
                <div className="flex gap-2 flex-wrap">
                  <Button
                    variant={selectedIndustry === undefined ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedIndustry(undefined)}
                  >
                    All Industries
                  </Button>
                  {industriesLoading ? (
                    <Spinner size="sm" />
                  ) : (
                    industries?.map((industry) => (
                      <Button
                        key={industry.id}
                        variant={selectedIndustry === industry.id ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setSelectedIndustry(industry.id)}
                      >
                        {industry.name}
                      </Button>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Checklists Grid */}
          {checklistsLoading ? (
            <div className="flex justify-center items-center py-16">
              <Spinner size="lg" />
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={selectedIndustry || 'all'}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              >
                {filteredChecklists && filteredChecklists.length > 0 ? (
                  filteredChecklists.map((checklist, index) => (
                    <motion.div
                      key={checklist.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      whileHover={{ scale: 1.02 }}
                    >
                      <Card className="h-full cursor-pointer group hover:shadow-xl smooth-transition">
                        <CardHeader>
                          <div className="flex items-start justify-between mb-2">
                            <Shield className="h-8 w-8 text-primary" />
                            <Badge variant="secondary">{checklist.industry}</Badge>
                          </div>
                          <CardTitle className="group-hover:text-primary smooth-transition">
                            {checklist.name}
                          </CardTitle>
                          <CardDescription className="line-clamp-2">
                            {checklist.description}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">
                              {checklist.items?.length || 0} requirements
                            </span>
                            <Badge variant="outline">v{checklist.version}</Badge>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))
                ) : (
                  <div className="col-span-full text-center py-16">
                    <Shield className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
                    <h3 className="text-xl font-semibold mb-2">No checklists found</h3>
                    <p className="text-muted-foreground">
                      {searchQuery
                        ? 'Try adjusting your search criteria'
                        : 'No compliance checklists available for the selected industry'}
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          )}

          {/* Info Cards */}
          <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Validation API</CardTitle>
                <CardDescription>
                  Validate your configuration against any checklist programmatically
                </CardDescription>
              </CardHeader>
              <CardContent>
                <code className="text-xs bg-muted p-2 rounded block">
                  POST /validate
                </code>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Multi-Industry Support</CardTitle>
                <CardDescription>
                  Pre-built checklists for Healthcare (HIPAA, FDA), Finance, Gaming, Energy, and Technology
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  <Badge>HIPAA</Badge>
                  <Badge>FDA</Badge>
                  <Badge>SOC 2</Badge>
                  <Badge>PCI DSS</Badge>
                  <Badge>GDPR</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </PageContainer>
    </div>
  );
}
