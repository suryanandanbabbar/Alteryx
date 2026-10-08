"""Adapters for environment-specific licensing providers."""

from .databricks import DatabricksSecretProvider

__all__ = ["DatabricksSecretProvider"]
