"""Registry for job source connectors with capability introspection."""
from typing import Dict, List, Optional
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.connectors.remoteok import RemoteOKConnector
from app.jobs.connectors.jobicy import JobicyConnector
from app.jobs.connectors.arbeitnow import ArbeitnowConnector
from app.jobs.connectors.greenhouse import GreenhouseConnector
from app.jobs.connectors.lever import LeverConnector
from app.jobs.connectors.ashby import AshbyConnector
from app.jobs.connectors.smartrecruiters import SmartRecruitersConnector
from app.jobs.connectors.linkedin import LinkedInConnector
from app.jobs.connectors.internshala import InternshalaConnector
from app.jobs.connectors.glassdoor import GlassdoorConnector


class JobSourceRegistry:
    """Manages connector instances and allows dynamic lookup and capability introspection."""

    def __init__(self):
        self._connectors: Dict[str, BaseJobConnector] = {}

        # 1. Documented Public APIs
        self.register(RemoteOKConnector())
        self.register(JobicyConnector())
        self.register(ArbeitnowConnector())

        # 2. Employer ATS Career Boards (Official Public APIs)
        self.register(GreenhouseConnector())
        self.register(LeverConnector())
        self.register(AshbyConnector())
        self.register(SmartRecruitersConnector())

        # 3. Assisted Link Import Connectors (Compliance with strict anti-scraping Terms)
        self.register(LinkedInConnector())
        self.register(InternshalaConnector())
        self.register(GlassdoorConnector())

    def register(self, connector: BaseJobConnector) -> None:
        """Register a new connector."""
        self._connectors[connector.name.lower()] = connector

    def get(self, name: str) -> Optional[BaseJobConnector]:
        """Retrieve connector by identifier."""
        return self._connectors.get(name.lower())

    def get_all(self) -> List[BaseJobConnector]:
        """List all registered connectors."""
        return list(self._connectors.values())

    def get_enabled(self, enabled_names: List[str]) -> List[BaseJobConnector]:
        """Filter registered connectors by enabled identifiers."""
        clean_names = {n.strip().lower() for n in enabled_names}
        return [c for name, c in self._connectors.items() if name in clean_names]

    def unregister(self, name: str) -> None:
        """Remove a connector by identifier."""
        self._connectors.pop(name.lower(), None)

    def get_capabilities_matrix(self, enabled_names: Optional[List[str]] = None) -> List[SourceCapability]:
        """Return the explicit capability matrix across all sources."""
        active_names = {n.strip().lower() for n in enabled_names} if enabled_names else None
        matrix = []
        for c in self._connectors.values():
            caps = getattr(c, "capabilities", None)
            if caps is None:
                continue
            if active_names is not None:
                caps.enabled = c.name.lower() in active_names
            matrix.append(caps)
        return matrix


# Singleton instance
_registry = JobSourceRegistry()


def get_job_registry() -> JobSourceRegistry:
    return _registry
