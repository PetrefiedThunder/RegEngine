'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Header } from '@/components/layout/header';
import { PageContainer } from '@/components/layout/page-container';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinner';
import { useAPIKeys, useCreateAPIKey, useRevokeAPIKey } from '@/hooks/use-api';
import { Key, Plus, Trash2, CheckCircle, Copy, Shield } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState('');
  const [newKeyDescription, setNewKeyDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const { data: apiKeys, isLoading, refetch } = useAPIKeys(adminKey, !!adminKey);
  const createKeyMutation = useCreateAPIKey();
  const revokeKeyMutation = useRevokeAPIKey();

  const handleCreateKey = async () => {
    if (!adminKey) return;

    try {
      const result = await createKeyMutation.mutateAsync({
        adminKey,
        description: newKeyDescription || undefined,
      });
      setNewKeyDescription('');
      setIsCreating(false);
      if (result.api_key) {
        setCopiedKey(result.api_key);
      }
      refetch();
    } catch (error) {
      console.error('Failed to create API key:', error);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!adminKey || !confirm('Are you sure you want to revoke this API key?')) return;

    try {
      await revokeKeyMutation.mutateAsync({ adminKey, keyId });
      refetch();
    } catch (error) {
      console.error('Failed to revoke API key:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <Header />
      <PageContainer>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-6xl mx-auto"
        >
          {/* Page Header */}
          <div className="flex items-center gap-4 mb-8">
            <div className="p-3 rounded-lg bg-orange-100 dark:bg-orange-900">
              <Key className="h-8 w-8 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold">API Management</h1>
              <p className="text-muted-foreground mt-1">
                Manage API keys and access controls
              </p>
            </div>
          </div>

          {/* Admin Key Input */}
          {!adminKey && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle>Authentication Required</CardTitle>
                <CardDescription>
                  Enter your admin key to manage API keys
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  <Input
                    type="password"
                    placeholder="Enter admin key"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && refetch()}
                  />
                  <Button onClick={() => refetch()}>
                    <Shield className="h-4 w-4 mr-2" />
                    Authenticate
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Authenticated View */}
          {adminKey && (
            <>
              {/* New Key Creation */}
              <Card className="mb-8">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Create New API Key</CardTitle>
                      <CardDescription>
                        Generate a new API key for accessing RegEngine services
                      </CardDescription>
                    </div>
                    {!isCreating && (
                      <Button onClick={() => setIsCreating(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Key
                      </Button>
                    )}
                  </div>
                </CardHeader>
                {isCreating && (
                  <CardContent>
                    <div className="space-y-4">
                      <Input
                        placeholder="Description (optional)"
                        value={newKeyDescription}
                        onChange={(e) => setNewKeyDescription(e.target.value)}
                      />
                      <div className="flex gap-2">
                        <Button
                          onClick={handleCreateKey}
                          disabled={createKeyMutation.isPending}
                        >
                          {createKeyMutation.isPending ? (
                            <>
                              <Spinner size="sm" className="mr-2" />
                              Creating...
                            </>
                          ) : (
                            'Create Key'
                          )}
                        </Button>
                        <Button variant="outline" onClick={() => setIsCreating(false)}>
                          Cancel
                        </Button>
                      </div>
                    </div>

                    {copiedKey && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-4 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
                      >
                        <div className="flex items-start gap-3">
                          <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                          <div className="flex-1">
                            <h4 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                              API Key Created Successfully
                            </h4>
                            <p className="text-sm text-green-700 dark:text-green-300 mb-2">
                              Save this key now - it won&apos;t be shown again!
                            </p>
                            <div className="flex items-center gap-2">
                              <code className="flex-1 text-sm bg-white dark:bg-gray-800 p-2 rounded font-mono">
                                {copiedKey}
                              </code>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => copyToClipboard(copiedKey)}
                              >
                                <Copy className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </CardContent>
                )}
              </Card>

              {/* API Keys List */}
              <Card>
                <CardHeader>
                  <CardTitle>API Keys</CardTitle>
                  <CardDescription>
                    Manage existing API keys
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <div className="flex justify-center py-8">
                      <Spinner size="md" />
                    </div>
                  ) : apiKeys && apiKeys.length > 0 ? (
                    <div className="space-y-3">
                      {apiKeys.map((key) => (
                        <motion.div
                          key={key.key_id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent smooth-transition"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-1">
                              <Key className="h-4 w-4 text-muted-foreground" />
                              <code className="text-sm font-mono">{key.key_id}</code>
                              <Badge variant="secondary">Active</Badge>
                            </div>
                            {key.description && (
                              <p className="text-sm text-muted-foreground ml-7">
                                {key.description}
                              </p>
                            )}
                            <p className="text-xs text-muted-foreground ml-7 mt-1">
                              Created {formatDate(key.created_at)}
                            </p>
                          </div>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleRevokeKey(key.key_id)}
                            disabled={revokeKeyMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Key className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
                      <p className="text-muted-foreground">No API keys found</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </motion.div>
      </PageContainer>
    </div>
  );
}
