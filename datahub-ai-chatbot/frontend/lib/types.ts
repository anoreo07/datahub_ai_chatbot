export interface User {
  username: string;
  display_name?: string;
  roles: string[];
  is_admin: boolean;
  token?: string;
}

export interface LoginResponse {
  token: string;
  username: string;
  display_name?: string;
  roles: string[];
  is_admin: boolean;
}

export interface CitationItem {
  id: string;
  entity_name?: string;
  url?: string;
}

export interface EntityItem {
  urn: string;
  name: string;
  url?: string;
}

export interface Suggestion {
  original: string;
  suggested: string;
}

export interface LineageNode {
  name: string;
  urn: string;
  url?: string;
  entity_type?: string;
}

export interface LineageData {
  entity_name: string;
  entity_urn: string;
  entity_url?: string;
  upstreams: LineageNode[];
  downstreams: LineageNode[];
}

export interface ChatResponse {
  answer: string;
  intent?: string;
  entities?: EntityItem[];
  citations?: CitationItem[];
  confidence?: string;
  ambiguous?: boolean;
  insufficient_context?: boolean;
  trace_id?: string;
  conversation_id?: string;
  lineage?: LineageData;
  suggestion?: Suggestion;
}

export interface SearchItem {
  urn: string;
  entity_type: string;
  name: string;
  score: number;
  snippet: string;
  datahub_url?: string;
}

export interface SearchResponse {
  results: SearchItem[];
  total: number;
}

export interface StatsResponse {
  dataset: number;
  dashboard: number;
  glossary_term: number;
  document: number;
  total: number;
}

export interface GlossaryTerm {
  urn: string;
  name: string;
  domain?: string;
  description?: string;
}

export interface SchemaMatchItem {
  urn: string;
  name: string;
  description?: string;
  platform?: string;
  domain?: string;
  url?: string;
  similarity: number;
  matched_columns: string[];
  missing_columns: string[];
  additional_columns: string[];
}

export interface SchemaCompareResponse {
  candidates: SchemaMatchItem[];
  total: number;
}

export interface SqlJoin {
  table: string;
  column: string;
  reason?: string;
}

export interface SqlResponse {
  dataset?: string;
  urn?: string;
  selected_columns: string[];
  unavailable_columns: string[];
  sql: string;
  joins: SqlJoin[];
  explanation: string[];
  valid: boolean;
}

export interface ImpactItem {
  urn: string;
  name: string;
  url?: string;
  kind: string;
}

export interface ImpactResponse {
  dataset?: string;
  urn?: string;
  affected_datasets: ImpactItem[];
  affected_dashboards: ImpactItem[];
  affected_pipelines: ImpactItem[];
  affected_jobs: ImpactItem[];
  business_impact: string[];
  risk_level: string;
  valid: boolean;
}

export interface QualityDimension {
  key: string;
  label: string;
  score: number;
  status: string;
  detail: string;
}

export interface QualityResponse {
  dataset?: string;
  urn?: string;
  dimensions: QualityDimension[];
  overall_score: number;
  highlights: string[];
  recommendations: string[];
  valid: boolean;
}

export interface ReportSection {
  title: string;
  lines: string[];
}

export interface ReportAssessment {
  dimension: string;
  score: number;
  rating: string;
  stars: number;
}

export interface ReportResponse {
  dataset?: string;
  urn?: string;
  sections: ReportSection[];
  assessment: ReportAssessment[];
  overall_score: number;
  overall_rating: string;
  recommendations: string[];
  valid: boolean;
}

export interface HealthService {
  [key: string]: string;
}

export interface HealthResponse {
  status: string;
  services: HealthService;
}

export interface HealthLog {
  timestamp: string;
  status: string;
  duration_ms?: number;
  services: HealthService;
}

export interface StreamEvent {
  event: "status" | "token" | "done" | "error";
  data: unknown;
}