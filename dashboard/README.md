# Nevron Dashboard

Web-based monitoring UI for the Nevron AI agent framework.

## Tech Stack

- **Framework**: SvelteKit 5
- **Styling**: Tailwind CSS (dark theme)
- **Language**: TypeScript
- **Build**: Vite

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Development

The dashboard connects to the FastAPI backend at `http://localhost:8000`.

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server (port 5173) |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |

### Project Structure

```
src/
├── lib/
│   ├── api/
│   │   └── client.ts      # REST + WebSocket client
│   ├── stores/
│   │   └── websocket.ts   # WebSocket state management
│   └── components/
│       ├── Sidebar.svelte
│       ├── Header.svelte
│       ├── Card.svelte
│       ├── StatCard.svelte
│       └── EventFeed.svelte
└── routes/
    ├── +layout.svelte     # Main layout with sidebar
    ├── +page.svelte       # Dashboard home
    ├── agent/
    │   └── +page.svelte   # Agent control
    ├── runtime/
    │   └── +page.svelte   # Runtime monitor
    ├── memory/
    │   └── +page.svelte   # Memory explorer
    ├── learning/
    │   └── +page.svelte   # Learning insights
    └── mcp/
        └── +page.svelte   # MCP manager
```

## API Endpoints

The dashboard uses these API endpoints:

- `GET /api/v1/agent/status` - Agent state
- `GET /api/v1/runtime/statistics` - Runtime stats
- `GET /api/v1/memory/statistics` - Memory stats
- `GET /api/v1/learning/statistics` - Learning stats
- `GET /api/v1/mcp/servers` - MCP servers
- `WS /ws/{client_id}` - Real-time events

## Environment Variables

Create `.env` file:

```bash
PUBLIC_API_URL=http://localhost:8000
```

## Running with API

From the project root:

```bash
# Option 1: Both together
make dev

# Option 2: Separate terminals
make api        # Terminal 1
make dashboard  # Terminal 2
```

## Docker

```bash
# From project root
make docker-up
```

Dashboard available at http://localhost:3000
