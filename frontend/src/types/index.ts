// ============================================================================
// TYPE DEFINITIONS - Extracted from App.tsx for better organization
// ============================================================================

import React from 'react';

// View Types
export type View = 'landing' | 'selection' | 'wall';
export type ActiveTab = 'dashboard' | 'strategy' | 'drafting';
export type ToolId = 'research' | 'vault' | 'remove' | null;
export type AnalyticsMode = 'judge' | 'devils';

// Devil's Advocate Types
export type DevilsAdvocateAttackPoint = {
  title?: string;
  weakness?: string;
  counter_citation?: string;
  suggested_attack?: string;
  raw?: string;
};

export type DevilsAdvocateResponse = {
  attack_points: DevilsAdvocateAttackPoint[];
  vulnerability_score: number;
  preparation_recommendations: string[];
};

// Case Data
export type CaseData = {
  id: number;
  title: string;
  type: string;
  date: string;
  status: string;
};

// Node Types
export type NodeStatus = 'Verified' | 'Pending' | 'Contested';
export type NodeType = 'Evidence' | 'Precedent' | 'Statement' | 'Strategy';

export type NodeData = {
  id: number;
  title: string;
  type: NodeType;
  date: string;
  status: NodeStatus;
  x: number;
  y: number;
  rotation: number;
  pinColor: 'red' | 'blue' | 'green' | 'yellow';
  source?: string;
  attachments?: Array<{
    name: string;
    kind: 'photo' | 'video' | 'audio' | 'document' | 'other';
    sizeBytes?: number;
    url?: string;
  }>;
};

export type Connection = {
  from: number;
  to: number;
  label: string;
  type: 'conflict' | 'normal' | 'suggested';
  reason?: string;
  confidence?: number;
};

// Wall Analysis Types
export type WallInsightSeverity = 'low' | 'medium' | 'high';

export type WallAnalyzeResponse = {
  summary: string;
  insights: Array<{ title: string; detail: string; severity: WallInsightSeverity; node_ids: string[] }>;
  suggested_links: Array<{ source: string; target: string; label: string; confidence: number; reason?: string }>;
  next_actions: string[];
};

// Chat Types
export type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  hasConflict?: boolean;
  conflictDetail?: string;
  preservedTerms?: string[];
};

// Icon and UI Types
export type IconLike = React.ComponentType<{ size?: string | number; strokeWidth?: string | number }>;

export type CourtValue =
  | 'supreme_court'
  | 'high_court'
  | 'district_court'
  | 'tribunal'
  | 'other';

// Document Types
export type DocumentTemplate = {
  id: string;
  name: string;
  description: string;
};

export type FormattingRules = {
  court: string;
  font_family: string;
  font_size: number;
  line_spacing: number;
  margins: { top: number; bottom: number; left: number; right: number };
  paragraph_indent: number;
  page_numbering: string;
};

// Shepardizing Types
export type ShepardizeStatus = 'good_law' | 'distinguished' | 'overruled' | 'unknown';
export type ShepardizeResult = {
  status: ShepardizeStatus;
  status_emoji?: string;
  message?: string;
};

// Judge Analytics Types
export type JudgeAnalyticsPattern = {
  pattern: string;
  signal: 'low' | 'medium' | 'high';
  evidence: string[];
  caveats: string[];
};

export type JudgeAnalyticsResponse = {
  judge_name: string;
  total_cases_analyzed: number;
  patterns: JudgeAnalyticsPattern[];
  recommendations: string[];
};
