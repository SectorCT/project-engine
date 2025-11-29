from typing import Dict, List
from systems.docker_env import DockerEnv

class ProjectInitializer:
    """
    Utility system (NOT an agent) for project initialization.
    Two steps:
    1. get_project_structure() - Returns structure definition (runs before PM)
    2. init_project() - Actually creates files in Docker (runs during build)
    """
    
    @staticmethod
    def get_project_structure(has_backend: bool, has_frontend: bool) -> Dict:
        """
        Step 1: Get project structure definition.
        Returns a data structure describing folders and files that will exist.
        Does NOT create files - just returns the structure.
        
        Args:
            has_backend: Whether backend (Express.js + TypeScript) is needed
            has_frontend: Whether frontend (Vite + React + TypeScript) is needed
            
        Returns:
            Dict with folder structure, known files, and tech stack info
        """
        folders = []
        known_files = []
        
        # Root level files
        known_files.extend([
            "package.json",
            "tsconfig.json",
            ".gitignore",
            "README.md"
        ])
        
        if has_frontend:
            folders.extend([
                "src/",
                "src/components/",
                "src/pages/",
                "src/utils/",
                "src/types/",
                "public/",
            ])
            known_files.extend([
                "vite.config.ts",
                "index.html",  # Vite expects index.html in root, not public/
                "src/main.tsx",
                "src/App.tsx",
                "src/index.css",
            ])
        
        if has_backend:
            folders.extend([
                "server/",
                "server/routes/",
                "server/middleware/",
                "server/utils/",
                "server/types/",
            ])
            known_files.extend([
                "server/index.ts",
                "server/cors.ts",  # Pre-configured CORS
                "server/tsconfig.json",
            ])
        
        # Common folders
        folders.extend([
            "tests/",
        ])
        
        return {
            "folders": sorted(set(folders)),
            "known_files": sorted(set(known_files)),
            "tech_stack": {
                "frontend": "Vite + React + TypeScript" if has_frontend else None,
                "backend": "Express.js + TypeScript + CORS" if has_backend else None,
            },
            "has_backend": has_backend,
            "has_frontend": has_frontend
        }
    
    @staticmethod
    def init_project(structure: Dict, docker_env: DockerEnv):
        """
        Step 2: Initialize project in Docker container.
        Actually creates the folder structure and files.
        
        Args:
            structure: Structure dict from get_project_structure()
            docker_env: DockerEnv instance for executing commands
        """
        print("Initializing project structure in Docker container...")
        
        # Create folders
        folders = structure.get("folders", [])
        for folder in folders:
            # Remove trailing slash for mkdir
            folder_clean = folder.rstrip('/')
            cmd = f'bash -c "mkdir -p /app/{folder_clean}"'
            docker_env.exec_run(cmd, workdir="/app")
        
        # Create package.json
        has_backend = structure.get("has_backend", False)
        has_frontend = structure.get("has_frontend", False)
        
        package_json_content = _generate_package_json(has_backend, has_frontend)
        _write_file_to_docker(docker_env, "/app/package.json", package_json_content)
        
        # Create root tsconfig.json
        root_tsconfig = _generate_root_tsconfig()
        _write_file_to_docker(docker_env, "/app/tsconfig.json", root_tsconfig)
        
        # Create .gitignore
        gitignore_content = _generate_gitignore()
        _write_file_to_docker(docker_env, "/app/.gitignore", gitignore_content)
        
        # Create README.md
        readme_content = _generate_readme(has_backend, has_frontend)
        _write_file_to_docker(docker_env, "/app/README.md", readme_content)
        
        if has_frontend:
            _init_frontend(docker_env, structure)
        
        if has_backend:
            _init_backend(docker_env, structure)
        
        print("Project structure initialized successfully.")
    
    @staticmethod
    def get_structure_summary(structure: Dict) -> str:
        """
        Get a human-readable summary of the project structure for PM agent context.
        """
        lines = [
            "Project Structure:",
            f"- Frontend: {structure['tech_stack']['frontend'] or 'None'}",
            f"- Backend: {structure['tech_stack']['backend'] or 'None'}",
            "",
            "Folders:",
        ]
        for folder in structure.get("folders", []):
            lines.append(f"  - {folder}")
        lines.append("")
        lines.append("Known Files:")
        for file in structure.get("known_files", []):
            lines.append(f"  - {file}")
        
        return "\n".join(lines)


def _write_file_to_docker(docker_env: DockerEnv, filepath: str, content: str):
    """Helper to write a file to Docker container."""
    import base64
    import uuid
    # Generate a unique delimiter to avoid conflicts
    delimiter = f"EOF_{uuid.uuid4().hex[:8]}"
    # Encode content as base64 to avoid shell escaping issues
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
    # Use Python to decode and write - most reliable
    python_cmd = f"python3 -c \"import base64; open('{filepath}', 'w').write(base64.b64decode('{content_b64}').decode('utf-8'))\""
    docker_env.exec_run(python_cmd, workdir="/app")


