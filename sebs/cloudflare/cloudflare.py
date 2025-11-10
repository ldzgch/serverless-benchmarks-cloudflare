import os
import shutil
import json
from typing import cast, Dict, List, Optional, Tuple, Type

import docker
import subprocess  # <-- ADD THIS
import requests

from sebs.cloudflare.config import CloudflareConfig
from sebs.cloudflare.function import CloudflareWorker
from sebs.cloudflare.resources import CloudflareSystemResources
from sebs.cloudflare.container import CloudflareContainer
from sebs.benchmark import Benchmark
from sebs.cache import Cache
from sebs.config import SeBSConfig
from sebs.utils import LoggingHandlers
from sebs.faas.function import Function, ExecutionResult, Trigger, FunctionConfig
from sebs.faas.system import System



class Cloudflare(System):
    """
    Cloudflare Workers serverless platform implementation.
    
    Cloudflare Workers run on Cloudflare's edge network, providing
    low-latency serverless execution globally.
    """
    
    _config: CloudflareConfig
    container_client: CloudflareContainer

    @staticmethod
    def name():
        return "cloudflare"

    @staticmethod
    def typename():
        return "Cloudflare"

    @staticmethod
    def function_type() -> "Type[Function]":
        return CloudflareWorker

    @property
    def config(self) -> CloudflareConfig:
        return self._config

    def __init__(
        self,
        sebs_config: SeBSConfig,
        config: CloudflareConfig,
        cache_client: Cache,
        docker_client: docker.client,
        logger_handlers: LoggingHandlers,
    ):
        super().__init__(
            sebs_config,
            cache_client,
            docker_client,
            CloudflareSystemResources(config, cache_client, docker_client, logger_handlers),
        )
        self.logging_handlers = logger_handlers
        self._config = config
        self._api_base_url = "https://api.cloudflare.com/client/v4"
        self.container_client = CloudflareContainer(
            sebs_config, config, docker_client
        )

    def initialize(self, config: Dict[str, str] = {}, resource_prefix: Optional[str] = None):
        """
        Initialize the Cloudflare Workers platform.
        
        Args:
            config: Additional configuration parameters
            resource_prefix: Prefix for resource naming
        """
        # Verify credentials are valid
        self._verify_credentials()
        self.initialize_resources(select_prefix=resource_prefix)

    def _verify_credentials(self):
        """Verify that the Cloudflare API credentials are valid."""
        headers = self._get_auth_headers()
        response = requests.get(f"{self._api_base_url}/user/tokens/verify", headers=headers)
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to verify Cloudflare credentials: {response.status_code} - {response.text}"
            )
        
        self.logging.info("Cloudflare credentials verified successfully")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Cloudflare API requests."""
        if self.config.credentials.api_token:
            return {
                "Authorization": f"Bearer {self.config.credentials.api_token}",
                "Content-Type": "application/json",
            }
        elif self.config.credentials.email and self.config.credentials.api_key:
            return {
                "X-Auth-Email": self.config.credentials.email,
                "X-Auth-Key": self.config.credentials.api_key,
                "Content-Type": "application/json",
            }
        else:
            raise RuntimeError("Invalid Cloudflare credentials configuration")

    def package_code(
        self,
        directory: str,
        language_name: str,
        language_version: str,
        architecture: str,
        benchmark: str,
        is_cached: bool,
        container_deployment: bool,
    ) -> Tuple[str, int, str]:
        """
        Package code for Cloudflare Workers deployment.

        If container_deployment is True, builds and pushes a Docker image
        using wrangler and returns the image URI.
        
        If container_deployment is False, prepares the single script file
        for 'script' deployment.
        """
        
        if container_deployment:
            
            SERVER_FILES = {
                "python": "server.py",
                "nodejs": "server.js",
            }

            if language_name not in SERVER_FILES:
                raise NotImplementedError(
                    f"Container deployment for {language_name} is not supported."
                )

            # 1. Copy the language-specific web server wrapper
            server_wrapper_name = SERVER_FILES[language_name]
            sebs_template_dir = self.sebs_config.templates_dir
            
            server_wrapper_src = os.path.join(
                sebs_template_dir, "cloudflare", language_name, server_wrapper_name
            )
            server_wrapper_dst = os.path.join(directory, server_wrapper_name)

            if not os.path.exists(server_wrapper_src):
                raise RuntimeError(f"Missing server wrapper template at {server_wrapper_src}")
            
            shutil.copy2(server_wrapper_src, server_wrapper_dst)
            self.logging.info(f"Copied {server_wrapper_name} to build directory.")

            # 2. Build and push the image using the container client
            #    build_base_image is inherited from DockerContainer
            #    It will find the Dockerfile, build, check cache, and push
            _, container_uri = self.container_client.build_base_image(
                directory,
                language_name,
                language_version,
                architecture,
                benchmark,
                is_cached,
            )

            # For containers, the "package_path" is the build directory
            # and size is not relevant.
            return (directory, 0, container_uri)

        else:
            # Original logic for script-based deployment
            CONFIG_FILES = {
                "nodejs": "handler.js",
                "python": "handler.py",
            }

            if language_name not in CONFIG_FILES:
                raise NotImplementedError(
                    f"Language {language_name} is not yet supported for "
                    "script-based Cloudflare Workers"
                )

            # For script-based workers, the "package" is just the handler file itself.
            handler_file = CONFIG_FILES[language_name]
            package_path = os.path.join(directory, handler_file)

            if not os.path.exists(package_path):
                raise RuntimeError(f"Handler file {handler_file} not found in {directory}")

            bytes_size = os.path.getsize(package_path)
            mbytes = bytes_size / 1024.0 / 1024.0
            self.logging.info(f"Worker script package size: {mbytes:.2f} MB")

            return (package_path, bytes_size, "")
        
    def create_function_old(
        self,
        code_package: Benchmark,
        func_name: str,
        container_deployment: bool,
        container_uri: str,
    ) -> CloudflareWorker:
        """
        Create a new Cloudflare Worker.
        
        If a worker with the same name already exists, it will be updated.
        
        Args:
            code_package: Benchmark containing the function code
            func_name: Name of the worker
            container_deployment: Whether to deploy as container (not supported)
            container_uri: URI of container image (not used)
            
        Returns:
            CloudflareWorker instance
        """
        if container_deployment:
            raise NotImplementedError(
                "Container deployment is not supported for Cloudflare Workers"
            )

        package = code_package.code_location
        benchmark = code_package.benchmark
        language = code_package.language_name
        language_runtime = code_package.language_version
        function_cfg = FunctionConfig.from_benchmark(code_package)
        
        func_name = self.format_function_name(func_name)
        account_id = self.config.credentials.account_id
        
        if not account_id:
            raise RuntimeError("Cloudflare account ID is required to create workers")

        # Check if worker already exists
        existing_worker = self._get_worker(func_name, account_id)
        
        if existing_worker:
            self.logging.info(f"Worker {func_name} already exists, updating it")
            worker = CloudflareWorker(
                func_name,
                code_package.benchmark,
                func_name,  # script_id is the same as name
                code_package.hash,
                language_runtime,
                function_cfg,
                account_id,
            )
            self.update_function(worker, code_package, container_deployment, container_uri)
            worker.updated_code = True
        else:
            self.logging.info(f"Creating new worker {func_name}")
            
            # Read the worker script
            with open(package, 'r') as f:
                script_content = f.read()
            
            # Create the worker
            self._create_or_update_worker(func_name, script_content, account_id)
            
            worker = CloudflareWorker(
                func_name,
                code_package.benchmark,
                func_name,
                code_package.hash,
                language_runtime,
                function_cfg,
                account_id,
            )

        # Add LibraryTrigger and HTTPTrigger
        from sebs.cloudflare.triggers import LibraryTrigger, HTTPTrigger
        
        library_trigger = LibraryTrigger(func_name, self)
        library_trigger.logging_handlers = self.logging_handlers
        worker.add_trigger(library_trigger)
        
        # Cloudflare Workers are automatically accessible via HTTPS
        worker_url = f"https://{func_name}.{account_id}.workers.dev"
        http_trigger = HTTPTrigger(func_name, worker_url)
        http_trigger.logging_handlers = self.logging_handlers
        worker.add_trigger(http_trigger)

        return worker

    def create_function(
        self,
        code_package: Benchmark,
        func_name: str,
        container_deployment: bool,
        container_uri: str,
    ) -> CloudflareWorker:
        """
        Create a new Cloudflare Worker (either script or container-based).
        
        If a worker with the same name already exists, it will be updated.
        """
        
        language_runtime = code_package.language_version
        function_cfg = FunctionConfig.from_benchmark(code_package)
        
        func_name = self.format_function_name(func_name)
        account_id = self.config.credentials.account_id
        
        if not account_id:
            raise RuntimeError("Cloudflare account ID is required to create workers")

        worker = None
        
        if container_deployment:
            # ---- CONTAINER DEPLOYMENT ----
            # We must update/deploy every time for containers,
            # as we can't easily check the deployed image URI.
            self.logging.info(f"Creating/Updating container worker {func_name}")
            build_dir = code_package.code_location
            
            if not container_uri:
                 raise RuntimeError("container_uri is required for container deployment")

            self._deploy_container_worker(func_name, build_dir, container_uri)
            
            worker = CloudflareWorker(
                func_name,
                code_package.benchmark,
                func_name,
                code_package.hash,
                language_runtime,
                function_cfg,
                account_id,
            )
            worker.updated_code = True # We always update containers

        else:
            # ---- SCRIPT DEPLOYMENT (Original Logic) ----
            package = code_package.code_location
            
            # Check if worker already exists
            existing_worker = self._get_worker(func_name, account_id)
            
            if existing_worker:
                self.logging.info(f"Worker {func_name} already exists, updating it")
                worker = CloudflareWorker(
                    func_name,
                    code_package.benchmark,
                    func_name,  # script_id is the same as name
                    code_package.hash,
                    language_runtime,
                    function_cfg,
                    account_id,
                )
                self.update_function(worker, code_package, container_deployment, container_uri)
                worker.updated_code = True
            else:
                self.logging.info(f"Creating new worker {func_name}")
                
                # Read the worker script
                with open(package, 'r') as f:
                    script_content = f.read()
                
                # Create the worker
                # Use the RENAMED method here
                self._deploy_script_worker(func_name, script_content, account_id)
                
                worker = CloudflareWorker(
                    func_name,
                    code_package.benchmark,
                    func_name,
                    code_package.hash,
                    language_runtime,
                    function_cfg,
                    account_id,
                )

        # ---- COMMON LOGIC ----
        # Add LibraryTrigger and HTTPTrigger
        from sebs.cloudflare.triggers import LibraryTrigger, HTTPTrigger
        
        library_trigger = LibraryTrigger(func_name, self)
        library_trigger.logging_handlers = self.logging_handlers
        worker.add_trigger(library_trigger)
        
        # Cloudflare Workers are automatically accessible via HTTPS
        # This URL pattern works for both scripts and containers
        worker_url = f"https://{func_name}.{self.config.credentials.workers_dev_domain}"
        http_trigger = HTTPTrigger(func_name, worker_url)
        http_trigger.logging_handlers = self.logging_handlers
        worker.add_trigger(http_trigger)

        return worker
    def _get_worker(self, worker_name: str, account_id: str) -> Optional[dict]:
        """Get information about an existing worker."""
        headers = self._get_auth_headers()
        url = f"{self._api_base_url}/accounts/{account_id}/workers/scripts/{worker_name}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json().get("result")
        elif response.status_code == 404:
            return None
        else:
            raise RuntimeError(
                f"Failed to check worker existence: {response.status_code} - {response.text}"
            )

    def _deploy_script_worker(
        self, worker_name: str, script_content: str, account_id: str
    ) -> dict:
        """Create or update a Cloudflare Worker."""
        headers = self._get_auth_headers()
        # Remove Content-Type as we're sending form data
        headers.pop("Content-Type", None)
        
        url = f"{self._api_base_url}/accounts/{account_id}/workers/scripts/{worker_name}"
        
        # Cloudflare Workers API expects the script as form data
        files = {
            'script': ('worker.js', script_content, 'application/javascript'),
        }
        
        response = requests.put(url, headers=headers, files=files)
        
        if response.status_code not in [200, 201]:
            raise RuntimeError(
                f"Failed to create/update worker: {response.status_code} - {response.text}"
            )
        
        return response.json().get("result", {})
    
    def _create_or_update_worker(
        self, worker_name: str, script_content: str, account_id: str
    ) -> dict:
        """Create or update a Cloudflare Worker."""
        headers = self._get_auth_headers()
        # Remove Content-Type as we're sending form data
        headers.pop("Content-Type", None)
        
        url = f"{self._api_base_url}/accounts/{account_id}/workers/scripts/{worker_name}"
        
        # Cloudflare Workers API expects the script as form data
        files = {
            'script': ('worker.js', script_content, 'application/javascript'),
        }
        
        response = requests.put(url, headers=headers, files=files)
        
        if response.status_code not in [200, 201]:
            raise RuntimeError(
                f"Failed to create/update worker: {response.status_code} - {response.text}"
            )
        
        return response.json().get("result", {})

    def cached_function(self, function: Function):
        """
        Handle a function retrieved from cache.
        
        Refreshes triggers and logging handlers.
        
        Args:
            function: The cached function
        """
        from sebs.cloudflare.triggers import LibraryTrigger, HTTPTrigger
        
        for trigger in function.triggers(Trigger.TriggerType.LIBRARY):
            trigger.logging_handlers = self.logging_handlers
            cast(LibraryTrigger, trigger).deployment_client = self
            
        for trigger in function.triggers(Trigger.TriggerType.HTTP):
            trigger.logging_handlers = self.logging_handlers

    def update_function_old(
        self,
        function: Function,
        code_package: Benchmark,
        container_deployment: bool,
        container_uri: str,
    ):
        """
        Update an existing Cloudflare Worker.
        
        Args:
            function: Existing function instance to update
            code_package: New benchmark containing the function code
            container_deployment: Whether to deploy as container (not supported)
            container_uri: URI of container image (not used)
        """
        if container_deployment:
            raise NotImplementedError(
                "Container deployment is not supported for Cloudflare Workers"
            )

        worker = cast(CloudflareWorker, function)
        package = code_package.code_location
        
        # Read the updated script
        with open(package, 'r') as f:
            script_content = f.read()
        
        # Update the worker
        account_id = worker.account_id or self.config.credentials.account_id
        if not account_id:
            raise RuntimeError("Account ID is required to update worker")
        
        self._create_or_update_worker(worker.name, script_content, account_id)
        self.logging.info(f"Updated worker {worker.name}")
        
        # Update configuration if needed
        self.update_function_configuration(worker, code_package)

    def update_function(
        self,
        function: Function,
        code_package: Benchmark,
        container_deployment: bool,
        container_uri: str,
    ):
        """
        Update an existing Cloudflare Worker.
        """
        
        worker = cast(CloudflareWorker, function)
        account_id = worker.account_id or self.config.credentials.account_id
        if not account_id:
            raise RuntimeError("Account ID is required to update worker")

        if container_deployment:
            # ---- CONTAINER UPDATE ----
            self.logging.info(f"Updating container worker {worker.name}")
            build_dir = code_package.code_location
            
            if not container_uri:
                 raise RuntimeError("container_uri is required for container deployment")

            self._deploy_container_worker(worker.name, build_dir, container_uri)
            self.logging.info(f"Updated container worker {worker.name}")

        else:
            # ---- SCRIPT UPDATE (Original Logic) ----
            package = code_package.code_location
            
            # Read the updated script
            with open(package, 'r') as f:
                script_content = f.read()
            
            # Update the worker using the RENAMED method
            self._deploy_script_worker(worker.name, script_content, account_id)
            self.logging.info(f"Updated script worker {worker.name}")
        
        # Update configuration if needed
        self.update_function_configuration(worker, code_package)

    def update_function_configuration(
        self, cached_function: Function, benchmark: Benchmark
    ):
        """
        Update the configuration of a Cloudflare Worker.
        
        Note: Cloudflare Workers have limited configuration options compared
        to traditional FaaS platforms. Memory and timeout are managed by Cloudflare.
        
        Args:
            cached_function: The function to update
            benchmark: The benchmark with new configuration
        """
        # Cloudflare Workers have fixed resource limits:
        # - CPU time: 50ms (free), 50ms-30s (paid)
        # - Memory: 128MB
        # Most configuration is handled via wrangler.toml or API settings
        
        worker = cast(CloudflareWorker, cached_function)
        
        # For environment variables or KV namespaces, we would use the API here
        # For now, we'll just log that configuration update was requested
        self.logging.info(
            f"Configuration update requested for worker {worker.name}. "
            "Note: Cloudflare Workers have limited runtime configuration options."
        )

    def default_function_name(self, code_package: Benchmark, resources=None) -> str:
        """
        Generate a default function name for Cloudflare Workers.
        
        Args:
            code_package: The benchmark package
            resources: Optional resources (not used)
            
        Returns:
            Default function name
        """
        # Cloudflare Worker names must be lowercase and can contain hyphens
        return (
            f"{code_package.benchmark}-{code_package.language_name}-"
            f"{code_package.language_version.replace('.', '')}"
        ).lower()

    @staticmethod
    def format_function_name(name: str) -> str:
        """
        Format a function name to comply with Cloudflare Worker naming rules.
        
        Worker names must:
        - Be lowercase
        - Contain only alphanumeric characters and hyphens
        - Not start or end with a hyphen
        
        Args:
            name: The original name
            
        Returns:
            Formatted name
        """
        # Convert to lowercase and replace invalid characters
        formatted = name.lower().replace('_', '-').replace('.', '-')
        # Remove any characters that aren't alphanumeric or hyphen
        formatted = ''.join(c for c in formatted if c.isalnum() or c == '-')
        # Remove leading/trailing hyphens
        formatted = formatted.strip('-')
        return formatted

    def enforce_cold_start(self, functions: List[Function], code_package: Benchmark):
        """
        Enforce cold start for Cloudflare Workers.
        
        Note: Cloudflare Workers don't have a traditional cold start mechanism
        like AWS Lambda. Workers are instantiated on-demand at edge locations.
        We can't force a cold start, but we can update the worker to invalidate caches.
        
        Args:
            functions: List of functions to enforce cold start on
            code_package: The benchmark package
        """
        self.logging.warning(
            "Cloudflare Workers do not support forced cold starts. "
            "Workers are automatically instantiated on-demand at edge locations."
        )

    def download_metrics(
        self,
        function_name: str,
        start_time: int,
        end_time: int,
        requests: Dict[str, ExecutionResult],
        metrics: dict,
    ):
        """
        Download per-invocation metrics from Cloudflare Analytics Engine.
        
        Queries Analytics Engine SQL API to retrieve performance data for each
        invocation and enriches the ExecutionResult objects with provider metrics.
        
        Note: Requires Analytics Engine binding to be configured on the worker
        and benchmark code to write data points during execution.
        
        Args:
            function_name: Name of the worker
            start_time: Start time (Unix timestamp in seconds)
            end_time: End time (Unix timestamp in seconds)
            requests: Dict mapping request_id -> ExecutionResult
            metrics: Dict to store aggregated metrics
        """
        if not requests:
            self.logging.warning("No requests to download metrics for")
            return
        
        account_id = self.config.credentials.account_id
        if not account_id:
            self.logging.error("Account ID required to download metrics")
            return
        
        self.logging.info(
            f"Downloading Analytics Engine metrics for {len(requests)} invocations "
            f"of worker {function_name}"
        )
        
        try:
            # Query Analytics Engine for per-invocation metrics
            metrics_data = self._query_analytics_engine(
                account_id, start_time, end_time, function_name
            )
            
            if not metrics_data:
                self.logging.warning(
                    "No metrics data returned from Analytics Engine. "
                    "Ensure the worker has Analytics Engine binding configured "
                    "and is writing data points during execution."
                )
                return
            
            # Match metrics with invocation requests
            matched = 0
            unmatched_metrics = 0
            
            for row in metrics_data:
                request_id = row.get('request_id')
                
                if request_id and request_id in requests:
                    result = requests[request_id]
                    
                    # Populate provider times (convert ms to microseconds)
                    wall_time_ms = row.get('wall_time_ms', 0)
                    cpu_time_ms = row.get('cpu_time_ms', 0)
                    
                    result.provider_times.execution = int(cpu_time_ms * 1000)  # μs
                    result.provider_times.initialization = 0  # Not separately tracked
                    
                    # Populate stats
                    result.stats.cold_start = (row.get('cold_warm') == 'cold')
                    result.stats.memory_used = 128.0  # Cloudflare Workers: fixed 128MB
                    
                    # Populate billing info
                    # Cloudflare billing: $0.50 per million requests + 
                    # $12.50 per million GB-seconds of CPU time
                    result.billing.memory = 128
                    result.billing.billed_time = int(cpu_time_ms * 1000)  # μs
                    
                    # GB-seconds calculation: (128MB / 1024MB/GB) * (cpu_time_ms / 1000ms/s)
                    gb_seconds = (128.0 / 1024.0) * (cpu_time_ms / 1000.0)
                    result.billing.gb_seconds = int(gb_seconds * 1000000)  # micro GB-seconds
                    
                    matched += 1
                elif request_id:
                    unmatched_metrics += 1
            
            # Calculate statistics from matched metrics
            if matched > 0:
                cpu_times = [
                    requests[rid].provider_times.execution 
                    for rid in requests 
                    if requests[rid].provider_times.execution > 0
                ]
                cold_starts = sum(
                    1 for rid in requests if requests[rid].stats.cold_start
                )
                
                metrics['cloudflare'] = {
                    'total_invocations': len(metrics_data),
                    'matched_invocations': matched,
                    'unmatched_invocations': len(requests) - matched,
                    'unmatched_metrics': unmatched_metrics,
                    'cold_starts': cold_starts,
                    'warm_starts': matched - cold_starts,
                    'data_source': 'analytics_engine',
                    'note': 'Per-invocation metrics from Analytics Engine'
                }
                
                if cpu_times:
                    metrics['cloudflare']['avg_cpu_time_us'] = sum(cpu_times) // len(cpu_times)
                    metrics['cloudflare']['min_cpu_time_us'] = min(cpu_times)
                    metrics['cloudflare']['max_cpu_time_us'] = max(cpu_times)
            
            self.logging.info(
                f"Analytics Engine metrics: matched {matched}/{len(requests)} invocations"
            )
            
            if matched < len(requests):
                missing = len(requests) - matched
                self.logging.warning(
                    f"{missing} invocations not found in Analytics Engine. "
                    "This may be due to:\n"
                    "  - Analytics Engine ingestion delay (typically <60s)\n"
                    "  - Worker not writing data points correctly\n"
                    "  - Analytics Engine binding not configured"
                )
            
            if unmatched_metrics > 0:
                self.logging.warning(
                    f"{unmatched_metrics} metrics found in Analytics Engine "
                    "that don't match tracked request IDs (possibly from other sources)"
                )
        
        except Exception as e:
            self.logging.error(f"Failed to download metrics: {e}")
            self.logging.warning(
                "Continuing without Analytics Engine metrics. "
                "Client-side timing data is still available."
            )

    def _deploy_container_worker(
        self, worker_name: str, build_dir: str, container_uri: str
    ):
        """
        Deploys a container-based worker using `wrangler`.
        
        This function generates a loader script and a wrangler.toml,
        then executes `wrangler deploy`.

        Args:
            worker_name: The name for the worker.
            build_dir: The build context directory (where Dockerfile is).
            container_uri: The full URI of the pushed container image.
        """
        self.logging.info(f"Deploying container {container_uri} to worker {worker_name}")

        # 1. Generate wrangler.toml
        #    Note: We use a fixed compatibility date. This could be configurable.
        toml_content = f"""
