"""
Abstract Surface Adapter interface for computer-use operations.
Decouples agent perception/action from underlying platform (browser, desktop, accessibility, vision).
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from src.models.actions import Locator, Observation


class SurfaceAdapter(ABC):
    """
    Abstract interface for operating computer surfaces.
    Subclasses implement platform-specific interaction logic.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection or launching surface session."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close surface session and cleanup resources."""
        pass

    @abstractmethod
    async def observe(self) -> Observation:
        """Observe current surface state (URL, title, interactive elements, text, screenshot)."""
        pass

    @abstractmethod
    async def click(self, locator: Locator, timeout_ms: int = 5000) -> bool:
        """Click element matching locator."""
        pass

    @abstractmethod
    async def type(self, locator: Locator, text: str, timeout_ms: int = 5000) -> bool:
        """Type text into target element matching locator."""
        pass

    @abstractmethod
    async def navigate(self, url: str) -> bool:
        """Navigate surface to target URL."""
        pass

    @abstractmethod
    async def extract(self, locator: Locator) -> Optional[str]:
        """Extract text content from target element matching locator."""
        pass

    @abstractmethod
    async def screenshot(self) -> bytes:
        """Capture image screenshot of current surface."""
        pass

    @abstractmethod
    async def wait_for_selector(self, locator: Locator, timeout_ms: int = 5000) -> bool:
        """Wait for element matching locator to be present/visible."""
        pass
