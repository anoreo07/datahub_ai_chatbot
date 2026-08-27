# Frontend Improvement Report

**Date**: 2026-08-21
**Baseline**: 661 backend tests pass, TypeScript compiles

---

## Summary

Implemented structured message rendering, clarification UI, error recovery, context bar, evidence panel, and suggestion chips for the DataAtlas chatbot frontend.

---

## 1. Current Frontend Architecture (Before)

### Structure
```
frontend/
  app/(app)/chat/page.tsx     # Simple ChatLayout wrapper
  components/chat/
    chat-layout.tsx           # Main orchestrator (82 lines)
    message-bubble.tsx        # God component (372 lines)
    chat-input.tsx            # Input with slash commands
    markdown.tsx              # Markdown renderer
    lineage-graph.tsx         # SVG lineage visualization
    quality-report-card.tsx   # Quality report card
  lib/
    use-chat.ts               # Chat state management
    types.ts                  # TypeScript interfaces
    stream.ts                 # SSE streaming
    app-store.tsx             # Global state (AppProvider)
```

### Problems Found
1. **MessageBubble is a god component** — handles user messages, assistant messages, citations, entities, lineage, quality reports, suggestions, lightbox, copy button (372 lines)
2. **No structured response rendering** — everything rendered as markdown
3. **No clarification UI** — suggestions rendered as text buttons
4. **No thinking indicator** — just simple dot animation
5. **No evidence/citation side panel** — citations just link to DataHub
6. **No context bar** — no way to see active context
7. **Error messages are dead-ends** — no recovery actions
8. **No entity detail panel** — just links to DataHub

---

## 2. Components/Hooks/Services Created

### New Components
| Component | File | Responsibility |
|-----------|------|----------------|
| `MessageRenderer` | `message-renderer.tsx` | Routes to correct sub-renderer |
| `TextMessage` | `renderers/text-message.tsx` | Plain text/markdown |
| `EntityCard` | `renderers/entity-card.tsx` | Entity result card |
| `ClarificationCard` | `renderers/clarification-card.tsx` | Clarification/suggestion |
| `ErrorCard` | `renderers/error-card.tsx` | Error with recovery actions |
| `ThinkingIndicator` | `renderers/thinking-indicator.tsx` | Process status |
| `EvidenceBlock` | `renderers/evidence-block.tsx` | Citation/evidence |
| `EvidencePanel` | `evidence-panel.tsx` | Side panel for entity details |
| `ContextBar` | `context-bar.tsx` | Active context display |
| `SuggestionChips` | `suggestion-chips.tsx` | Discovery suggestions |

### Modified Components
| Component | Changes |
|-----------|---------|
| `MessageBubble` | Delegates to `MessageRenderer` for assistant messages |
| `ChatLayout` | Added ContextBar, SuggestionChips, EvidencePanel |
| `useChat` | Added activeContext state, new message fields |
| `types.ts` | Added ErrorCode, RecoveryAction, ClarificationCandidate, ActiveContext |

---

## 3. Chat Message Improvements

### Before
- All assistant messages rendered as plain markdown
- Citations just links to DataHub
- Entities just text badges

### After
- **MessageRenderer** routes to appropriate sub-renderer
- **EntityCard** shows entity name, type, platform, domain, description
- **EvidenceBlock** shows citations with entity names
- **ErrorCard** shows error with recovery actions
- **ClarificationCard** shows candidates with confirm/reject buttons

---

## 4. Clarification Improvements

### Before
- SuggestionBox rendered as text with "Đồng ý" button
- Click sends text "đúng rồi" to backend

### After
- **ClarificationCard** shows candidates with:
  - Entity name, type, confidence
  - Description if available
  - [Chọn] button per candidate
  - [Không, tìm cái khác] button
- Structured confirmation flow ready for backend integration

---

## 5. Error Recovery

### Before
- Error messages just displayed as red text
- No recovery actions

### After
- **ErrorCard** with error codes:
  - NOT_FOUND: Search for similar entities
  - AMBIGUOUS: Show candidates
  - INSUFFICIENT_METADATA: Show missing metadata
  - PERMISSION_DENIED: Clear message
  - INTERNAL_ERROR: Retry button
