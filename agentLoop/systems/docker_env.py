import docker
import docker.errors
import os
import time
import tarfile
import io
import hashlib
from typing import Dict, Any
from config.settings import settings

def get_port_for_project(project_id: str, port_base: int = 20000, port_range: int = 29000) -> int:
    """
    Deterministically assign a port in the range [port_base, port_base + port_range) 
    based on project_id hash.
    
    Args:
        project_id: Unique project identifier
        port_base: Starting port number (default 20000)
        port_range: Number of ports available (default 29000, so range is 20000-48999)
    
    Returns:
        Port number in the specified range
    """
    # Hash the project_id to get a consistent port
    hash_obj = hashlib.md5(project_id.encode('utf-8'))
    hash_int = int(hash_obj.hexdigest(), 16)
    port = port_base + (hash_int % port_range)
    return port

class DockerEnv:
    def __init__(self, workspace_path: str = None, project_id: str = None):
        """
        Initialize DockerEnv.
        :param workspace_path: Path to LOCAL workspace (currently unused - container starts empty).
        :param project_id: Unique project ID for persistent container naming. If None, uses default container name.
        """
        # Use default Docker socket at /var/run/docker.sock
        # This is the standard location for Docker-in-Docker (socket mounted from host)
        # The socket is mounted in docker-compose.yml: /var/run/docker.sock:/var/run/docker.sock
        default_socket_path = '/var/run/docker.sock'
        try:
            # Check if socket file exists (it should be mounted from host)
            if os.path.exists(default_socket_path):
                # Use the mounted socket - this allows the container to control the host's Docker daemon
                self.client = docker.DockerClient(base_url=f'unix://{default_socket_path}')
        else:
                # Fallback: try docker.from_env() which reads DOCKER_HOST env var
                # This is useful if DOCKER_HOST is set to a different socket path
             self.client = docker.from_env()
        except docker.errors.DockerException as e:
            raise RuntimeError(
                f"Cannot connect to Docker daemon. Socket file '{default_socket_path}' not found or not accessible. "
                f"Make sure Docker socket is mounted in the container (docker-compose.yml should have: "
                f"- /var/run/docker.sock:/var/run/docker.sock). Original error: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Docker client. Socket file '{default_socket_path}' may not exist or Docker daemon may not be running. "
                f"Original error: {e}"
            ) from e
             
        self.workspace_path = os.path.abspath(workspace_path) if workspace_path else None
        self.image_name = "project_engine_builder:latest"
        # Use project-specific container name if project_id is provided
        if project_id:
            self.container_name = f"project_engine_{project_id}_container"
        else:
            self.container_name = "project_engine_builder_container"
        self.project_id = project_id
        self.container = None

    def build_image(self):
        """Build the Docker image if it doesn't exist."""
        print(f"Building Docker image {self.image_name}...")
        dockerfile_path = os.path.join(os.path.dirname(__file__), '../docker')
        
        try:
            self.client.images.build(
                path=dockerfile_path,
                dockerfile="Dockerfile.builder",
                tag=self.image_name,
                rm=True
            )
            print("Docker image built successfully.")
        except docker.errors.BuildError as e:
            print(f"Error building Docker image: {e}")
            raise

    def start_container(self, has_backend: bool = False):
        """
        Start or resume the container for this project.
        If container exists and is stopped, resume it.
        If container exists and is running, reuse it.
        If container doesn't exist, create a new one.
        """
        # Calculate expected ports based on project_id
        if self.project_id:
            frontend_port = get_port_for_project(self.project_id, port_base=20000, port_range=29000)
        else:
            frontend_port = 3000
        
        try:
            # Check if container already exists
            try:
                existing_container = self.client.containers.get(self.container_name)
                container_info = existing_container.attrs
                container_status = container_info['State']['Status']
                
                if container_status == 'running':
                    print(f"Container {self.container_name} is already running. Reusing existing container.")
                    self.container = existing_container
                    return
                elif container_status in ['exited', 'stopped']:
                    print(f"Container {self.container_name} exists but is stopped. Resuming container...")
                    existing_container.start()
                    self.container = existing_container
                    # Wait a moment for the container to stabilize
                    time.sleep(2)
                    print(f"✅ Container {self.container_name} resumed successfully.")
                    return
                else:
                    # Container is in an unexpected state, remove and recreate
                    print(f"Container {self.container_name} is in state '{container_status}'. Removing and recreating...")
                    existing_container.remove(force=True)
            except docker.errors.NotFound:
                # Container doesn't exist, will create new one
                pass

            print(f"Creating new container {self.container_name}...")
            
            environment = {}
            if settings.CURSOR_API_KEY:
                environment["CURSOR_API_KEY"] = settings.CURSOR_API_KEY
            
            # Assign ports dynamically based on project_id
            ports = {'3000/tcp': frontend_port}
            
            # Create persistent container (not ephemeral)
            # Container will persist across restarts
            self.container = self.client.containers.run(
                self.image_name,
                name=self.container_name,
                ports=ports,
                environment=environment,
                detach=True,
                tty=True,
                # Keep container running even after exit
                remove=False,  # Don't auto-remove on stop
                log_config=docker.types.LogConfig(type=docker.types.LogConfig.types.JSON)
            )
            print(f"✅ Container {self.container_name} created and started.")
            
            # Wait a moment for the container to stabilize
            time.sleep(2)
            
        except Exception as e:
            print(f"Error starting container: {e}")
            raise

    def copy_workspace_to_container(self):
        """
        Copies the local workspace into the container's /app directory.
        This is safer than binding as it doesn't touch local files.
        (Currently unused - container starts empty)
        """
        if not self.container:
            return

        print(f"Copying workspace from {self.workspace_path} to container:/app ...")
        
        # Create a tar archive of the workspace in memory
        # We exclude .git, venv, node_modules to keep it light/clean
        exclude = {'.git', 'venv', 'node_modules', '__pycache__', '.DS_Store'}
        
        # We'll stream it to the container
        # Python's tarfile module can be slow for huge projects, but fine for this scale.
        # Alternatively we can use `docker cp` via subprocess, but using the library is cleaner.
        
        try:
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w') as tar:
                # Add files from workspace_path to tar
                for root, dirs, files in os.walk(self.workspace_path):
                    # Modify dirs in-place to skip excluded
                    dirs[:] = [d for d in dirs if d not in exclude]
                    
                    for file in files:
                        if file in exclude: continue
                        
                        file_path = os.path.join(root, file)
                        # Arcname is relative path inside the tar
                        rel_path = os.path.relpath(file_path, self.workspace_path)
                        tar.add(file_path, arcname=rel_path)
            
            stream.seek(0)
            
            # Put archive into /app
            self.container.put_archive(path='/app', data=stream)
            print("Workspace copied successfully.")
            
        except Exception as e:
            print(f"Error copying workspace: {e}")
            # Non-fatal? Maybe fatal if we need the code.
            raise

    def exec_run(self, command: str, workdir: str = "/app", silent: bool = False):
        """
        Execute a command inside the container with minimal logging.
        """
        if not self.container:
            raise Exception("Container not running.")
        
        if not silent:
            # Only log if explicitly requested (for important commands)
            pass
        
        try:
            exit_code, output = self.container.exec_run(
                command, 
                workdir=workdir,
                environment={"CURSOR_API_KEY": settings.CURSOR_API_KEY} if settings.CURSOR_API_KEY else {},
                stdout=True,
                stderr=True
            )
            
            try:
                decoded_output = output.decode('utf-8')
            except UnicodeDecodeError:
                # Try with error handling
                decoded_output = output.decode('utf-8', errors='replace')
            except:
                decoded_output = str(output)
            
            # Only log errors if not silent
            if not silent and exit_code != 0:
                print(f"⚠️  Command failed with exit code {exit_code}")
            
            return exit_code, decoded_output
            
        except Exception as e:
            if not silent:
                print(f"⚠️  Execution error: {str(e)}")
            # Return error exit code and error message
            return 1, f"Execution error: {str(e)}"

    def get_file_structure(self, path: str = "/app") -> Dict[str, Any]:
        """
        Get file structure from container as a tree.
        Returns a dict with 'type' (file/dir), 'name', 'path', and 'children' (for dirs).
        """
        if not self.container:
            raise Exception("Container not running.")
        
        try:
            # Use find command to get file structure
            cmd = f'sh -c \'find {path} -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" | head -200\''
            exit_code, output = self.container.exec_run(cmd, workdir="/app")
            
            if exit_code != 0:
                return {"error": f"Failed to get file structure: {output}"}
            
            files = [line.strip() for line in output.strip().split('\n') if line.strip()]
            
            # Build tree structure
            tree = {}
            for file_path in files:
                parts = file_path.replace(path, '').strip('/').split('/')
                current = tree
                for i, part in enumerate(parts):
                    if part not in current:
                        is_file = i == len(parts) - 1
                        current[part] = {
                            "name": part,
                            "path": file_path,
                            "type": "file" if is_file else "dir",
                            "children": {} if not is_file else None
                        }
                    current = current[part].get("children", {})
            
            # Convert to list format
            def dict_to_list(d):
                result = []
                for key, value in sorted(d.items()):
                    item = {
                        "name": value["name"],
                        "path": value["path"],
                        "type": value["type"]
                    }
                    if value["type"] == "dir" and value["children"]:
                        item["children"] = dict_to_list(value["children"])
                    result.append(item)
                return result
            
            return {"structure": dict_to_list(tree)}
            
        except Exception as e:
            return {"error": f"Error getting file structure: {str(e)}"}
    
    def read_file(self, file_path: str) -> str:
        """
        Read file content from container.
        Returns file content as string.
        """
        if not self.container:
            raise Exception("Container not running.")
        
        try:
            # Use cat to read file
            cmd = f'cat "{file_path}"'
            exit_code, output = self.container.exec_run(cmd, workdir="/app")
            
            if exit_code != 0:
                raise Exception(f"Failed to read file: {output}")
            
            return output.decode('utf-8', errors='replace')
            
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
    
    def get_container(self):
        """Get the container object (for external use, e.g., in API endpoints)."""
        if not self.container:
            # Try to get existing container
            try:
                self.container = self.client.containers.get(self.container_name)
            except docker.errors.NotFound:
                return None
        return self.container

    def stop_container(self, remove: bool = False):
        """
        Stop the container.
        :param remove: If True, also remove the container. Default False to keep it persistent.
        """
        if self.container:
            print(f"Stopping container {self.container_name}...")
            try:
                self.container.stop()
                if remove:
                    self.container.remove()
                    print(f"Container {self.container_name} stopped and removed.")
                else:
                    print(f"Container {self.container_name} stopped (still exists, can be resumed).")
            except Exception as e:
                print(f"Error stopping container: {e}")
            finally:
                self.container = None
