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
                    "You can use MongoDB in your backend code:\n"
                    "1. Import the MongoDB URI from server/mongodb.config.ts:\n"
                    "   import { MONGODB_URI } from './mongodb.config';\n"
                    "\n"
                    "2. Install mongodb driver if needed:\n"
                    "   npm install mongodb\n"
                    "\n"
                    "3. Connect to MongoDB:\n"
                    "   import { MongoClient } from 'mongodb';\n"
                    "   const client = new MongoClient(MONGODB_URI);\n"
                    "   await client.connect();\n"
                    "   const db = client.db('project_db');\n"
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
        
        # Add implementation instructions
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("IMPLEMENTATION INSTRUCTIONS")
        prompt_parts.append("=" * 80)
        prompt_parts.append(
            "1. Review the project structure and existing files above.\n"
            "2. Check dependencies - ensure prerequisite tasks are completed.\n"
            "3. If this task requires design decisions, first create a markdown file documenting your choices.\n"
            "4. Implement the necessary code changes following the task description.\n"
            "5. Use the existing project structure - don't create unnecessary files.\n"
            "6. Follow the tech stack conventions (TypeScript, React patterns, etc.).\n"
            "7. If there are tests, run them to verify.\n"
            "8. If there are no tests, create basic tests if possible.\n"
            "9. Ensure code quality and follow best practices.\n"
            "10. Make sure your implementation integrates well with related tasks."
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
