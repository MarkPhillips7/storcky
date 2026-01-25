# Storcky

Interactive animations of financial data for stocks. Storcky is a play on the words "stock story."

## Tech Stack

- **Frontend**: Next.js 14+ with TypeScript, React
- **Database**: Convex
- **Auth**: Clerk
- **Styling**: Tailwind CSS + ShadCN
- **Visualization**: GSAP, D3, d3-sankey-diagram
- **Backend API**: FastAPI (Python) with EdgarTools
- **Monorepo**: TurboRepo
- **Package Manager**: pnpm

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm 8+
- Python 3.9+ (Python 3.10+ recommended for latest edgartools features)

### Installation

1. Install dependencies:
```bash
pnpm install
```

2. Set up environment variables:
- Copy `.env.example` files in `apps/web` and `apps/api`
- Configure Clerk, Convex, and API URLs

3. Install Python dependencies:
```bash
cd apps/api && pip3 install -r requirements.txt
```

4. Start development servers:
```bash
pnpm dev
```

This will start:
- Next.js app on http://localhost:3000
- FastAPI service on http://localhost:8000

## Project Structure

```
storcky/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
└── packages/
    └── shared/       # Shared types
```

## Development

- `pnpm dev` - Start all development servers
- `pnpm build` - Build all apps
- `pnpm lint` - Lint all apps
