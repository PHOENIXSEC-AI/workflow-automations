#!/usr/bin/env python3
"""
Utility for managing Prefect secrets.
Provides a simple CLI and Python API for creating, retrieving, updating, and deleting Prefect secrets.

Usage:
    python secrets_manager.py create SECRET_NAME SECRET_VALUE
    python secrets_manager.py get SECRET_NAME 
    python secrets_manager.py list
    python secrets_manager.py delete SECRET_NAME
    python secrets_manager.py update SECRET_NAME NEW_SECRET_VALUE

Or import the SecretsManager class for programmatic use.
"""
import argparse
from typing import Optional

from prefect.blocks.system import Secret
from core.utils import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)


class SecretsManager:
    """Utility class for managing Prefect secrets."""

    @staticmethod
    def create_secret(name: str, value: str) -> bool:
        """
        Create a new secret in Prefect's block storage.

        Args:
            name: The name to identify the secret
            value: The secret value to store

        Returns:
            bool: True if successful, False if a secret with this name already exists
        """
        try:
            # Check if secret already exists
            try:
                Secret.load(name)
                # msg = f"Secret '{name}' already exists. Use update if you want to change its value."
                # print()
                logger.info(
                    f"Secret '{name}' already exists. Use update if you want to change its value.")
                return False
            except ValueError:
                # Expected if secret doesn't exist yet
                pass

            # Create and save the secret
            secret_block = Secret(value=value)
            secret_block.save(name=name, overwrite=False)
            logger.info(f"Secret '{name}' created successfully.")
            return True
        except Exception as e:
            logger.error(f"Error creating secret: {e}")
            return False

    @staticmethod
    def get_secret(name: str) -> Optional[str]:
        """
        Retrieve a secret value by name.

        Args:
            name: The name of the secret to retrieve

        Returns:
            Optional[str]: The secret value or None if not found
        """
        try:
            secret_block = Secret.load(name)
            value = secret_block.get()
            # Only show first 3 characters for security in console output
            masked_value = value[:3] + '*' * \
                (len(value) - 3) if len(value) > 3 else '***'
            logger.info(f"Retrieved secret '{name}': {masked_value}")
            return value
        except ValueError:
            logger.warning(f"Secret '{name}' not found.")
            return None
        except Exception as e:
            logger.error(f"Error retrieving secret: {e}")
            return None

    @staticmethod
    def update_secret(name: str, value: str) -> bool:
        """
        Update an existing secret's value.

        Args:
            name: The name of the secret to update
            value: The new secret value

        Returns:
            bool: True if successful, False if the secret doesn't exist or update failed
        """
        try:
            # Check if secret exists
            try:
                Secret.load(name)
            except ValueError:
                logger.warning(f"Secret '{name}' not found. Create it first.")
                return False

            # Update the secret
            secret_block = Secret(value=value)
            secret_block.save(name=name, overwrite=True)
            logger.info(f"Secret '{name}' updated successfully.")
            return True
        except Exception as e:
            logger.error(f"Error updating secret: {e}")
            return False

    @staticmethod
    def delete_secret(name: str) -> bool:
        """
        Delete a secret by name.

        Args:
            name: The name of the secret to delete

        Returns:
            bool: True if successful, False if the secret doesn't exist or deletion failed
        """
        try:
            # Check if secret exists
            try:
                secret_block = Secret.load(name)
            except ValueError:
                logger.warning(f"Secret '{name}' not found.")
                return False

            # Delete the secret
            secret_block.delete()
            logger.info(f"Secret '{name}' deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Error deleting secret: {e}")
            return False


def main():
    """Command-line interface for the secrets manager."""
    parser = argparse.ArgumentParser(description="Manage Prefect secrets")

    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new secret")
    create_parser.add_argument("name", help="Secret name")
    create_parser.add_argument("value", help="Secret value")

    # Get command
    get_parser = subparsers.add_parser("get", help="Retrieve a secret")
    get_parser.add_argument("name", help="Secret name")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a secret")
    delete_parser.add_argument("name", help="Secret name")

    # Update command
    update_parser = subparsers.add_parser(
        "update", help="Update an existing secret")
    update_parser.add_argument("name", help="Secret name")
    update_parser.add_argument("value", help="New secret value")

    args = parser.parse_args()

    if args.command == "create":
        SecretsManager.create_secret(args.name, args.value)
    elif args.command == "get":
        SecretsManager.get_secret(args.name)
    elif args.command == "delete":
        SecretsManager.delete_secret(args.name)
    elif args.command == "update":
        SecretsManager.update_secret(args.name, args.value)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
