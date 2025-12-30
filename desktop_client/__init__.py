# Desktop Client for Leitor de Simulados

from .client import DesktopClient
from .api_client import APIClient, APIError

__all__ = ["DesktopClient", "APIClient", "APIError"]
