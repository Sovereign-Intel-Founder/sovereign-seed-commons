from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any

class BaseStreamAdapter(ABC):
    """Abstract base class for all pluggable data stream adapters in Sovereign Seed Commons."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize connection, validate configuration and loopback security."""
        pass

    @abstractmethod
    async def stream_data(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator yielding normalized JSON/dictionary data packets from the external stream."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully teardown connection and clean up resources."""
        pass