def _generate_package_json(has_backend: bool, has_frontend: bool) -> str:
    """Generate package.json with appropriate scripts and dependencies."""
    scripts = {}
    dependencies = {}
    dev_dependencies = {
        "typescript": "^5.0.0",
        "@types/node": "^20.0.0",
    }
    
    if has_frontend:
        scripts.update({
            "dev": "vite",
            "build": "tsc && vite build",
            "preview": "vite preview",
        })
        dependencies.update({
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
        })
        dev_dependencies.update({
            "@vitejs/plugin-react": "^4.0.0",
            "@types/react": "^18.2.0",
            "@types/react-dom": "^18.2.0",
            "vite": "^5.0.0",
        })
    
    if has_backend:
        scripts.update({
            "server": "tsx server/index.ts",
            "server:dev": "tsx watch server/index.ts",
        })
        dependencies.update({
            "express": "^4.18.0",
            "cors": "^2.8.5",
        })
        dev_dependencies.update({
            "@types/express": "^4.17.0",
            "@types/cors": "^2.8.0",
            "tsx": "^4.0.0",
        })
    
    scripts["test"] = "echo 'Tests not yet configured'"
    
    import json
    package_data = {
        "name": "project",
        "version": "1.0.0",
        "type": "module",
        "scripts": scripts,
        "dependencies": dependencies,
        "devDependencies": dev_dependencies,
    }
    return json.dumps(package_data, indent=2)


def _generate_root_tsconfig() -> str:
    """Generate root tsconfig.json."""
    return '''{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true
  },
  "include": ["src", "server"],
  "exclude": ["node_modules", "dist"]
}'''


def _generate_gitignore() -> str:
    """Generate .gitignore."""
    return '''node_modules/
dist/
build/
.env
.env.local
*.log
.DS_Store
coverage/
.idea/
.vscode/
'''


def _generate_readme(has_backend: bool, has_frontend: bool) -> str:
    """Generate README.md."""
    parts = ["# Project", "", "## Tech Stack"]
    if has_frontend:
        parts.append("- Frontend: Vite + React + TypeScript")
    if has_backend:
        parts.append("- Backend: Express.js + TypeScript + CORS")
    parts.append("")
    parts.append("## Scripts")
    parts.append("- `npm run dev` - Start development server (frontend)")
    if has_backend:
        parts.append("- `npm run server:dev` - Start backend server in watch mode")
    parts.append("- `npm run build` - Build for production")
    parts.append("- `npm test` - Run tests")
    return "\n".join(parts)


def _init_frontend(docker_env: DockerEnv, structure: Dict):
    """Initialize frontend files."""
    # vite.config.ts
    vite_config = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Bind to all interfaces so it's accessible from outside container
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
'''
    _write_file_to_docker(docker_env, "/app/vite.config.ts", vite_config)
    
    # src/main.tsx
    main_tsx = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''
    _write_file_to_docker(docker_env, "/app/src/main.tsx", main_tsx)
    
    # src/App.tsx
    app_tsx = '''import React from 'react'

function App() {
  return (
    <div>
      <h1>Welcome</h1>
    </div>
  )
}

export default App
'''
    _write_file_to_docker(docker_env, "/app/src/App.tsx", app_tsx)
    
    # src/index.css
    index_css = '''* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
'''
    _write_file_to_docker(docker_env, "/app/src/index.css", index_css)
    
    # index.html - Vite expects this in the ROOT, not in public/
    # The public/ folder is for static assets (images, favicons, etc.)
    index_html = '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Project</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'''
    _write_file_to_docker(docker_env, "/app/index.html", index_html)


def _init_backend(docker_env: DockerEnv, structure: Dict):
    """Initialize backend files."""
    # server/tsconfig.json
    server_tsconfig = '''{
  "extends": "../tsconfig.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./",
    "module": "CommonJS",
    "target": "ES2020",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "strict": true,
    "resolveJsonModule": true
  },
  "include": ["./**/*"],
  "exclude": ["node_modules", "dist"]
}
'''
    _write_file_to_docker(docker_env, "/app/server/tsconfig.json", server_tsconfig)
    
    # server/cors.ts (pre-configured CORS)
    cors_ts = '''import cors from 'cors';
import { Express } from 'express';

export function setupCors(app: Express) {
  app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
  }));
}
'''
    _write_file_to_docker(docker_env, "/app/server/cors.ts", cors_ts)
    
    # server/index.ts
    server_index = '''import express from 'express';
import { setupCors } from './cors';

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(express.json());
setupCors(app);

// Routes
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
'''
    _write_file_to_docker(docker_env, "/app/server/index.ts", server_index)

