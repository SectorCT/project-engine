import docker
import os
import time
import tarfile
import io
from config.settings import settings

class DockerEnv:
    def __init__(self, workspace_path: str = None):
        """
        Initialize DockerEnv.
        :param workspace_path: Path to LOCAL workspace (currently unused - container starts empty).
        """
        # Allow configuring Docker client (e.g. for Docker Desktop)
        # docker.from_env() automatically reads DOCKER_HOST environment variable if set.
        # We can also pass base_url if needed from settings.
        if settings.DOCKER_SOCKET_PATH:
             self.client = docker.DockerClient(base_url=settings.DOCKER_SOCKET_PATH)
        else:
             self.client = docker.from_env()
             
        self.workspace_path = os.path.abspath(workspace_path) if workspace_path else None
        self.image_name = "project_engine_builder:latest"
        self.container_name = "project_engine_builder_container"
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

    def start_container(self):
        """Start the container (ISOLATED and EMPTY)."""
        try:
            # Check if container exists and remove it
            try:
                old_container = self.client.containers.get(self.container_name)
                old_container.remove(force=True)
            except docker.errors.NotFound:
                pass

            print(f"Starting container {self.container_name} (ISOLATED and EMPTY)...")
            
            environment = {}
            if settings.CURSOR_API_KEY:
                environment["CURSOR_API_KEY"] = settings.CURSOR_API_KEY
            
            # Expose port 3000 for frontend (Vite dev server)
            # Map container port 3000 to host port 3000
            ports = {'3000/tcp': 3000}
            
            # NO VOLUMES. We want isolation.
            # Container starts completely empty - no files copied.
            self.container = self.client.containers.run(
                self.image_name,
                name=self.container_name,
                # volumes={}, # Removed binding
                ports=ports,
                environment=environment,
                detach=True,
                tty=True,
                log_config=docker.types.LogConfig(type=docker.types.LogConfig.types.JSON)
            )
            print("Container started (empty filesystem).")
            
            # Wait a moment for the container to stabilize
            time.sleep(2)
            
            # We do NOT copy any files - container starts fresh/empty
            
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

    def exec_run(self, command: str, workdir: str = "/app"):
        """
        Execute a command inside the container with enhanced logging.
        """
        if not self.container:
            raise Exception("Container not running.")
        
        print(f"[DockerEnv] Executing command: {command[:100]}..." if len(command) > 100 else f"[DockerEnv] Executing command: {command}")
        print(f"[DockerEnv] Working directory: {workdir}")
        
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
            
            # Log execution details
            print(f"[DockerEnv] Command exit code: {exit_code}")
            if exit_code != 0:
                print(f"[DockerEnv] Command failed with exit code {exit_code}")
            
            return exit_code, decoded_output
            
        except Exception as e:
            print(f"[DockerEnv] Exception during command execution: {type(e).__name__}: {e}")
            # Return error exit code and error message
            return 1, f"Execution error: {str(e)}"

    def stop_container(self):
        """Stop and remove the container."""
        if self.container:
            print("Stopping container...")
            try:
                self.container.stop()
                self.container.remove()
                print("Container stopped and removed.")
            except Exception as e:
                print(f"Error stopping container: {e}")
            finally:
                self.container = None
