# Project-Engine Client

Frontend application for Project-Engine - an AI-powered autonomous software development platform.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Framer Motion** - Animation library
- **React Router** - Client-side routing
- **TanStack Query** - Server state management
- **Shadcn UI** - UI component library
- **Radix UI** - Headless UI primitives

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The development server will start on `http://localhost:8080`

## Project Structure

```
client/
├── public/              # Static assets
├── src/
│   ├── components/      # React components
│   │   ├── ui/         # Shadcn UI components
│   │   ├── build/      # Build view components
│   │   ├── NavLink.tsx
│   │   └── ProjectCard.tsx
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utility functions
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── vite.config.ts
```

## Features

- User authentication UI
- Project dashboard with filtering and search
- Multi-step project creation wizard
- Real-time live build view with 4-panel layout
- Agent communication visualization
- Live preview of applications being built
- Architecture and file tree visualization
- Status tracking and metrics

## Design System

The application uses a custom design system with:
- Dark theme with electric blue primary color
- Glassmorphism effects
- Smooth animations
- Responsive design (mobile-first)

See `src/index.css` for all design tokens and CSS variables.

## Development

### Adding New Components

Components should be placed in `src/components/` and follow the existing patterns.

### Styling

- Use Tailwind CSS utility classes
- Use semantic color tokens from the design system
- Follow the mobile-first responsive approach

### TypeScript

All components should be typed with TypeScript interfaces. Avoid using `any` types.

## License

Part of the Project-Engine project.

