from agents.base_agent import BaseAgent
from systems.docker_env import DockerEnv
import time
import re
import base64

class CoderAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are an expert Software Engineer (Coder Agent).
Your task is to implement features and fix bugs based on ticket descriptions.
You work inside a Docker container and use the 'cursor-agent' CLI to make changes.
You are pragmatic, clean, and efficient.
"""
        super().__init__(
            name="Coder",
            role="Software Engineer",
            system_prompt=system_prompt
        )
        self.cursor_agent_path = "cursor-agent"  # Default, will be updated if needed

    def _needs_design_decision(self, ticket_title: str, description: str) -> bool:
        """Check if ticket requires a design decision (colors, fonts, layout, etc.)"""
        design_keywords = [
            'color', 'palette', 'typography', 'font', 'layout', 'design',
            'style', 'theme', 'choose', 'select', 'define', 'establish',
            'guidelines', 'structure', 'wireframe', 'mockup'
        ]
        text = (ticket_title + " " + description).lower()
        return any(keyword in text for keyword in design_keywords)

    def _build_enhanced_prompt(self, ticket: dict, parent_context: str = None, 
                               project_structure: dict = None, all_tickets: list = None,
                               dependencies: list = None, completed_tickets: list = None) -> str:
        """Build an enhanced prompt with full project context."""
        task_description = ticket.get('description', '')
        ticket_title = ticket.get('title', '')
        ticket_id = ticket.get('_id') or ticket.get('id', '')
        
        # Check if this needs a design decision
        needs_design = self._needs_design_decision(ticket_title, task_description)
        
        prompt_parts = [
            "=" * 80,
            "PROJECT CONTEXT AND TASK",
            "=" * 80,
            f"\nTask: {ticket_title}",
            f"Task ID: {ticket_id}",
            f"Description:\n{task_description}"
        ]
        
        # Add project structure context
        if project_structure:
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("PROJECT STRUCTURE")
            prompt_parts.append("=" * 80)
            tech_stack = project_structure.get('tech_stack', {})
            if tech_stack.get('frontend'):
                prompt_parts.append(f"Frontend: {tech_stack['frontend']}")
            if tech_stack.get('backend'):
                prompt_parts.append(f"Backend: {tech_stack['backend']}")
            
            prompt_parts.append("\nExisting Folders:")
            for folder in project_structure.get('folders', []):
                prompt_parts.append(f"  - {folder}")
            
            prompt_parts.append("\nExisting Files (from initialization):")
            for file in project_structure.get('known_files', []):
                prompt_parts.append(f"  - {file}")
            
            # Add MongoDB database information if backend exists
            if project_structure.get('has_backend', False):
                prompt_parts.append("\n" + "=" * 80)
                prompt_parts.append("MONGODB DATABASE ACCESS")
                prompt_parts.append("=" * 80)
                prompt_parts.append(
                    "MongoDB is installed and running in the Docker container.\n"
                    "- MongoDB URI: mongodb://localhost:27017/project_db\n"
                    "- MongoDB runs on port 27017 (default port)\n"
                    "- No authentication required (development mode)\n"
                    "- MongoDB configuration file: server/mongodb.config.ts\n"
                    "\n"
                    "CRITICAL: You MUST use Mongoose for all database interactions.\n"
                    "Do NOT use the native MongoDB driver.\n"
                    "\n"
                    "How to use Mongoose:\n"
                    "1. Mongoose is already installed (included in package.json)\n"
                    "\n"
                    "2. Import and connect to MongoDB:\n"
                    "   import mongoose from 'mongoose';\n"
                    "   import { MONGODB_URI } from './mongodb.config';\n"
                    "   await mongoose.connect(MONGODB_URI);\n"
                    "\n"
                    "3. Define Mongoose schemas and models:\n"
                    "   - Create models in server/models/ directory\n"
                    "   - Use Mongoose schema validation\n"
                    "   - Use Mongoose methods for CRUD operations\n"
                    "   - Example:\n"
                    "     import mongoose from 'mongoose';\n"
                    "     const userSchema = new mongoose.Schema({{\n"
                    "       name: {{ type: String, required: true }},\n"
                    "       email: {{ type: String, required: true, unique: true }}\n"
                    "     }});\n"
                    "     export const User = mongoose.model('User', userSchema);\n"
                    "\n"
                    "4. MongoDB is already running - no need to start it manually.\n"
                    "   The database is accessible immediately when the container is running."
                )
            
            # Add current files in container
            if project_structure.get('current_files'):
                prompt_parts.append("\nCurrent Files in Container:")
                prompt_parts.append(project_structure.get('current_files'))
        
        # Add parent epic context
        if parent_context:
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("PARENT EPIC CONTEXT")
            prompt_parts.append("=" * 80)
            prompt_parts.append(parent_context)
        
        # Add dependencies context
        if dependencies:
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("DEPENDENCIES (Must be completed before this task)")
            prompt_parts.append("=" * 80)
            for dep in dependencies:
                dep_title = dep.get('title', 'Unknown')
                dep_desc = dep.get('description', '')[:200]
                dep_status = dep.get('status', 'unknown')
                prompt_parts.append(f"\n- {dep_title} (Status: {dep_status})")
                if dep_desc:
                    prompt_parts.append(f"  {dep_desc}")
        
        # Add related tickets (siblings in same epic)
        if all_tickets:
            parent_id = ticket.get('parent_id')
            if parent_id:
                siblings = [
                    t for t in all_tickets 
                    if t.get('parent_id') == parent_id 
                    and str(t.get('_id') or t.get('id')) != str(ticket_id)
                    and t.get('type') == 'story'
                ]
                if siblings:
                    prompt_parts.append("\n" + "=" * 80)
                    prompt_parts.append("RELATED TASKS (Same Epic)")
                    prompt_parts.append("=" * 80)
                    for sibling in siblings:
                        sib_status = sibling.get('status', 'unknown')
                        prompt_parts.append(f"- {sibling.get('title', 'Unknown')} (Status: {sib_status})")
        
        # Add completed tickets context (for reference)
        if completed_tickets:
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("COMPLETED TASKS (For Reference)")
            prompt_parts.append("=" * 80)
            for completed in completed_tickets[:5]:  # Limit to 5 most recent
                prompt_parts.append(f"- {completed.get('title', 'Unknown')}")
        
        # Add specific instructions for design decisions
        if needs_design:
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("DESIGN DECISION REQUIRED")
            prompt_parts.append("=" * 80)
            prompt_parts.append(
                "IMPORTANT: This task requires making design decisions. "
                "Before implementing code, create a markdown file (e.g., DESIGN_DECISIONS.md or similar) "
                "that documents your choices. For example:\n"
                "- If choosing colors: list the hex codes and their usage\n"
                "- If choosing fonts: specify font families, sizes, weights\n"
                "- If choosing layout: describe the structure and spacing\n"
                "Then implement the code based on these documented decisions."
            )
        
        # Add development rules and guidelines
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("DEVELOPMENT RULES AND GUIDELINES")
        prompt_parts.append("=" * 80)
        prompt_parts.append(
            "CRITICAL: Follow these rules strictly:\n\n"
            "REACT/FRONTEND RULES:\n"
            "1. COMPONENT REUSABILITY: Before creating a new component, ALWAYS check if one already exists in src/components/\n"
            "   - Look for similar components that can be reused or extended\n"
            "   - Extract common patterns into reusable components\n"
            "   - Use composition over duplication\n\n"
            "2. STATE MANAGEMENT: Use React Context API for shared application state\n"
            "   - Create context providers in src/contexts/ for data accessed across components\n"
            "   - Use useState for local component state only\n"
            "   - Avoid prop drilling - use context when data passes through multiple levels\n\n"
            "3. MODERN REACT PRACTICES:\n"
            "   - Use functional components with hooks\n"
            "   - Use TypeScript for type safety\n"
            "   - Keep components small and focused (single responsibility)\n"
            "   - Use custom hooks to extract reusable logic\n\n"
            "4. FORM VALIDATION: ALWAYS implement frontend form validation\n"
            "   - Use controlled components for form inputs\n"
            "   - Validate input before submission\n"
            "   - Show clear error messages to users\n"
            "   - Disable submit button while form is invalid\n"
            "   - Sanitize user input before sending to backend\n"
            "   - CRITICAL: Password forms on signup MUST include a 'Confirm Password' field (frontend only)\n"
            "   - CRITICAL: When handling form errors, NEVER allow page refresh that clears form data\n"
            "   - Handle form state properly: preserve form data on errors, prevent accidental page reloads\n"
            "   - Use React state to maintain form values even if errors occur\n"
            "   - Prevent form submission from triggering page refresh (use preventDefault on form submit)\n"
            "   - Show error messages without clearing form inputs\n"
            "   - Example: const handleSubmit = (e) => { e.preventDefault(); /* handle submission */ }\n\n"
            "5. DATA SYNCHRONIZATION: ALWAYS refresh data after mutations\n"
            "   - After creating new data (e.g., new post), refetch the list to show the new item\n"
            "   - After updating data, refresh the affected data in the UI\n"
            "   - After deleting data, remove it from the UI or refetch the list\n"
            "   - Use React Context or state management to update data across components\n"
            "   - Don't rely on optimistic updates alone - always verify with server\n"
            "   - Example: After POST /api/posts, refetch GET /api/posts to update the posts list\n\n"
            "6. API CALLS & FETCH REQUESTS: ALWAYS use centralized API utility\n"
            "   - CRITICAL: NEVER use fetch() directly in components or pages\n"
            "   - CRITICAL: ALWAYS create and use src/utils/api.ts for all API calls\n"
            "   - All API calls must go through functions in src/utils/api.ts\n"
            "   - CRITICAL: NEVER use base URL (e.g., http://localhost:5000) in API calls\n"
            "   - CRITICAL: ALWAYS use relative paths starting with /api/... (e.g., /api/posts, /api/users)\n"
            "   - Vite configuration automatically proxies /api/* requests to the backend\n"
            "   - Example: Use fetch('/api/posts') NOT fetch('http://localhost:5000/api/posts')\n"
            "   - Example api.ts structure:\n"
            "     ```typescript\n"
            "     // src/utils/api.ts\n"
            "     export const getPosts = async () => {\n"
            "       const response = await fetch('/api/posts');\n"
            "       return response.json();\n"
            "     };\n"
            "     export const createPost = async (data) => {\n"
            "       const response = await fetch('/api/posts', {\n"
            "         method: 'POST',\n"
            "         headers: { 'Content-Type': 'application/json' },\n"
            "         body: JSON.stringify(data)\n"
            "       });\n"
            "       return response.json();\n"
            "     };\n"
            "     ```\n"
            "   - Import and use in components: import { getPosts, createPost } from '@/utils/api' or './utils/api'\n"
            "   - NEVER write fetch() calls directly in component code\n\n"
            "7. PAGE/ROUTE INTEGRATION: ALWAYS integrate pages immediately\n"
            "   - If creating a page/route component, you MUST:\n"
            "     * Set up routing (add route to router configuration)\n"
            "     * Add navigation (navbar, menu, button, or link to access the page)\n"
            "     * If it's a home/landing page, set it as the default route (/)\n"
            "     * Ensure the page is accessible and visible in the app\n"
            "   - Never create a page component without integrating it into routing and navigation\n"
            "   - Check existing routing setup (likely in src/App.tsx or src/main.tsx)\n"
            "   - If navigation doesn't exist, create it (navbar, menu, etc.)\n"
            "   - Example: If creating HomePage, add route '/' and make it the default route\n\n"
            "8. COLOR & ACCESSIBILITY: ALWAYS ensure readable colors and proper hover states\n"
            "   - Text must be readable in its default state (before hover)\n"
            "   - NEVER use the same color for background and text (e.g., blue button with blue text)\n"
            "   - Hover animations should enhance visibility, not fix broken text readability\n"
            "   - If text color changes on hover, ensure it's readable in BOTH states\n"
            "   - Use sufficient color contrast (WCAG guidelines: 4.5:1 for normal text, 3:1 for large text)\n"
            "   - Test color combinations to ensure text is always visible\n"
            "   - BAD EXAMPLE: Blue button with blue text that only becomes white on hover (text invisible before hover)\n"
            "   - GOOD EXAMPLE: Blue button with white text (readable in default state, can enhance on hover)\n\n"
            "9. AUTHENTICATION & AUTO-REDIRECT: ALWAYS handle authentication properly\n"
            "   - If an API call to a protected endpoint returns 401, automatically redirect to login page\n"
            "   - Check authentication status before making API calls to protected endpoints\n"
            "   - Use route guards or authentication checks in React components\n"
            "   - Protect routes that require authentication (redirect if not authenticated)\n"
            "   - Example: If user tries to access /profile but not logged in, redirect to /login\n"
            "   - Example: If API call returns 401, catch it and redirect to /login\n\n"
            "10. SIGNUP & LOGIN FLOW: CRITICAL authentication behavior\n"
            "   - If there is a login form, the signup function MUST automatically log the user in after successful registration\n"
            "   - Do NOT redirect to login page after signup - the user should be logged in immediately\n"
            "   - After signup, set authentication tokens/cookies and update authentication state\n"
            "   - Redirect to the appropriate page (e.g., dashboard, home) after signup, not to login\n"
            "   - Example: After successful signup, call login function with the new user credentials, or directly set auth state if signup returns auth tokens\n"
            "   - The user should not have to manually log in after creating an account\n\n"
            "11. TODO COMMENTS FOR FUTURE IMPLEMENTATION: Leave detailed TODOs for unimplemented dependencies\n"
            "   - If a dependent function or feature is not implemented yet, leave a detailed TODO comment\n"
            "   - Format: TODO: really detailed description ENDTODO\n"
            "   - The description should be VERY detailed, explaining:\n"
            "     * What needs to be implemented\n"
            "     * Why it's needed (context)\n"
            "     * What dependencies or prerequisites exist\n"
            "     * Any specific requirements or constraints\n"
            "   - Example: TODO: Implement user authentication middleware. This is needed because the /api/profile endpoint requires authentication. The middleware should check for a JWT token in the Authorization header, verify it using the JWT_SECRET, and attach the user object to req.user. If token is missing or invalid, return 401. ENDTODO\n"
            "   - After all tickets are completed, the system will automatically parse the project for TODOs and create tickets for them\n\n"
        )
        
        if project_structure and project_structure.get('has_backend', False):
            prompt_parts.append(
                "BACKEND RULES:\n"
                "1. DATABASE: ALWAYS use Mongoose for all MongoDB interactions\n"
                "   - Do NOT use the native MongoDB driver\n"
                "   - Define Mongoose schemas for all data models\n"
                "   - Place Mongoose models in server/models/ directory\n"
                "   - Use Mongoose models for all CRUD operations\n"
                "   - Use Mongoose schema validation\n"
                "   - Connect using: import mongoose from 'mongoose'; import { MONGODB_URI } from './mongodb.config'; await mongoose.connect(MONGODB_URI);\n\n"
                "2. DATA VALIDATION: ALWAYS validate all input data on the backend\n"
                "   - Validate request body, query parameters, and route parameters\n"
                "   - Use Mongoose schema validation for database models\n"
                "   - Use validation middleware or libraries for API endpoints\n"
                "   - Return clear, specific error messages for validation failures\n"
                "   - Never trust client-side validation alone\n\n"
                "3. AUTHENTICATION & AUTHORIZATION:\n"
                "   - If an endpoint requires authentication, ALWAYS protect it with authentication middleware\n"
                "   - Use authentication middleware to verify tokens/sessions before processing requests\n"
                "   - Return 401 Unauthorized if authentication fails or token is missing/invalid\n"
                "   - Protect all endpoints that access user-specific data\n"
                "   - CRITICAL: If saving passwords in the database, ALWAYS hash them before storing\n"
                "   - NEVER store plain text passwords - use bcrypt, argon2, or similar hashing library\n"
                "   - Hash passwords on the backend before saving to MongoDB\n"
                "   - Example: app.get('/api/posts', authenticateToken, getPostsHandler)\n"
                "   - Example: const hashedPassword = await bcrypt.hash(password, 10); before saving user\n\n"
                "4. API DESIGN:\n"
                "   - Use RESTful conventions for API endpoints\n"
                "   - Return appropriate HTTP status codes\n"
                "   - Use consistent response formats\n"
                "   - Implement proper error handling\n\n"
                "5. SECURITY:\n"
                "   - Sanitize all user input\n"
                "   - Use Mongoose schema validation (Mongoose handles SQL injection protection)\n"
                "   - Validate file uploads (type, size, content)\n\n"
            )
        
        if project_structure and project_structure.get('has_frontend', False):
            prompt_parts.append(
                "FRONTEND AUTHENTICATION RULES:\n"
                "1. AUTO-REDIRECT TO LOGIN: ALWAYS redirect to login page if authentication is required\n"
                "   - If an API call to a protected endpoint returns 401, automatically redirect to login page\n"
                "   - Check authentication status before making API calls to protected endpoints\n"
                "   - Use route guards or authentication checks in React components\n"
                "   - Protect routes that require authentication (redirect if not authenticated)\n"
                "   - Example: If user tries to access /profile but not logged in, redirect to /login\n"
                "   - Example: If API call returns 401, catch it and redirect to /login\n\n"
            )
        
        prompt_parts.append(
            "GENERAL RULES:\n"
            "1. Code Quality: Write clean, readable, maintainable code\n"
            "2. File Organization: Follow existing project structure\n"
            "3. Error Handling: Always handle errors gracefully with user-friendly messages\n"
            "4. TypeScript: Use proper types and interfaces\n"
            "5. Integration: Ensure your implementation integrates well with related tasks\n\n"
        )
        
        # Add implementation instructions
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("IMPLEMENTATION INSTRUCTIONS")
        prompt_parts.append("=" * 80)
        prompt_parts.append(
            "1. Review the project structure and existing files above.\n"
            "2. Check dependencies - ensure prerequisite tasks are completed.\n"
            "3. Check for existing components before creating new ones.\n"
            "4. If this task requires design decisions, first create a markdown file documenting your choices.\n"
            "5. Implement the necessary code changes following the task description.\n"
            "6. Use the existing project structure - don't create unnecessary files.\n"
            "7. Follow ALL development rules listed above.\n"
            "8. Implement proper validation (frontend AND backend if applicable).\n"
            "9. Use React Context for shared state if needed.\n"
            "10. Ensure code quality and follow best practices.\n"
            "11. Make sure your implementation integrates well with related tasks."
        )
        
        prompt_parts.append("\n" + "=" * 80)
        
        return "\n".join(prompt_parts)

    def _get_current_file_structure(self, docker_env: DockerEnv) -> str:
        """Get the current file structure from the Docker container."""
        try:
            # Get a tree-like structure of files
            cmd = 'bash -c "find /app -type f -not -path \'*/node_modules/*\' -not -path \'*/.git/*\' | head -50 | sort"'
            exit_code, output = docker_env.exec_run(cmd, workdir="/app")
            if exit_code == 0 and output:
                files = output.strip().split('\n')
                return "\n".join([f"  - {f}" for f in files if f])
        except:
            pass
        return "  (Unable to retrieve file structure)"

    def resolve_ticket(self, ticket: dict, docker_env: DockerEnv, parent_context: str = None,
                      project_structure: dict = None, all_tickets: list = None) -> bool:
        """
        Attempt to resolve a ticket by generating code via Cursor CLI in Docker.
        Returns True if successful, False otherwise.
        """
        print(f"\n[{self.name}] Picking up ticket: {ticket.get('title')} (ID: {ticket.get('id')})")
        
        # Get current file structure from container
        current_files = self._get_current_file_structure(docker_env)
        if project_structure:
            project_structure['current_files'] = current_files
        
        # 1. Verify cursor-agent is available
        print(f"[{self.name}] Checking if cursor-agent is available...")
        
        # Check if cursor-agent exists at expected location
        check_cmd = 'bash -c "which cursor-agent 2>/dev/null || echo NOT_FOUND"'
        exit_code, output = docker_env.exec_run(check_cmd)
        
        if 'NOT_FOUND' in output or exit_code != 0:
            print(f"[{self.name}] ERROR: cursor-agent not found in PATH!")
            print(f"[{self.name}] Checking installation location...")
            
            # Check if it exists at the expected location
            check_location_cmd = 'bash -c "ls -la /root/.local/bin/cursor-agent 2>/dev/null || echo NOT_IN_LOCAL_BIN"'
            exit_code_loc, output_loc = docker_env.exec_run(check_location_cmd)
            print(f"[{self.name}] Location check output:\n{output_loc}")
            
            # Check PATH
            path_cmd = 'bash -c "echo PATH=$PATH && echo HOME=$HOME"'
            exit_code_path, output_path = docker_env.exec_run(path_cmd)
            print(f"[{self.name}] Environment check:\n{output_path}")
            
            # Try to find cursor-agent anywhere
            find_cmd = 'bash -c "find /root -name cursor-agent 2>/dev/null | head -5 || echo NOT_FOUND_ANYWHERE"'
            exit_code_find, output_find = docker_env.exec_run(find_cmd)
            print(f"[{self.name}] Search for cursor-agent:\n{output_find}")
            
            # If found but not in PATH, try using full path
            if 'NOT_FOUND_ANYWHERE' not in output_find and '/root/.local/bin/cursor-agent' in output_loc:
                print(f"[{self.name}] cursor-agent found at /root/.local/bin/cursor-agent, will use full path")
                self.cursor_agent_path = "/root/.local/bin/cursor-agent"
            else:
                print(f"[{self.name}] cursor-agent installation appears to have failed!")
                print(f"[{self.name}] Attempting to reinstall...")
                install_cmd = 'bash -c "curl https://cursor.com/install -fsS | bash"'
                exit_code_install, output_install = docker_env.exec_run(install_cmd)
                print(f"[{self.name}] Reinstall output:\n{output_install}")
                
                # Check again after reinstall
                check_again = 'bash -c "which cursor-agent 2>/dev/null || /root/.local/bin/cursor-agent --version 2>/dev/null || echo STILL_NOT_FOUND"'
                exit_code_again, output_again = docker_env.exec_run(check_again)
                print(f"[{self.name}] After reinstall check:\n{output_again}")
                
                if 'STILL_NOT_FOUND' in output_again:
                    print(f"[{self.name}] FATAL: cursor-agent cannot be installed or found!")
                    return False
                else:
                    self.cursor_agent_path = "/root/.local/bin/cursor-agent"
        else:
            print(f"[{self.name}] cursor-agent found in PATH.")
            self.cursor_agent_path = "cursor-agent"
        
        # 2. Check CURSOR_API_KEY
        print(f"[{self.name}] Checking CURSOR_API_KEY...")
        key_cmd = 'bash -c \'if [ -z "$CURSOR_API_KEY" ]; then echo "MISSING"; else echo "SET"; fi\''
        exit_code3, output3 = docker_env.exec_run(key_cmd)
        if 'MISSING' in output3:
            print(f"[{self.name}] WARNING: CURSOR_API_KEY not set in container!")
        else:
            print(f"[{self.name}] CURSOR_API_KEY is set.")
        
        # 2.5. Test cursor-agent with a simple command
        print(f"[{self.name}] Testing cursor-agent with --help or --version...")
        test_cmd = f'bash -c "{self.cursor_agent_path} --version 2>&1 || {self.cursor_agent_path} --help 2>&1 || echo CURSOR_AGENT_TEST_FAILED"'
        test_exit, test_output = docker_env.exec_run(test_cmd, workdir="/app")
        print(f"[{self.name}] cursor-agent test output:\n{test_output[:300]}")
        if 'CURSOR_AGENT_TEST_FAILED' in test_output:
            print(f"[{self.name}] WARNING: cursor-agent test command failed!")
        
        # 3. Build enhanced prompt with full context
        # Get dependencies for this ticket
        dependencies = []
        ticket_dep_ids = ticket.get('dependencies', [])
        if ticket_dep_ids and all_tickets:
            for dep_id in ticket_dep_ids:
                dep_ticket = next(
                    (t for t in all_tickets 
                     if str(t.get('_id') or t.get('id')) == str(dep_id)),
                    None
                )
                if dep_ticket:
                    dependencies.append(dep_ticket)
        
        # Get completed tickets for reference
        completed_tickets = []
        if all_tickets:
            completed_tickets = [t for t in all_tickets if t.get('status') == 'done']
        
        cursor_prompt = self._build_enhanced_prompt(
            ticket, 
            parent_context,
            project_structure=project_structure,
            all_tickets=all_tickets,
            dependencies=dependencies,
            completed_tickets=completed_tickets
        )
        
        # 4. Execute Cursor CLI command
        # Using stdin to pass prompt (more reliable than command line args)
        # First, write prompt to a temp file, then use it
        print(f"[{self.name}] Preparing prompt file...")
        
        # Escape the prompt for safe shell usage
        # Use a here-document approach
        prompt_escaped = cursor_prompt.replace('$', '\\$').replace('`', '\\`')
        
        # Write prompt to file first, then use cursor-agent with file
        write_prompt_cmd = f'''bash -c "cat > /tmp/cursor_prompt.txt << 'PROMPT_EOF'
{cursor_prompt}
PROMPT_EOF"
'''
        
        print(f"[{self.name}] Writing prompt to /tmp/cursor_prompt.txt...")
        exit_code_write, output_write = docker_env.exec_run(write_prompt_cmd)
        if exit_code_write != 0:
            print(f"[{self.name}] ERROR: Failed to write prompt file!")
            print(f"[{self.name}] Write command output: {output_write}")
            return False
        
        # Now execute cursor-agent with the prompt file
        # Using -p for print mode and reading from stdin/file
        cursor_cmd = getattr(self, 'cursor_agent_path', 'cursor-agent')
        
        # Create debug folder in home directory (use absolute path)
        debug_folder = "/root/cursor_debug"
        create_folder_cmd = f'bash -c "mkdir -p {debug_folder}"'
        docker_env.exec_run(create_folder_cmd, workdir="/app")
        
        # Create debug output filename based on ticket in home directory
        ticket_id = ticket.get('id') or ticket.get('_id', 'unknown')
        safe_title = "".join(c for c in ticket.get('title', 'ticket')[:30] if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        debug_output_file = f"{debug_folder}/cursor_debug_{ticket_id}_{safe_title}.txt"
        
        # Execute cursor-agent and capture output
        # Run from /app directory so files are created in the project directory
        # Include /app as context using @/app notation if supported, otherwise just cd to /app
        cmd = f'bash -c "cd /app && {cursor_cmd} -p --force < /tmp/cursor_prompt.txt 2>&1"'
        
        print(f"[{self.name}] Executing Cursor CLI command...")
        print(f"[{self.name}] Command: cd /app && {cursor_cmd} -p --force < /tmp/cursor_prompt.txt")
        print(f"[{self.name}] Working directory: /app (project directory)")
        print(f"[{self.name}] Debug output will be saved to: {debug_output_file}")
        print(f"[{self.name}] Prompt preview (first 200 chars): {cursor_prompt[:200]}...")
        
        # Also save the prompt to a file for reference in home directory
        prompt_debug_file = f"{debug_folder}/cursor_prompt_{ticket_id}_{safe_title}.txt"
        save_prompt_cmd = f'bash -c "cp /tmp/cursor_prompt.txt {prompt_debug_file}"'
        docker_env.exec_run(save_prompt_cmd, workdir="/app")
        print(f"[{self.name}] Prompt saved to: {prompt_debug_file}")
        
        # Verify we're in the right directory before execution
        verify_dir_cmd = 'bash -c "cd /app && pwd && ls -la | head -5"'
        verify_exit, verify_output = docker_env.exec_run(verify_dir_cmd, workdir="/app")
        print(f"[{self.name}] Directory verification:\n{verify_output[:200]}")
        
        # Add project directory context to the prompt
        # Cursor-agent works in the current directory, so we'll run from /app
        # We can also mention the directory in the prompt itself
        enhanced_prompt = f"{cursor_prompt}\n\nIMPORTANT: All files should be created/modified in the /app directory. The current working directory is /app."
        
        # Update the prompt file with enhanced version
        enhanced_prompt_b64 = base64.b64encode(enhanced_prompt.encode('utf-8')).decode('ascii')
        update_prompt_cmd = f"python3 -c \"import base64; open('/tmp/cursor_prompt.txt', 'w').write(base64.b64decode('{enhanced_prompt_b64}').decode('utf-8'))\""
        docker_env.exec_run(update_prompt_cmd, workdir="/app")
        
        # Wait 10 seconds before execution to avoid rate limiting
        print(f"[{self.name}] Waiting 10 seconds before execution to avoid rate limiting...")
        time.sleep(10)
        print(f"[{self.name}] Starting execution now...")
        
        # Execute the command and capture output
        # Run from /app directory so files are created in the project
        exit_code, output = docker_env.exec_run(cmd, workdir="/app")
        
        # Explicitly write the output to the debug file
        # Escape the output for safe shell usage
        output_escaped = output.replace('$', '\\$').replace('`', '\\`').replace('"', '\\"')
        write_output_cmd = f'''bash -c "cat > {debug_output_file} << 'OUTPUT_EOF'
{output}
OUTPUT_EOF"
'''
        write_exit, write_output = docker_env.exec_run(write_output_cmd, workdir="/app")
        if write_exit != 0:
            print(f"[{self.name}] WARNING: Failed to write output to debug file! Exit code: {write_exit}")
            print(f"[{self.name}] Write command output: {write_output}")
        else:
            print(f"[{self.name}] Output successfully written to {debug_output_file}")
        
        # Enhanced error logging
        print(f"\n[{self.name}] ========== Cursor CLI Execution Results ==========")
        print(f"[{self.name}] Exit Code: {exit_code}")
        print(f"[{self.name}] Output Length: {len(output)} characters")
        print(f"[{self.name}] First 500 chars of output:\n{output[:500]}")
        if len(output) > 500:
            print(f"[{self.name}] ... (truncated, full output in {debug_output_file})")
        print(f"[{self.name}] Full output saved to: {debug_output_file}")
        print(f"[{self.name}] ====================================================\n")
        
        # Verify the debug file was created and show its size and content preview
        check_file_cmd = f'bash -c "ls -lh {debug_output_file} 2>/dev/null && echo ---FILE_CONTENT_START--- && head -20 {debug_output_file} 2>/dev/null || echo FILE_NOT_CREATED"'
        file_check_exit, file_check_output = docker_env.exec_run(check_file_cmd, workdir="/app")
        print(f"[{self.name}] Debug file check:\n{file_check_output.strip()}")
        
        # Also list all files in the debug folder
        list_files_cmd = f'bash -c "ls -lah {debug_folder}/ 2>/dev/null || echo FOLDER_NOT_FOUND"'
        list_exit, list_output = docker_env.exec_run(list_files_cmd, workdir="/app")
        print(f"[{self.name}] Files in {debug_folder}:\n{list_output.strip()}")
        
        # Check for common error patterns
        if exit_code != 0:
            error_patterns = {
                'resource_exhausted': 'API rate limit or resource exhaustion',
                'ConnectError': 'Connection error - check network/API endpoint',
                'authentication': 'Authentication failed - check CURSOR_API_KEY',
                'not found': 'Command not found - check cursor-agent installation',
                'permission': 'Permission denied - check file permissions'
            }
            
            for pattern, description in error_patterns.items():
                if pattern.lower() in output.lower():
                    print(f"[{self.name}] Detected error pattern '{pattern}': {description}")
            
            print(f"[{self.name}] Failed to execute Cursor command (exit code: {exit_code}).")
            return False
        
        # Check output for success indicators
        if 'error' in output.lower() or 'failed' in output.lower():
            print(f"[{self.name}] WARNING: Output contains error keywords, but exit code was 0.")
        
        print(f"[{self.name}] Ticket resolved successfully.")
        return True
