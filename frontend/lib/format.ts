import type {
  ApprovalKind,
  ApprovalStatus,
  AuthenticationModel,
  ClaimStatus,
  ExternalWaitKind,
  IntegrationContext,
  Responsible,
  RetrievalStatus,
  ScopeSensitivity,
  SourceType,
  StepPhase,
} from "@/types";

export const AUTH_LABEL: Record<AuthenticationModel, string> = {
  oauth2: "OAuth 2.0",
  oauth1: "OAuth 1.0a",
  api_key: "API key",
  other: "Other",
  unknown: "Unknown",
};

export const CONTEXT_LABEL: Record<IntegrationContext, string> = {
  personal: "Personal tool",
  internal: "Internal company tool",
  multi_tenant_saas: "Multi-user SaaS",
};

export const CONTEXT_HELP: Record<IntegrationContext, string> = {
  personal: "Only your own account connects",
  internal: "People inside one organization connect",
  multi_tenant_saas: "Any customer's users connect",
};

export const CLAIM_STATUS_LABEL: Record<ClaimStatus, string> = {
  tested: "Tested",
  cross_checked: "Cross-checked",
  officially_documented: "Documented",
  inferred: "Inferred",
  estimated: "Estimated",
  unknown: "Unknown",
};

export const CLAIM_STATUS_HELP: Record<ClaimStatus, string> = {
  tested: "Observed by an automated request we actually made (e.g. a live OAuth discovery document).",
  cross_checked: "The supporting quote was found in two or more retrieved pages.",
  officially_documented: "The supporting quote was found verbatim in a retrieved official page.",
  inferred: "Model or curator judgment without a verified quote in an official source.",
  estimated: "An estimate (e.g. hands-on effort), not a measurement.",
  unknown: "The sources we checked did not answer this.",
};

export const APPROVAL_LABEL: Record<ApprovalStatus, string> = {
  required: "Required",
  not_required: "Not required",
  conditional: "Conditional",
  unclear: "Unclear",
};

export const APPROVAL_KIND_LABEL: Record<ApprovalKind, string> = {
  app_registration: "App registration",
  user_consent: "User consent",
  admin_consent: "Admin consent",
  provider_verification: "Provider verification",
  marketplace_listing: "Marketplace listing",
  production_access: "Production access",
};

export const WAIT_LABEL: Record<ExternalWaitKind, string> = {
  none: "No wait",
  known: "Documented",
  estimated: "Estimated",
  unknown: "Unknown",
};

export const RESPONSIBLE_LABEL: Record<Responsible, string> = {
  agent: "Agent",
  developer: "Developer",
  developer_with_agent: "Developer + agent",
  provider: "Provider",
  workspace_admin: "Workspace admin",
  end_user: "End user",
};

export const PHASE_LABEL: Record<StepPhase, string> = {
  prerequisites: "Prerequisites",
  registration: "Registration",
  credentials: "Credentials & redirects",
  scopes: "Scopes",
  implementation: "Implementation",
  testing: "Testing",
  verification: "Verification",
  distribution: "Distribution",
  launch: "Launch",
};

export const SOURCE_TYPE_LABEL: Record<SourceType, string> = {
  official_docs: "Official docs",
  official_api_reference: "API reference",
  official_policy: "Official policy",
  official_support: "Official support",
  provider_metadata: "Provider metadata",
  secondary: "Secondary",
};

export const RETRIEVAL_LABEL: Record<RetrievalStatus, string> = {
  retrieved: "Retrieved",
  snippet_only: "Snippet only",
  failed: "Failed",
  blocked: "Blocked",
  not_attempted: "Not attempted",
};

export const SENSITIVITY_LABEL: Record<ScopeSensitivity, string> = {
  basic: "Basic",
  sensitive: "Sensitive",
  restricted: "Restricted",
  admin: "Admin",
  unknown: "Unclassified",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", { year: "numeric", month: "short", day: "numeric" }).format(new Date(value));
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatHours(low: number, high: number): string {
  if (low === 0 && high === 0) return "Not estimated";
  const fmt = (h: number) => (h < 1 ? `${Math.round(h * 60)} min` : `${Number.isInteger(h) ? h : h.toFixed(1)} h`);
  return `${fmt(low)} – ${fmt(high)}`;
}

export function formatMinutes(minutes: number | null | undefined): string | null {
  if (minutes == null) return null;
  if (minutes < 60) return `~${minutes} min`;
  const hours = minutes / 60;
  return `~${Number.isInteger(hours) ? hours : hours.toFixed(1)} h`;
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
