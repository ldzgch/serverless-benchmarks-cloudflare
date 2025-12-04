import os
import requests
import subprocess
import docker
from typing import Dict, Tuple

from sebs.cloudflare.config import CloudflareConfig
from sebs.config import SeBSConfig
from sebs.faas.container import DockerContainer


class CloudflareContainer(DockerContainer):
    """
    Manages Docker container builds and pushes to Cloudflare Container Registry.
    
    This class handles:
    - Constructing the correct image URI for Cloudflare.
    - Checking if an image already exists in the registry using the Cloudflare API.
    - Pushing images using the `wrangler` CLI, which handles authentication.
    """

    @staticmethod
    def name():
        return "cloudflare"

    @staticmethod
    def typename() -> str:
        return "Cloudflare.Container"

    def __init__(
        self,
        system_config: SeBSConfig,
        config: CloudflareConfig,
        docker_client: docker.client.DockerClient,
    ):
        """
        Initializes the CloudflareContainer client.
        
        Args:
            system_config: General SeBS configuration.
            config: Cloudflare-specific configuration.
            docker_client: An initialized Docker client instance.
        """
        super().__init__(system_config, docker_client)
        self.config = config
        self._api_base_url = "https://api.cloudflare.com/client/v4"

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for Cloudflare API requests.
        
        Note: This is for registry *inspection*. Pushing is handled by wrangler.
        """
        if self.config.credentials.api_token:
            return {
                "Authorization": f"Bearer {self.config.credentials.api_token}",
                "Content-Type": "application/json",
            }
        else:
            raise RuntimeError("Cloudflare API token is not configured (api_token)")

    def registry_name(
        self, benchmark: str, language_name: str, language_version: str, architecture: str
    ) -> Tuple[str, str, str, str]:
        """
        Generates the registry, repository, tag, and full URI for a Cloudflare image.

        Args:
            benchmark: The name of the benchmark.
            language_name: The programming language.
            language_version: The language version.
            architecture: The CPU architecture.

        Returns:
            A tuple containing (registry_url, repository_name, image_tag, image_uri).
        """
        account_id = self.config.credentials.account_id
        if not account_id:
            raise RuntimeError("Cloudflare account ID is not configured (account_id)")

        # e.g., registry.cloudflare.com/your-account-id
        registry_url = f"registry.cloudflare.com/{account_id}"

        # e.g., sebs-110-video-processing-nodejs
        repository_name = (
            f"sebs-{benchmark}-{language_name}".lower().replace("_", "-")
        )

        # e.g., 18-x64
        image_tag = f"{language_version}-{architecture}".lower().replace(".", "-")

        # e.g., registry.cloudflare.com/your-account-id/sebs-110-video-processing-nodejs:18-x64
        image_uri = f"{registry_url}/{repository_name}:{image_tag}" 

        return registry_url, repository_name, image_tag, image_uri

    def find_image(self, repository_name: str, image_tag: str) -> bool:
        """
        Checks if a specific image tag exists in the Cloudflare Container Registry.

        Args:
            repository_name: The name of the repository (e.g., "sebs-video-processing-nodejs").
            image_tag: The image tag (e.g., "18-x64").

        Returns:
            True if the image exists, False otherwise.
        """
        headers = self._get_auth_headers()
        account_id = self.config.credentials.account_id
        url = (
            f"{self._api_base_url}/accounts/{account_id}/registry/repositories/"
            f"{repository_name}/images"
        )

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 404:
                # Repository itself doesn't exist, so the image can't.
                self.logging.info(f"Repository {repository_name} not found.")
                return False

            # Raise an exception for other HTTP errors
            response.raise_for_status()

            data = response.json()
            for image in data.get("result", {}).get("images", []):
                if image_tag in image.get("tags", []):
                    self.logging.info(f"Found existing image {repository_name}:{image_tag}")
                    return True

            self.logging.info(f"Image tag {image_tag} not found in {repository_name}")
            return False

        except requests.exceptions.RequestException as e:
            self.logging.error(f"Failed to query Cloudflare Registry API: {e}")
            # If we can't check, assume it doesn't exist to force a new build/push
            return False


        return registry_url, repository_name, image_tag, image_uri

    def find_image(self, repository_name: str, image_tag: str) -> bool:
        """
        Checks if a specific image tag exists in the Cloudflare Container Registry.

        Args:
            repository_name: The name of the repository (e.g., "sebs-video-processing-nodejs").
            image_tag: The image tag (e.g., "18-x64").

        Returns:
            True if the image exists, False otherwise.
        """
        headers = self._get_auth_headers()
        account_id = self.config.credentials.account_id
        url = (
            f"{self._api_base_url}/accounts/{account_id}/registry/repositories/"
            f"{repository_name}/images"
        )

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 404:
                # Repository itself doesn't exist, so the image can't.
                self.logging.info(f"Repository {repository_name} not found.")
                return False

            # Raise an exception for other HTTP errors
            response.raise_for_status()

            data = response.json()
            for image in data.get("result", {}).get("images", []):
                if image_tag in image.get("tags", []):
                    self.logging.info(f"Found existing image {repository_name}:{image_tag}")
                    return True

            self.logging.info(f"Image tag {image_tag} not found in {repository_name}")
            return False

        except requests.exceptions.RequestException as e:
            self.logging.error(f"Failed to query Cloudflare Registry API: {e}")
            # If we can't check, assume it doesn't exist to force a new build/push
            return False

    def push_image(self, repository_uri: str, image_tag: str):
        """
        Pushes a locally-built Docker image to the Cloudflare Container Registry.
        
        This method uses the `wrangler` CLI, which must be installed.
        It assumes the base `DockerContainer.build_image` has already built
        and tagged the image with the full remote URI.
        
        Args:
            repository_uri: The full repository URI (e.g., "registry.cloudflare.com/account-id/repo-name").
            image_tag: The image tag (e.g., "18-x64").
        """
        if ':' in repository_uri:
            base_image_name = repository_uri.split(':')[0]
            final_image_tag = image_tag
        else:
            base_image_name = repository_uri
            final_image_tag = image_tag

        full_image_name = f"{base_image_name}:{final_image_tag}"
        
        self.logging.info(f"Pushing image {full_image_name} to Cloudflare using wrangler...")

        api_token = self.config.credentials.api_token
        if not api_token:
            raise RuntimeError("Cloudflare API token is required to push images with wrangler.")

        # Set the API token in the environment for the wrangler subprocess
        push_env = os.environ.copy()
        push_env["CLOUDFLARE_API_TOKEN"] = api_token

# We assume the image is already built and tagged locally with `full_image_name`
        # by the DockerContainer.build_image method.
        cmd = ["wrangler", "containers", "push", full_image_name]

        try:
            # We use subprocess.run for a blocking call
            process = subprocess.run(
                cmd,
                env=push_env,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.logging.info(f"Wrangler output: {process.stdout}")
            self.logging.info(f"Successfully pushed image {full_image_name}")

        except subprocess.CalledProcessError as e:
            self.logging.error(f"Failed to push image {full_image_name} with wrangler.")
            self.logging.error(f"Wrangler return code: {e.returncode}")
            self.logging.error(f"Wrangler stdout: {e.stdout}")
            self.logging.error(f"Wrangler stderr: {e.stderr}")
            raise RuntimeError(f"Wrangler push failed: {e.stderr}")
        except FileNotFoundError:
            self.logging.error("`wrangler` command not found.")
            raise RuntimeError(
                "`wrangler` CLI is not installed or not in PATH. "
                "It is required for Cloudflare container operations."
            )