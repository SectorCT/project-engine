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
        
        # Create .cursorrules file
        cursorrules_content = _generate_cursorrules(has_backend, has_frontend)
        _write_file_to_docker(docker_env, "/app/.cursorrules", cursorrules_content)
        
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


def _generate_cursorrules(has_backend: bool, has_frontend: bool) -> str:
    """Generate .cursorrules file with development guidelines."""
    rules = []
    
    rules.append("# Project Development Rules")
    rules.append("")
    rules.append("## React/Frontend Best Practices")
    rules.append("")
    rules.append("### Component Reusability")
    rules.append("- ALWAYS check if a component already exists before creating a new one")
    rules.append("- Look in src/components/ for reusable components")
    rules.append("- Extract common patterns into reusable components")
    rules.append("- Use composition over duplication")
    rules.append("")
    rules.append("### State Management")
    rules.append("- Use React Context API for shared application state")
    rules.append("- Create context providers in src/contexts/ for data that needs to be accessed across components")
    rules.append("- Use useState for local component state")
    rules.append("- Use useReducer for complex state logic")
    rules.append("- Avoid prop drilling - use context when data needs to pass through multiple levels")
    rules.append("")
    rules.append("### Modern React Patterns")
    rules.append("- Use functional components with hooks")
    rules.append("- Use TypeScript for type safety")
    rules.append("- Follow React best practices: proper key usage, memoization when needed")
    rules.append("- Use custom hooks to extract reusable logic")
    rules.append("- Keep components small and focused (single responsibility)")
    rules.append("")
    rules.append("### Form Handling")
    rules.append("- ALWAYS implement form validation on the frontend")
    rules.append("- Use controlled components for form inputs")
    rules.append("- Validate input before submission")
    rules.append("- Show clear error messages to users")
    rules.append("- Disable submit button while form is invalid")
    rules.append("- Sanitize user input before sending to backend")
    rules.append("- CRITICAL: Password forms on signup MUST include a 'Confirm Password' field (frontend only)")
    rules.append("- CRITICAL: When handling form errors, NEVER allow page refresh that clears form data")
    rules.append("- Handle form state properly: preserve form data on errors, prevent accidental page reloads")
    rules.append("- Use React state to maintain form values even if errors occur")
    rules.append("- Prevent form submission from triggering page refresh (use preventDefault)")
    rules.append("- Show error messages without clearing form inputs")
    rules.append("")
    rules.append("### Data Synchronization")
    rules.append("- ALWAYS refresh/update data after mutations (create, update, delete)")
    rules.append("- After creating new data (e.g., new post), refetch the list to show the new item")
    rules.append("- After updating data, refresh the affected data in the UI")
    rules.append("- After deleting data, remove it from the UI or refetch the list")
    rules.append("- Use React Context or state management to update data across components")
    rules.append("- Don't rely on optimistic updates alone - always verify with server")
    rules.append("")
    rules.append("### API Calls & Fetch Requests")
    rules.append("- CRITICAL: NEVER use fetch() directly in components or pages")
    rules.append("- CRITICAL: ALWAYS create and use a centralized API utility file: src/utils/api.ts")
    rules.append("- All API calls must go through functions in src/utils/api.ts")
    rules.append("- CRITICAL: NEVER use base URL (e.g., http://localhost:5000) in API calls")
    rules.append("- CRITICAL: ALWAYS use relative paths starting with /api/... (e.g., /api/posts, /api/users)")
    rules.append("- Vite configuration automatically proxies /api/* requests to the backend")
    rules.append("- Example: Use fetch('/api/posts') NOT fetch('http://localhost:5000/api/posts')")
    rules.append("- Example api.ts structure:")
    rules.append("  ```typescript")
    rules.append("  // src/utils/api.ts")
    rules.append("  export const getPosts = async () => {")
    rules.append("    const response = await fetch('/api/posts');")
    rules.append("    return response.json();")
    rules.append("  };")
    rules.append("  ```")
    rules.append("- Import and use API functions in components: import { getPosts } from '@/utils/api'")
    rules.append("")
    rules.append("### Page/Route Integration")
    rules.append("- ALWAYS integrate pages into the app structure immediately after creation")
    rules.append("- If creating a page/route component, you MUST:")
    rules.append("  1. Set up routing (add route to router configuration)")
    rules.append("  2. Add navigation (navbar, menu, button, or link to access the page)")
    rules.append("  3. If it's a home/landing page, set it as the default route (/)")
    rules.append("  4. Ensure the page is accessible and visible in the app")
    rules.append("- Never create a page component without integrating it into routing and navigation")
    rules.append("- Check existing routing setup (likely in src/App.tsx or src/main.tsx)")
    rules.append("- If navigation doesn't exist, create it (navbar, menu, etc.)")
    rules.append("")
    rules.append("### Color & Accessibility")
    rules.append("- ALWAYS ensure text is readable with sufficient color contrast")
    rules.append("- Text must be readable in its default state (before hover)")
    rules.append("- NEVER use the same color for background and text (e.g., blue button with blue text)")
    rules.append("- Hover animations should enhance visibility, not fix broken text readability")
    rules.append("- If text color changes on hover, ensure it's readable in BOTH states")
    rules.append("- Use WCAG contrast guidelines: minimum 4.5:1 for normal text, 3:1 for large text")
    rules.append("- Test color combinations to ensure text is always visible and readable")
    rules.append("- Example of BAD: Blue button with blue text that only becomes white on hover")
    rules.append("- Example of GOOD: Blue button with white text (readable in default state)")
    rules.append("")
    
    if has_backend:
        rules.append("## Backend Best Practices")
        rules.append("")
        rules.append("### Data Validation")
        rules.append("- ALWAYS validate all input data on the backend")
        rules.append("- Validate request body, query parameters, and route parameters")
        rules.append("- Use validation middleware or libraries")
        rules.append("- Return clear, specific error messages for validation failures")
        rules.append("- Never trust client-side validation alone")
        rules.append("")
        rules.append("### API Design")
        rules.append("- Use RESTful conventions for API endpoints")
        rules.append("- Return appropriate HTTP status codes")
        rules.append("- Use consistent response formats")
        rules.append("- Implement proper error handling")
        rules.append("")
        rules.append("### Database (MongoDB)")
        rules.append("- ALWAYS use Mongoose for all database interactions")
        rules.append("- Do NOT use the native MongoDB driver")
        rules.append("- Define Mongoose schemas for all data models")
        rules.append("- Use Mongoose models for all CRUD operations")
        rules.append("- Place Mongoose models in server/models/ directory")
        rules.append("- Use Mongoose validation and middleware")
        rules.append("- Use Mongoose connection from mongodb.config.ts")
        rules.append("")
        rules.append("### Authentication & Authorization")
        rules.append("- If an endpoint requires authentication, ALWAYS protect it on the backend")
        rules.append("- Use authentication middleware to protect routes (e.g., verify JWT token)")
        rules.append("- Return 401 Unauthorized if authentication fails")
        rules.append("- CRITICAL: If saving passwords in the database, ALWAYS hash them before storing")
        rules.append("- NEVER store plain text passwords in the database")
        rules.append("- Use bcrypt, argon2, or similar hashing library to hash passwords")
        rules.append("- Hash passwords on the backend before saving to database")
        rules.append("- On the frontend, ALWAYS automatically redirect to login page if authentication is required")
        rules.append("- Check authentication status before making API calls to protected endpoints")
        rules.append("- If API call returns 401, redirect user to login page")
        rules.append("- Use route guards or authentication checks in React components")
        rules.append("- Protect routes that require authentication (redirect if not authenticated)")
        rules.append("")
        rules.append("### Security")
        rules.append("- CRITICAL: If saving passwords, ALWAYS hash them before storing in database")
        rules.append("- NEVER store plain text passwords - use bcrypt, argon2, or similar")
        rules.append("- Hash passwords on the backend before saving to MongoDB")
        rules.append("- Sanitize all user input")
        rules.append("- Use Mongoose schema validation (not parameterized queries)")
        rules.append("- Implement proper authentication and authorization")
        rules.append("- Validate file uploads (type, size, content)")
        rules.append("")
    
    rules.append("## General Development Rules")
    rules.append("")
    rules.append("### Code Quality")
    rules.append("- Write clean, readable, maintainable code")
    rules.append("- Follow TypeScript best practices")
    rules.append("- Use meaningful variable and function names")
    rules.append("- Add comments for complex logic")
    rules.append("- Keep functions small and focused")
    rules.append("")
    rules.append("### File Organization")
    rules.append("- Follow the existing project structure")
    rules.append("- Place components in src/components/")
    rules.append("- Place utilities in src/lib/ or src/utils/")
    rules.append("- Place types/interfaces in appropriate type files")
    rules.append("- Keep related files together")
    rules.append("")
    rules.append("### Error Handling")
    rules.append("- Always handle errors gracefully")
    rules.append("- Provide user-friendly error messages")
    rules.append("- Log errors appropriately for debugging")
    rules.append("- Don't expose sensitive information in error messages")
    rules.append("")
    rules.append("### TODO Comments for Future Implementation")
    rules.append("- If a dependent function or feature is not implemented yet, leave a detailed TODO comment")
    rules.append("- Format: TODO: really detailed description ENDTODO")
    rules.append("- The description should be VERY detailed, explaining:")
    rules.append("  * What needs to be implemented")
    rules.append("  * Why it's needed (context)")
    rules.append("  * What dependencies or prerequisites exist")
    rules.append("  * Any specific requirements or constraints")
    rules.append("- Example: TODO: Implement user authentication middleware. This is needed because the /api/profile endpoint requires authentication. The middleware should check for a JWT token in the Authorization header, verify it using the JWT_SECRET, and attach the user object to req.user. If token is missing or invalid, return 401. ENDTODO")
    rules.append("- After all tickets are completed, the system will automatically parse the project for TODOs and create tickets for them")
    rules.append("")
    rules.append("### Authentication Flow")
    rules.append("- CRITICAL: If there is a login form, the signup function MUST automatically log the user in after successful registration")
    rules.append("- Do NOT redirect to login page after signup - the user should be logged in immediately")
    rules.append("- After signup, set authentication tokens/cookies and update authentication state")
    rules.append("- Redirect to the appropriate page (e.g., dashboard, home) after signup, not to login")
    rules.append("- Example: After successful signup, call login function with the new user credentials, or directly set auth state if signup returns auth tokens")
    rules.append("")
    
    return "\n".join(rules)


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

