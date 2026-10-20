// Friendly aliases over the types generated from the backend's OpenAPI schema
// (regenerate with `npm run gen:types`).
import type { components } from "./api.gen";

type S = components["schemas"];

export type IntegrationGuide = S["IntegrationGuide"];
export type GuideResponse = S["GuideResponse"];
export type GuideSummary = S["GuideSummary"];
export type GuideList = S["GuideList"];
export type ChecklistProgress = S["ChecklistProgress"];
export type Claim = S["Claim"];
export type Source = S["Source"];
export type SetupStep = S["SetupStep"];
export type ApprovalItem = S["ApprovalItem"];
export type ExternalWait = S["ExternalWait"];
export type PathOption = S["PathOption"];
export type ScopePermission = S["ScopePermission"];
export type BlockerOrUnknown = S["BlockerOrUnknown"];
export type VerificationReport = S["VerificationReport"];

export type ClaimStatus = S["ClaimStatus"];
export type ApprovalStatus = S["ApprovalStatus"];
export type ApprovalKind = S["ApprovalKind"];
export type AuthenticationModel = S["AuthenticationModel"];
export type IntegrationContext = S["IntegrationContext"];
export type ExternalWaitKind = S["ExternalWaitKind"];
export type Responsible = S["Responsible"];
export type StepPhase = S["StepPhase"];
export type SourceType = S["SourceType"];
export type RetrievalStatus = S["RetrievalStatus"];
export type ScopeSensitivity = S["ScopeSensitivity"];

export type ResearchRun = S["ResearchRunOut"];
export type ResearchEvent = S["ResearchEvent"];
export type ResearchSourceEntry = S["ResearchSourceEntry"];
export type ResearchStarted = S["ResearchStarted"];
export type ResearchRequest = S["ResearchRequest"];

export type LLMConfigStatus = S["LLMConfigStatus"];
export type LLMTestResult = S["LLMTestResult"];
export type ProvidersResponse = S["ProvidersResponse"];
export type ProviderOption = S["ProviderOption"];
export type ModelsResponse = S["ModelsResponse"];

export type ChatResponse = S["ChatResponse"];
export type ChatTurn = S["ChatTurn"];