- Recovery actions trigger actual flows

---

## 6. Thinking UI

### Before
- Simple dot animation
- No process status

### After
- **ThinkingIndicator** with:
  - Step-specific icons (Brain, Loader2)
  - Vietnamese step labels
  - Completion state with checkmark

---

## 7. Evidence Side Panel

### Before
- Citations link directly to DataHub

### After
- **EvidencePanel** opens from left side:
  - Entity metadata (platform, domain, description)
  - Schema fields if available
  - Owners if available
  - Tags if available
  - Loading/error states
  - "Mở trong DataHub" button at bottom
  - Escape key closes panel

---

## 8. Context Bar

### Before
- No context display

### After
- **ContextBar** shows active context:
  - Dataset — name ×
  - Domain — name ×
  - Field — name ×
- Updates from backend response
- Remove button per item (ready for backend support)

---

## 9. User Suggestions

### Before
- Hard-coded 4 suggestions

### After
- **SuggestionChips** with:
  - Generic suggestions (search, understand, trace)
  - Context-aware suggestions (when in dataset context)
  - Grouped by category with icons

---

## 10. Backend/API Contract Changes

### New Types Added
```typescript
interface ErrorInfo {
  code: ErrorCode;
  message: string;
  recovery_actions?: RecoveryAction[];
}

interface ClarificationCandidate {
  name: string;
  urn: string;
  entity_type?: string;
  url?: string;
  description?: string;
  confidence?: number;
}

interface ActiveContext {
  items: ActiveContextItem[];
}

interface ActiveContextItem {
  type: "dataset" | "domain" | "field" | "term" | "report" | "dashboard" | "entity";
  name: string;
  urn?: string;
  url?: string;
}
```

### ChatResponse Extended
- `error_info?: ErrorInfo`
- `clarification_candidates?: ClarificationCandidate[]`
- `active_context?: ActiveContext`

---

## 11. Tests

### TypeScript
- `npx tsc --noEmit` — **PASS**

### Backend Regression
- 661 tests — **ALL PASS**

### Manual Verification
- Component renders correctly
- TypeScript compiles without errors
- No broken imports

---

## 12. Limitations

1. **EvidencePanel API** — Backend `/api/v1/entities/{urn}` endpoint not yet implemented; panel falls back to local data
2. **Context removal** — Backend support needed for removing context items
3. **Clarification flow** — Backend structured confirmation API not yet implemented; current flow sends text
4. **Thinking steps** — Backend SSE events not yet extended with detailed step info
5. **No unit tests** — Frontend unit tests not yet created (would need Jest/Vitest setup)

---

## 13. Files Changed

### New Files
- `components/chat/message-renderer.tsx`
- `components/chat/renderers/text-message.tsx`
- `components/chat/renderers/entity-card.tsx`
- `components/chat/renderers/clarification-card.tsx`
- `components/chat/renderers/error-card.tsx`
- `components/chat/renderers/thinking-indicator.tsx`
- `components/chat/renderers/evidence-block.tsx`
- `components/chat/evidence-panel.tsx`
- `components/chat/context-bar.tsx`
- `components/chat/suggestion-chips.tsx`

### Modified Files
- `lib/types.ts` — Added ErrorInfo, RecoveryAction, ClarificationCandidate, ActiveContext
- `lib/use-chat.ts` — Added activeContext state, new message fields
- `components/chat/message-bubble.tsx` — Delegates to MessageRenderer
- `components/chat/chat-layout.tsx` — Added ContextBar, SuggestionChips, EvidencePanel

---

## 14. Architecture Principles Followed

- ✅ UI components only render/presentation
- ✅ Hooks manage interaction/state
- ✅ Services manage API
- ✅ Domain logic not in JSX
- ✅ No duplicate fetch logic
- ✅ No duplicate normalization
- ✅ No god components
- ✅ Types shared for backend/frontend contract
  - State has single source of truth (useChat hook)
- ✅ No circular dependency
- ✅ No hard-coding per dataset/test case
- ✅ Existing capabilities preserved (SSE streaming, citation, lineage, SQL, image, thinking)
