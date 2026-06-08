import logging
from typing import Any

logger = logging.getLogger("app_skeleton.security")
logger.setLevel(logging.INFO)

# Optional: Add file handler if needed, currently uses default stream
# handler which FastAPI configures, but could be specific to security logs.

def log_failed_auth(detail: str, ip_address: str = "unknown") -> None:
    logger.warning(f"SECURITY: Failed authentication - {detail} (IP: {ip_address})")

def log_denied_access(email: str, resource: str, action: str, ip_address: str = "unknown") -> None:
    logger.warning(f"SECURITY: Denied access - User {email} attempted {action} on {resource} (IP: {ip_address})")

def log_file_download(email: str, logical_path: str) -> None:
    logger.info(f"SECURITY: File access - User {email} downloaded {logical_path}")

def log_image_access(email: str, asset_id: str, action: str) -> None:
    logger.info(f"SECURITY: Image access - User {email} {action} asset {asset_id}")

def log_delete_operation(email: str, resource_type: str, resource_id: str) -> None:
    logger.info(f"SECURITY: Delete operation - User {email} deleted {resource_type} {resource_id}")

def log_admin_operation(email: str, action: str, target: str) -> None:
    logger.info(f"SECURITY: Admin operation - Admin {email} performed {action} on {target}")

def log_dev_bypass_attempt(ip_address: str = "unknown") -> None:
    logger.warning(f"SECURITY: Dev bypass attempted - Auth skip header provided in production (IP: {ip_address})")