name = "{worker_name}"
main = "loader.js"
compatibility_date = "2024-05-01"

[[containers]]
binding = "MY_CONTAINER"
image = "{container_uri}"
"""
        toml_path = os.path.join(build_dir, "wrangler.toml")
        with open(toml_path, "w") as f:
            f.write(toml_content)

        # 2. Generate loader.js entrypoint script
        #    This script forwards requests to the container.
        loader_content = """
export default {
  async fetch(request, env, ctx) {
    // getByName("instance") creates/gets a proxy to the container instance
    const container = env.MY_CONTAINER.getByName("instance");
    // Forward the original request to the container
    return container.fetch(request);
  },
};
"""
        loader_path = os.path.join(build_dir, "loader.js")
        with open(loader_path, "w") as f:
            f.write(loader_content)
        
        # 3. Get API token for wrangler
        api_token = self.config.credentials.api_token
        if not api_token:
            raise RuntimeError("Cloudflare API token is required to deploy with wrangler.")

        push_env = os.environ.copy()
        push_env["CLOUDFLARE_API_TOKEN"] = api_token

        cmd = ["wrangler", "deploy"]
        
        try:
            process = subprocess.run(
                cmd,
                env=push_env,
                cwd=build_dir, # Run from the build directory
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.logging.info(f"Wrangler deploy stdout: {process.stdout}")
            self.logging.info(f"Successfully deployed container worker {worker_name}")

        except subprocess.CalledProcessError as e:
            self.logging.error(f"Failed to deploy container worker {worker_name} with wrangler.")
            self.logging.error(f"Wrangler return code: {e.returncode}")
            self.logging.error(f"Wrangler stdout: {e.stdout}")
            self.logging.error(f"Wrangler stderr: {e.stderr}")
            raise RuntimeError(f"Wrangler deploy failed: {e.stderr}")
        except FileNotFoundError:
            self.logging.error("`wrangler` command not found.")
            raise RuntimeError(
                "`wrangler` CLI is not installed or not in PATH. "
                "It is required for Cloudflare container operations."
            )

    def _query_analytics_engine(
        self, 
        account_id: str, 
        start_time: int, 
        end_time: int,
        script_name: str
    ) -> List[dict]:
        """
        Query Analytics Engine SQL API for worker metrics.
        
        Retrieves per-invocation metrics written by the worker during execution.
        The worker must write data points with the following schema:
        - index1: request_id (unique identifier)
        - index2: cold_warm ("cold" or "warm")
        - double1: wall_time_ms (wall clock time in milliseconds)
        - double2: cpu_time_ms (CPU time in milliseconds)
        - blob1: url (request URL)
        - blob2: status ("success" or "error")
        - blob3: error_message (if applicable)
        
        Args:
            account_id: Cloudflare account ID
            start_time: Unix timestamp (seconds)
            end_time: Unix timestamp (seconds)
            script_name: Worker script name
            
        Returns:
            List of metric data points, one per invocation
        """
        headers = self._get_auth_headers()
        url = f"{self._api_base_url}/accounts/{account_id}/analytics_engine/sql"
        
        # Convert Unix timestamps to DateTime format for ClickHouse
        from datetime import datetime
        start_dt = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
        end_dt = datetime.utcfromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
        
        # SQL query for Analytics Engine
        # Note: Analytics Engine uses ClickHouse SQL syntax
        sql_query = f"""
        SELECT 
          index1 as request_id,
          index2 as cold_warm,
          double1 as wall_time_ms,
          double2 as cpu_time_ms,
          blob1 as url,
          blob2 as status,
          blob3 as error_message,
          timestamp
        FROM ANALYTICS_DATASET
        WHERE timestamp >= toDateTime('{start_dt}')
          AND timestamp <= toDateTime('{end_dt}')
          AND blob1 LIKE '%{script_name}%'
        ORDER BY timestamp ASC
        """
        
        try:
            # Analytics Engine SQL API returns newline-delimited JSON
            response = requests.post(
                url, 
                headers=headers, 
                data=sql_query,
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse newline-delimited JSON response
                results = []
                for line in response.text.strip().split('\n'):
                    if line:
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            self.logging.warning(f"Failed to parse Analytics Engine line: {line}")
                
                self.logging.info(f"Retrieved {len(results)} data points from Analytics Engine")
                return results
            else:
                raise RuntimeError(
                    f"Analytics Engine query failed: {response.status_code} - {response.text}"
                )
        
        except requests.exceptions.Timeout:
            self.logging.error("Analytics Engine query timed out")
            return []
        except Exception as e:
            self.logging.error(f"Analytics Engine query error: {e}")
            return []

    def create_trigger(
        self, function: Function, trigger_type: Trigger.TriggerType
    ) -> Trigger:
        """
        Create a trigger for a Cloudflare Worker.
        
        Args:
            function: The function to create a trigger for
            trigger_type: Type of trigger to create
            
        Returns:
            The created trigger
        """
        from sebs.cloudflare.triggers import LibraryTrigger, HTTPTrigger
        
        worker = cast(CloudflareWorker, function)
        
        if trigger_type == Trigger.TriggerType.LIBRARY:
            trigger = LibraryTrigger(worker.name, self)
            trigger.logging_handlers = self.logging_handlers
            return trigger
        elif trigger_type == Trigger.TriggerType.HTTP:
            account_id = worker.account_id or self.config.credentials.account_id
            worker_url = f"https://{worker.name}.{account_id}.workers.dev"
            trigger = HTTPTrigger(worker.name, worker_url)
            trigger.logging_handlers = self.logging_handlers
            return trigger
        else:
            raise NotImplementedError(
                f"Trigger type {trigger_type} is not supported for Cloudflare Workers"
            )

    def shutdown(self) -> None:
        """
        Shutdown the Cloudflare system.
        
        Saves configuration to cache.
        """
        try:
            self.cache_client.lock()
            self.config.update_cache(self.cache_client)
        finally:
            self.cache_client.unlock()


    def delete_function(self, function: Function):
        """
        Delete a Cloudflare Worker.

        Args:
            function: The function to delete
        """
        worker = cast(CloudflareWorker, function)
        worker_name = worker.name
        account_id = worker.account_id or self.config.credentials.account_id

        if not account_id:
            self.logging.error(f"Account ID is required to delete worker {worker_name}")
            raise RuntimeError(f"Account ID is required to delete worker {worker_name}")

        self.logging.info(f"Deleting worker {worker_name}")

        headers = self._get_auth_headers()
        url = f"{self._api_base_url}/accounts/{account_id}/workers/scripts/{worker_name}"

        try:
            response = requests.delete(url, headers=headers, timeout=10)

            # 200 OK (with result) or 204 No Content (no result) are both success
            if response.status_code in [200, 204]:
                self.logging.info(f"Successfully deleted worker {worker_name}")
            elif response.status_code == 404:
                self.logging.warning(
                    f"Worker {worker_name} not found during deletion, "
                    "assuming it was already deleted."
                )
            else:
                # Raise an error for other unexpected statuses
                raise RuntimeError(
                    f"Failed to delete worker {worker_name}: "
                    f"{response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
            self.logging.error(f"Network error while deleting worker {worker_name}: {e}")
            raise RuntimeError(f"Error deleting worker {worker_name}") from e
