'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { Header } from '@/components/layout/header';
import { PageContainer } from '@/components/layout/page-container';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Database,
  TrendingUp,
  CheckCircle,
  Key,
  ArrowRight,
  Zap,
  Shield,
  Globe
} from 'lucide-react';

const features = [
  {
    icon: Database,
    title: 'Document Ingestion',
    description: 'Automatically fetch and normalize regulatory documents with OCR and NLP',
    href: '/ingest',
    color: 'text-blue-500',
  },
  {
    icon: CheckCircle,
    title: 'Compliance Validation',
    description: 'Validate configurations against multi-industry compliance checklists',
    href: '/compliance',
    color: 'text-green-500',
  },
  {
    icon: TrendingUp,
    title: 'Regulatory Opportunities',
    description: 'Discover arbitrage opportunities and compliance gaps across jurisdictions',
    href: '/opportunities',
    color: 'text-purple-500',
  },
  {
    icon: Key,
    title: 'API Management',
    description: 'Manage API keys and access controls for your organization',
    href: '/admin',
    color: 'text-orange-500',
  },
];

const stats = [
  { label: 'Industries Supported', value: '5+', icon: Globe },
  { label: 'Compliance Checklists', value: '20+', icon: Shield },
  { label: 'Real-time Processing', value: '100%', icon: Zap },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <Header />
      <PageContainer>
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-block mb-4"
          >
            <Badge variant="secondary" className="text-sm px-4 py-1">
              Regulatory Intelligence Platform
            </Badge>
          </motion.div>
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
            Welcome to RegEngine
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
            Automated regulatory compliance and intelligence platform with multi-industry support
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/compliance">
              <Button size="lg">
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/opportunities">
              <Button size="lg" variant="outline">
                Explore Opportunities
              </Button>
            </Link>
          </div>
        </motion.div>

        {/* Stats Section */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16"
        >
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + index * 0.1, duration: 0.5 }}
            >
              <Card className="text-center">
                <CardContent className="pt-6">
                  <stat.icon className="h-8 w-8 mx-auto mb-3 text-primary" />
                  <div className="text-3xl font-bold mb-1">{stat.value}</div>
                  <div className="text-sm text-muted-foreground">{stat.label}</div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6"
        >
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + index * 0.1, duration: 0.5 }}
              whileHover={{ scale: 1.02 }}
            >
              <Link href={feature.href}>
                <Card className="h-full cursor-pointer group">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <feature.icon className={`h-10 w-10 ${feature.color} group-hover:scale-110 smooth-transition`} />
                      <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:translate-x-1 smooth-transition" />
                    </div>
                    <CardTitle className="group-hover:text-primary smooth-transition">{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            </motion.div>
          ))}
        </motion.div>

        {/* Industries Section */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9, duration: 0.6 }}
          className="mt-16"
        >
          <Card>
            <CardHeader>
              <CardTitle>Supported Industries</CardTitle>
              <CardDescription>
                Pre-built compliance checklists for multiple regulated industries
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {['Healthcare', 'Finance', 'Gaming', 'Energy', 'Technology'].map((industry) => (
                  <Badge key={industry} variant="secondary">
                    {industry}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </PageContainer>
    </div>
  );
}
