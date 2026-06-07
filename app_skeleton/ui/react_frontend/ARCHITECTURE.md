# OMEIA React Frontend — Project Structure

Feature-based layout (inspired by [Bulletproof React](https://github.com/alan2207/bulletproof-react) / feature-sliced design).

## Top-level `src/`

| Path | Purpose |
|------|---------|
| `app/` | App shell, screen registry, global providers |
| `pages/` | Route-level views (one per nav `screen` key) |
| `features/` | Domain modules (UI + hooks co-located per feature) |
| `shared/` | Cross-feature layout, UI primitives, hooks |
| `services/` | API clients, fetch wrappers, React Query hooks |
| `lib/` | Pure utilities (no React) |
| `config/` | Navigation, Firebase, static config |
| `contexts/` | React context providers |
| `data/` | Static catalogs, seed JSON, fallbacks |
| `i18n/` | Locale strings and `useGuiT` |
| `styles/` | Global theme tokens and consistency CSS |
| `assets/` | Static images referenced by bundler |

## `features/` domains

```
features/
  ai-assistant/     Chat copilot, agent categories, 3D hero
  auth/             Login panels and scenes
  computational/    Hub onboarding, pipeline 3D
  documents/        Viewers, formatters, lab document browsers
  imaging/          Tile viewer widgets
  lab/              Lab roster, corpus, wet-lab browsers
  orders/           Orders space and billing browsers
  overview/         Overview intro and social panels
  projects/         Portfolio, workspace, digital twin UI
  search/           Unified search overlay and filters
  storage/          Data & storage document tabs
  taskpad/          Taskpad sheet widget
```

Each feature may contain:

- `components/` — feature-specific React components
- `hooks/` — feature-specific hooks (optional)
- `styles/` — feature CSS (optional)
- `index.js` — public barrel exports (optional)

## `shared/` layers

```
shared/
  layout/     Sidebar, ModuleShell, ErrorBoundary, cover cards
  ui/         Small reusable widgets (badges, links, common/)
  hooks/      Generic hooks (chat scroll, catalog preview, …)
```

## Import aliases (Vite + jsconfig)

Use `@/` paths instead of deep relatives:

```js
import ChatWidget from '@/features/ai-assistant/components/ChatWidget.jsx';
import { apiFetch } from '@/services/client.js';
import { mergeProjectRecord } from '@/lib/projectUtils.js';
import ProjectsScreen from '@/pages/ProjectsScreen.jsx';
import Sidebar from '@/shared/layout/Sidebar.jsx';
```

## Routing

Navigation is **not** React Router. `config/navigation.js` maps sidebar items → `screen` string; `app/screenRegistry.js` (or `App.jsx`) lazy-loads the matching `pages/*` module.

## Adding a new feature

1. Create `features/<name>/components/`.
2. Add API calls in `services/<name>Client.js` if needed.
3. Add a page under `pages/` and register in `config/navigation.js` + screen registry.
4. Export public API from `features/<name>/index.js` if other features need it.
