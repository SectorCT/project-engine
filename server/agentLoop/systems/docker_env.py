import docker
import hashlib
import io
import os
import tarfile
import time
from typing import Optional

from config.settings import settings


def get_port_for_project(project_id: str, port_base: int = 48000, port_range: int = 1000) -> int:
    """
    Deterministically assign a host port for the per-job container (defaults to 48000-48999).
    """
    hash_obj = hashlib.md5(project_id.encode('utf-8'))
    hash_int = int(hash_obj.hexdigest(), 16)
    return port_base + (hash_int % port_range)


class DockerEnv:
    def __init__(self, workspace_path: str = None, project_id: Optional[str] = None):
        """
        Initialize DockerEnv.
        :param workspace_path: Path to LOCAL workspace (currently unused - container starts empty).
        :param project_id: Job/project identifier used for container naming and port assignment.
        """
        if settings.DOCKER_SOCKET_PATH:
            self.client = docker.DockerClient(base_url=settings.DOCKER_SOCKET_PATH)
        else:
            self.client = docker.from_env()

        self.workspace_path = os.path.abspath(workspace_path) if workspace_path else None
        self.image_name = "project_engine_builder:latest"
        self.project_id = project_id
        self.container_name = (
            f"project_engine_{project_id}_container" if project_id else "project_engine_builder_container"
        )
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
                rm=True,
            )
            print("Docker image built successfully.")
        except docker.errors.BuildError as exc:
            print(f"Error building Docker image: {exc}")
            raise

    def start_container(self, has_backend: bool = False):
        """
        Start or resume the container for this project.
        Existing containers are reused to keep artifacts accessible for debugging.
        """
        if self.project_id:
            frontend_port = get_port_for_project(self.project_id, port_base=48000, port_range=1000)
            mongo_port = frontend_port + 1 if has_backend else None
            if mongo_port and mongo_port >= 49000:
                mongo_port = frontend_port - 1
        else:
            frontend_port = 3000
            mongo_port = 6666 if has_backend else None

        try:
            try:
                existing = self.client.containers.get(self.container_name)
                status = existing.attrs.get('State', {}).get('Status')
                if status == 'running':
                    print(f"Container {self.container_name} already running. Reusing.")
                    self.container = existing
                    self._log_ports(existing, has_backend)
                    return
                if status in {'exited', 'stopped'}:
                    print(f"Container {self.container_name} exists but is stopped. Starting...")
                    existing.start()
                    time.sleep(2)
                    self.container = existing
                    self._log_ports(existing, has_backend)
                    return
                print(f"Container {self.container_name} in unexpected state '{status}'. Removing...")
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass

            print(f"Creating new container {self.container_name}...")
            environment = {}
            if settings.CURSOR_API_KEY:
                environment["CURSOR_API_KEY"] = settings.CURSOR_API_KEY

            ports = {'3000/tcp': frontend_port}
            if has_backend and mongo_port:
                ports['27017/tcp'] = mongo_port

            self.container = self.client.containers.run(
                self.image_name,
                name=self.container_name,
                ports=ports,
                environment=environment,
                detach=True,
                tty=True,
                remove=False,
                log_config=docker.types.LogConfig(type=docker.types.LogConfig.types.JSON),
            )
            print(f"✅ Container {self.container_name} started.")
            self._log_ports(self.container, has_backend)
            time.sleep(2)
        except Exception as exc:
            print(f"Error starting container: {exc}")
            raise

    def _log_ports(self, container, has_backend: bool) -> None:
        bindings = container.attrs.get('HostConfig', {}).get('PortBindings', {})
        frontend_binding = bindings.get('3000/tcp')
        if frontend_binding:
            print(f"  Frontend available at http://localhost:{frontend_binding[0]['HostPort']}")
        if has_backend:
            mongo_binding = bindings.get('27017/tcp')
            if mongo_binding:
                print(f"  MongoDB mapped to localhost:{mongo_binding[0]['HostPort']}")

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
