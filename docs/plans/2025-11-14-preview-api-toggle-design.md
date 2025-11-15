# Preview API Toggle Design

**Goal:** Add settings dialog to frontend allowing users to switch between production and preview APIs.

**Architecture:** Settings modal with toggle switch. Custom React hook manages API endpoint selection via localStorage. Preview badge appears in header when active.

**Tech Stack:** React, TypeScript, Radix UI Dialog/Switch, localStorage

---

## Components

### 1. useApiConfig Hook (`src/hooks/useApiConfig.ts`)

Custom hook managing API endpoint selection.

**Exports:**
```typescript
{
  apiUrl: string;           // Current endpoint URL
  isPreview: boolean;       // Preview mode state
  togglePreview: () => void; // Toggle function
}
```

**Implementation:**
- Reads `oews-preview-mode` from localStorage on mount
- Returns production or preview URL based on state
- Provides toggle function that updates localStorage and state

**API URLs:**
```typescript
const API_CONFIG = {
  production: 'https://api.oews.bhavanaai.com/api/v1/query',
  preview: 'https://api.oews.bhavanaai.com/trace/api/v1/query'
};
```

### 2. SettingsDialog Component (`src/components/SettingsDialog.tsx`)

Modal dialog with preview mode toggle.

**Props:**
```typescript
{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isPreview: boolean;
  onTogglePreview: () => void;
  currentEndpoint: string;
}
```

**UI Structure:**
- Dialog title: "Settings"
- Section: "API Settings"
- Switch: "Enable Preview Mode"
- Description: "Preview mode uses experimental features being tested before general release"
- Current endpoint display (small gray text)

**Behavior:**
- Opens/closes via Dialog state
- Switch toggles preview mode immediately
- No explicit save button (auto-saves to localStorage)

### 3. Header Component Updates (`src/components/Header.tsx`)

Add gear icon button and preview badge.

**New Elements:**
- Settings button (gear icon) - opens SettingsDialog
- Preview badge (when `isPreview` is true)

**Layout:**
```
[OEWS Data Explorer] [Preview Badge*] ... [Settings Icon] [Feedback] [Employment & Wage Statistics]
```

*Badge only visible when preview mode active

**Badge Styling:**
- Small rounded chip
- Amber/orange background
- Text: "Preview"
- Positioned next to title

### 4. App Component Updates (`src/App.tsx`)

Replace hardcoded API_URL with hook.

**Changes:**
- Import and use `useApiConfig` hook
- Pass `apiUrl` from hook to fetch calls
- Pass `isPreview` to Header for badge display
- Manage SettingsDialog open/close state

---

## User Flow

1. User clicks gear icon in header
2. Settings dialog opens
3. User sees current mode (production/preview)
4. User toggles "Enable Preview Mode" switch
5. localStorage updates immediately
6. Dialog closes (or stays open)
7. Preview badge appears in header
8. Next query uses preview endpoint
9. User sees execution trace data in results

---

## Implementation Tasks

1. Create `useApiConfig` hook
2. Create `SettingsDialog` component
3. Update `Header` component (add gear icon + badge)
4. Update `App` component (use hook, manage dialog state)
5. Test toggle functionality
6. Test localStorage persistence
7. Verify both endpoints work correctly

---

## Success Criteria

- Settings icon appears in header
- Clicking icon opens settings dialog
- Toggle switch changes API endpoint
- Preview badge appears when preview mode active
- Settings persist across page refreshes
- Both production and preview APIs work correctly
- Clean UI that matches existing design

---

## Future Extensions

Settings dialog structure supports adding:
- Theme selection (light/dark mode)
- Default chart preferences
- Query history settings
- Advanced API options (timeout, model selection)
