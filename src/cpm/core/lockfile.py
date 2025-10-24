"""
Lockfile manager for reproducible installations (cpm-lock.json)
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

from cpm.core.schema import ServerConfig

logger = logging.getLogger(__name__)


class ServerLock(BaseModel):
    """Locked server information"""

    version: str
    resolved: str  # Registry URL or source
    integrity: str  # SHA512 hash
    installation: Dict  # Installation config snapshot


class Lockfile(BaseModel):
    """Lockfile structure (cpm-lock.json)"""

    lockfileVersion: int = 1
    generated: str  # ISO timestamp
    servers: Dict[str, ServerLock] = {}


class LockfileManager:
    """Manages cpm-lock.json for reproducible installs"""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path

    def load(self) -> Optional[Lockfile]:
        """Load lockfile"""
        if not self.lock_path.exists():
            return None

        try:
            with open(self.lock_path, "r") as f:
                data = json.load(f)
            return Lockfile(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load lockfile: {e}")
            return None

    def save(self, lockfile: Lockfile):
        """Save lockfile"""
        lockfile.generated = datetime.utcnow().isoformat() + "Z"

        with open(self.lock_path, "w") as f:
            json.dump(lockfile.model_dump(), f, indent=2)

        logger.info(f"Saved lockfile: {self.lock_path}")

    def add_server(
        self,
        name: str,
        version: str,
        resolved: str,
        server_config: ServerConfig,
    ):
        """Add or update server in lockfile"""
        lockfile = self.load() or Lockfile()

        # Generate integrity hash
        integrity = self._generate_integrity(server_config)

        # Create lock entry
        lock = ServerLock(
            version=version,
            resolved=resolved,
            integrity=integrity,
            installation=server_config.model_dump(),
        )

        lockfile.servers[name] = lock
        self.save(lockfile)

        logger.debug(f"Added {name}@{version} to lockfile")

    def remove_server(self, name: str):
        """Remove server from lockfile"""
        lockfile = self.load()
        if not lockfile:
            return

        if name in lockfile.servers:
            del lockfile.servers[name]
            self.save(lockfile)
            logger.debug(f"Removed {name} from lockfile")

    def get_server(self, name: str) -> Optional[ServerLock]:
        """Get locked server info"""
        lockfile = self.load()
        if not lockfile:
            return None

        return lockfile.servers.get(name)

    def verify_integrity(self, name: str, server_config: ServerConfig) -> bool:
        """Verify server matches lockfile integrity"""
        lock = self.get_server(name)
        if not lock:
            return False

        current_integrity = self._generate_integrity(server_config)
        return current_integrity == lock.integrity

    def _generate_integrity(self, server_config: ServerConfig) -> str:
        """Generate SHA512 hash of server config"""
        # Serialize config
        config_json = json.dumps(server_config.model_dump(), sort_keys=True)

        # Generate hash
        hash_obj = hashlib.sha512(config_json.encode())
        return f"sha512-{hash_obj.hexdigest()}"

    def get_all_locked_servers(self) -> Dict[str, ServerLock]:
        """Get all locked servers"""
        lockfile = self.load()
        if not lockfile:
            return {}

        return lockfile.servers

    def is_frozen(self) -> bool:
        """Check if lockfile exists (for --frozen-lockfile)"""
        return self.lock_path.exists()

    def validate(self) -> tuple[bool, List[str]]:
        """Validate lockfile integrity"""
        lockfile = self.load()
        if not lockfile:
            return False, ["Lockfile not found"]

        errors = []

        # Check version
        if lockfile.lockfileVersion != 1:
            errors.append(f"Unsupported lockfile version: {lockfile.lockfileVersion}")

        # Check servers
        if not lockfile.servers:
            errors.append("No servers in lockfile")

        return len(errors) == 0, errors
