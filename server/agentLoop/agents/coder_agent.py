from agents.base_agent import BaseAgent
from systems.docker_env import DockerEnv
import time
import re

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

    def _build_enhanced_prompt(self, ticket: dict, parent_context: str = None) -> str:
        """Build an enhanced prompt that handles design decisions."""
        task_description = ticket.get('description', '')
        ticket_title = ticket.get('title', '')
        
        # Check if this needs a design decision
        needs_design = self._needs_design_decision(ticket_title, task_description)
        
        prompt_parts = [
            f"Task: {ticket_title}",
            f"Description: {task_description}"
        ]
        
        if parent_context:
            prompt_parts.append(f"\nContext from Parent Epic:\n{parent_context}")
        
        # Add specific instructions for design decisions
        if needs_design:
            prompt_parts.append(
                "\nIMPORTANT: This task requires making design decisions. "
                "Before implementing code, create a markdown file (e.g., DESIGN_DECISIONS.md or similar) "
                "that documents your choices. For example:\n"
                "- If choosing colors: list the hex codes and their usage\n"
                "- If choosing fonts: specify font families, sizes, weights\n"
                "- If choosing layout: describe the structure and spacing\n"
                "Then implement the code based on these documented decisions."
            )
        
        prompt_parts.append(
            "\nInstructions:\n"
            "1. If this task requires design decisions (colors, fonts, layouts, etc.), "
            "first create a markdown file documenting your choices.\n"
            "2. Implement the necessary code changes.\n"
            "3. If there are tests, run them to verify.\n"
            "4. If there are no tests, create basic tests if possible.\n"
            "5. Ensure code quality and follow best practices."
        )
        
        return "\n".join(prompt_parts)

    def resolve_ticket(self, ticket: dict, docker_env: DockerEnv, parent_context: str = None) -> bool:
        """
        Attempt to resolve a ticket by generating code via Cursor CLI in Docker.
        Returns True if successful, False otherwise.
        """
        print(f"\n[{self.name}] Picking up ticket: {ticket.get('title')} (ID: {ticket.get('id')})")
        
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
        
        # 3. Build enhanced prompt
        cursor_prompt = self._build_enhanced_prompt(ticket, parent_context)
        
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
        cmd = f'bash -c "{cursor_cmd} -p --force < /tmp/cursor_prompt.txt 2>&1"'
        
        print(f"[{self.name}] Executing Cursor CLI command...")
        print(f"[{self.name}] Command: {cursor_cmd} -p --force < /tmp/cursor_prompt.txt")
        print(f"[{self.name}] Debug output will be saved to: {debug_output_file}")
        print(f"[{self.name}] Prompt preview (first 200 chars): {cursor_prompt[:200]}...")
        
        # Also save the prompt to a file for reference in home directory
        prompt_debug_file = f"{debug_folder}/cursor_prompt_{ticket_id}_{safe_title}.txt"
        save_prompt_cmd = f'bash -c "cp /tmp/cursor_prompt.txt {prompt_debug_file}"'
        docker_env.exec_run(save_prompt_cmd, workdir="/app")
        print(f"[{self.name}] Prompt saved to: {prompt_debug_file}")
        
        # Wait 10 seconds before execution to avoid rate limiting
        print(f"[{self.name}] Waiting 10 seconds before execution to avoid rate limiting...")
        time.sleep(10)
        print(f"[{self.name}] Starting execution now...")
        
        # Execute the command and capture output
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
