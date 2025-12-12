"""
Worker Registry for Universal Orchestrator.
Maps agent/persona names to their Gatherer and Verifier implementations.
"""
from typing import Dict, Type, Tuple
from agent_core.core.interfaces import Gatherer, Verifier
from deep_research_agent.workers import ResearchWorker, Critic

class WorkerRegistry:
    """Registry for Worker Persona Packs"""
    
    _registry: Dict[str, Tuple[Type[Gatherer], Type[Verifier]]] = {}

    @classmethod
    def register(cls, name: str, gatherer_cls: Type[Gatherer], verifier_cls: Type[Verifier]):
        """Register a new worker persona"""
        cls._registry[name] = (gatherer_cls, verifier_cls)

    @classmethod
    def get_worker_pair(cls, name: str) -> Tuple[Type[Gatherer], Type[Verifier]]:
        """Get the Gatherer and Verifier classes for a given persona"""
        # Default to ResearchWorker/Critic if not found or if name is empty
        if not name or name not in cls._registry:
            return (ResearchWorker, Critic)
        return cls._registry[name]

# Register default persona
WorkerRegistry.register("researcher", ResearchWorker, Critic)
