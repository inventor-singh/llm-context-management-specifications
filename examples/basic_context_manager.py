# Basic Context Manager Example

This example demonstrates a basic implementation of the LLM Context Window Management Specification (LCWMS).

```python
import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib
import numpy as np
from abc import ABC, abstractmethod

@dataclass
class ContextSegment:
    """Represents a segment of context information."""
    id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    relevance_score: float = 0.0
    access_count: int = 0
    compression_ratio: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextSegment':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class ContextMetrics:
    """Context management performance metrics."""
    total_segments: int
    active_segments: int
    total_size_bytes: int
    compression_ratio: float
    cache_hit_rate: float
    average_retrieval_time_ms: float
    memory_usage_bytes: int

class MemoryTier:
    """Enumeration of memory tiers."""
    ACTIVE = "active"
    WORKING = "working"
    LONG_TERM = "long_term"

class CompressionStrategy:
    """Enumeration of compression strategies."""
    NONE = "none"
    GZIP = "gzip"
    SEMANTIC = "semantic"
    ADAPTIVE = "adaptive"

class RetrievalStrategy:
    """Enumeration of retrieval strategies."""
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"

@dataclass
class ContextConfig:
    """Configuration for context management."""
    max_context_size: int = 32000
    working_memory_size: int = 128000
    compression_strategy: str = CompressionStrategy.ADAPTIVE
    compression_target_ratio: float = 0.3
    compression_quality_threshold: float = 0.8
    retrieval_strategy: str = RetrievalStrategy.HYBRID
    similarity_threshold: float = 0.7
    max_retrieval_results: int = 20
    cleanup_interval_minutes: int = 60
    metrics_enabled: bool = True

class CompressionEngine(ABC):
    """Abstract base class for compression engines."""
    
    @abstractmethod
    async def compress(self, content: str, target_ratio: float) -> str:
        pass
    
    @abstractmethod
    async def decompress(self, compressed_content: str) -> str:
        pass
    
    @abstractmethod
    def get_compression_ratio(self, original: str, compressed: str) -> float:
        pass

class BasicCompressionEngine(CompressionEngine):
    """Basic compression engine implementation."""
    
    async def compress(self, content: str, target_ratio: float) -> str:
        # Simple compression: truncate to target ratio
        target_length = int(len(content) * target_ratio)
        if target_length >= len(content):
            return content
        
        # Intelligent truncation: keep beginning and end
        keep_start = int(target_length * 0.7)
        keep_end = target_length - keep_start
        
        if keep_end > 0:
            compressed = content[:keep_start] + "...[truncated]..." + content[-keep_end:]
        else:
            compressed = content[:keep_start] + "...[truncated]"
        
        return compressed
    
    async def decompress(self, compressed_content: str) -> str:
        # For this basic implementation, decompression just returns the compressed content
        return compressed_content
    
    def get_compression_ratio(self, original: str, compressed: str) -> float:
        return len(compressed) / len(original) if len(original) > 0 else 1.0

class RetrievalEngine(ABC):
    """Abstract base class for retrieval engines."""
    
    @abstractmethod
    async def retrieve(self, query: str, segments: List[ContextSegment], limit: int) -> List[ContextSegment]:
        pass

class BasicRetrievalEngine(RetrievalEngine):
    """Basic retrieval engine implementation."""
    
    async def retrieve(self, query: str, segments: List[ContextSegment], limit: int) -> List[ContextSegment]:
        # Simple keyword-based retrieval
        query_words = set(query.lower().split())
        scored_segments = []
        
        for segment in segments:
            content_words = set(segment.content.lower().split())
            # Calculate simple overlap score
            overlap = len(query_words.intersection(content_words))
            if overlap > 0:
                score = overlap / len(query_words)
                segment.relevance_score = score
                scored_segments.append(segment)
        
        # Sort by relevance score and return top results
        scored_segments.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_segments[:limit]

class MemoryManager:
    """Manages different memory tiers."""
    
    def __init__(self, config: ContextConfig):
        self.config = config
        self.active_memory: Dict[str, ContextSegment] = {}
        self.working_memory: Dict[str, ContextSegment] = {}
        self.long_term_memory: Dict[str, ContextSegment] = {}
    
    async def store(self, tier: str, segment: ContextSegment) -> str:
        """Store a segment in the specified memory tier."""
        if tier == MemoryTier.ACTIVE:
            self.active_memory[segment.id] = segment
        elif tier == MemoryTier.WORKING:
            self.working_memory[segment.id] = segment
        elif tier == MemoryTier.LONG_TERM:
            self.long_term_memory[segment.id] = segment
        else:
            raise ValueError(f"Unknown memory tier: {tier}")
        
        return segment.id
    
    async def retrieve(self, tier: str, segment_id: str) -> Optional[ContextSegment]:
        """Retrieve a segment from the specified memory tier."""
        if tier == MemoryTier.ACTIVE:
            segment = self.active_memory.get(segment_id)
        elif tier == MemoryTier.WORKING:
            segment = self.working_memory.get(segment_id)
        elif tier == MemoryTier.LONG_TERM:
            segment = self.long_term_memory.get(segment_id)
        else:
            return None
        
        if segment:
            segment.access_count += 1
        
        return segment
    
    async def delete(self, tier: str, segment_id: str) -> bool:
        """Delete a segment from the specified memory tier."""
        if tier == MemoryTier.ACTIVE:
            return self.active_memory.pop(segment_id, None) is not None
        elif tier == MemoryTier.WORKING:
            return self.working_memory.pop(segment_id, None) is not None
        elif tier == MemoryTier.LONG_TERM:
            return self.long_term_memory.pop(segment_id, None) is not None
        return False
    
    async def get_all_segments(self, tier: str) -> List[ContextSegment]:
        """Get all segments from a memory tier."""
        if tier == MemoryTier.ACTIVE:
            return list(self.active_memory.values())
        elif tier == MemoryTier.WORKING:
            return list(self.working_memory.values())
        elif tier == MemoryTier.LONG_TERM:
            return list(self.long_term_memory.values())
        return []
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        return {
            "active": len(self.active_memory),
            "working": len(self.working_memory),
            "long_term": len(self.long_term_memory),
            "total": len(self.active_memory) + len(self.working_memory) + len(self.long_term_memory)
        }

class ContextManager:
    """Main context management system."""
    
    def __init__(self, config: ContextConfig):
        self.config = config
        self.memory_manager = MemoryManager(config)
        self.compression_engine = BasicCompressionEngine()
        self.retrieval_engine = BasicRetrievalEngine()
        self.metrics = ContextMetrics(
            total_segments=0,
            active_segments=0,
            total_size_bytes=0,
            compression_ratio=1.0,
            cache_hit_rate=0.0,
            average_retrieval_time_ms=0.0,
            memory_usage_bytes=0
        )
        self._last_cleanup = datetime.now()
    
    def _generate_segment_id(self, content: str) -> str:
        """Generate a unique ID for a context segment."""
        return hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()
    
    async def add_context(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add new content to the context."""
        if metadata is None:
            metadata = {}
        
        segment_id = self._generate_segment_id(content)
        segment = ContextSegment(
            id=segment_id,
            content=content,
            metadata=metadata,
            timestamp=datetime.now(),
            relevance_score=1.0  # New content starts with high relevance
        )
        
        # Store in active memory initially
        await self.memory_manager.store(MemoryTier.ACTIVE, segment)
        
        # Check if we need to optimize memory usage
        await self._maybe_optimize_memory()
        
        # Update metrics
        self.metrics.total_segments += 1
        self.metrics.active_segments = len(await self.memory_manager.get_all_segments(MemoryTier.ACTIVE))
        
        return segment_id
    
    async def retrieve_relevant(self, query: str, limit: int = 10) -> List[ContextSegment]:
        """Retrieve relevant context segments for a query."""
        start_time = datetime.now()
        
        # Search across all memory tiers
        all_segments = []
        for tier in [MemoryTier.ACTIVE, MemoryTier.WORKING, MemoryTier.LONG_TERM]:
            segments = await self.memory_manager.get_all_segments(tier)
            all_segments.extend(segments)
        
        # Use retrieval engine to find relevant segments
        relevant_segments = await self.retrieval_engine.retrieve(query, all_segments, limit)
        
        # Update retrieval metrics
        retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics.average_retrieval_time_ms = (
            self.metrics.average_retrieval_time_ms * 0.9 + retrieval_time * 0.1
        )
        
        return relevant_segments
    
    async def remove_context(self, segment_id: str) -> bool:
        """Remove a context segment."""
        for tier in [MemoryTier.ACTIVE, MemoryTier.WORKING, MemoryTier.LONG_TERM]:
            if await self.memory_manager.delete(tier, segment_id):
                self.metrics.total_segments -= 1
                self.metrics.active_segments = len(await self.memory_manager.get_all_segments(MemoryTier.ACTIVE))
                return True
        return False
    
    async def compress_context(self, segment_id: str) -> bool:
        """Compress a specific context segment."""
        # Find the segment
        segment = None
        tier = None
        for tier_name in [MemoryTier.ACTIVE, MemoryTier.WORKING, MemoryTier.LONG_TERM]:
            segment = await self.memory_manager.retrieve(tier_name, segment_id)
            if segment:
                tier = tier_name
                break
        
        if not segment:
            return False
        
        # Compress the content
        compressed_content = await self.compression_engine.compress(
            segment.content, 
            self.config.compression_target_ratio
        )
        
        # Update segment with compressed content
        segment.content = compressed_content
        segment.compression_ratio = self.compression_engine.get_compression_ratio(
            segment.content, compressed_content
        )
        
        # Store back in the same tier
        await self.memory_manager.store(tier, segment)
        
        return True
    
    async def _maybe_optimize_memory(self):
        """Optimize memory usage if needed."""
        active_segments = await self.memory_manager.get_all_segments(MemoryTier.ACTIVE)
        
        # Calculate current context size (simplified - just count characters)
        current_size = sum(len(segment.content) for segment in active_segments)
        
        if current_size > self.config.max_context_size:
            await self._optimize_active_memory()
    
    async def _optimize_active_memory(self):
        """Optimize active memory by moving/compressing/removing segments."""
        active_segments = await self.memory_manager.get_all_segments(MemoryTier.ACTIVE)
        
        # Sort by relevance score and last access time
        def score_segment(segment: ContextSegment) -> float:
            time_decay = (datetime.now() - segment.timestamp).total_seconds() / 3600  # hours
            return segment.relevance_score * (1.0 / (1.0 + time_decay)) * segment.access_count
        
        active_segments.sort(key=score_segment, reverse=True)
        
        # Keep top segments in active memory, move others to working memory
        keep_active = active_segments[:int(len(active_segments) * 0.6)]
        move_to_working = active_segments[int(len(active_segments) * 0.6):]
        
        for segment in move_to_working:
            await self.memory_manager.delete(MemoryTier.ACTIVE, segment.id)
            await self.memory_manager.store(MemoryTier.WORKING, segment)
    
    async def optimize(self) -> Dict[str, Any]:
        """Run optimization across all memory tiers."""
        await self._optimize_active_memory()
        
        # Cleanup old segments
        if datetime.now() - self._last_cleanup > timedelta(minutes=self.config.cleanup_interval_minutes):
            await self._cleanup_old_segments()
            self._last_cleanup = datetime.now()
        
        return {
            "optimization_completed": True,
            "memory_usage": self.memory_manager.get_memory_usage(),
            "metrics": asdict(self.metrics)
        }
    
    async def _cleanup_old_segments(self):
        """Remove very old segments from long-term memory."""
        cutoff_time = datetime.now() - timedelta(days=30)  # Keep 30 days
        
        long_term_segments = await self.memory_manager.get_all_segments(MemoryTier.LONG_TERM)
        for segment in long_term_segments:
            if segment.timestamp < cutoff_time and segment.access_count < 2:
                await self.memory_manager.delete(MemoryTier.LONG_TERM, segment.id)
    
    async def get_metrics(self) -> ContextMetrics:
        """Get current performance metrics."""
        # Update metrics
        self.metrics.active_segments = len(await self.memory_manager.get_all_segments(MemoryTier.ACTIVE))
        return self.metrics
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        memory_usage = self.memory_manager.get_memory_usage()
        metrics = await self.get_metrics()
        
        return {
            "memory_usage": memory_usage,
            "metrics": asdict(metrics),
            "config": asdict(self.config),
            "last_cleanup": self._last_cleanup.isoformat()
        }

# Example usage
async def main():
    """Example usage of the Context Manager."""
    
    # Create configuration
    config = ContextConfig(
        max_context_size=1000,  # Small for demo
        working_memory_size=2000,
        compression_strategy=CompressionStrategy.ADAPTIVE,
        retrieval_strategy=RetrievalStrategy.KEYWORD
    )
    
    # Create context manager
    context_manager = ContextManager(config)
    
    # Add some context
    print("Adding context...")
    id1 = await context_manager.add_context(
        "This is important information about machine learning algorithms.",
        {"type": "technical", "importance": "high"}
    )
    
    id2 = await context_manager.add_context(
        "User preferences: likes technical content, prefers detailed explanations.",
        {"type": "user_profile", "importance": "medium"}
    )
    
    id3 = await context_manager.add_context(
        "Previous conversation covered neural networks and deep learning concepts.",
        {"type": "conversation_history", "importance": "medium"}
    )
    
    # Retrieve relevant context
    print("\nRetrieving relevant context...")
    relevant = await context_manager.retrieve_relevant("machine learning", limit=5)
    
    print(f"Found {len(relevant)} relevant segments:")
    for segment in relevant:
        print(f"- {segment.id[:8]}: {segment.content[:50]}... (score: {segment.relevance_score:.2f})")
    
    # Add more content to trigger optimization
    print("\nAdding more content to trigger optimization...")
    for i in range(10):
        await context_manager.add_context(
            f"Additional content item {i} with various details about different topics.",
            {"type": "filler", "importance": "low"}
        )
    
    # Run optimization
    print("\nRunning optimization...")
    optimization_result = await context_manager.optimize()
    print(f"Optimization result: {optimization_result}")
    
    # Get final status
    print("\nFinal system status:")
    status = await context_manager.get_status()
    print(json.dumps(status, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

1. **Memory Hierarchy**: Three-tier memory system (active, working, long-term)
2. **Context Segmentation**: Breaking content into manageable segments
3. **Relevance Scoring**: Basic relevance calculation for retrieval
4. **Compression**: Simple compression with configurable ratios
5. **Optimization**: Automatic memory optimization and cleanup
6. **Metrics**: Performance monitoring and reporting
7. **Configuration**: Flexible configuration system

## Usage Instructions

1. Install required dependencies:
   ```bash
   pip install numpy
   ```

2. Run the example:
   ```bash
   python basic_context_manager.py
   ```

3. Modify the configuration and test different scenarios

## Extension Points

- Replace `BasicCompressionEngine` with advanced compression algorithms
- Implement `BasicRetrievalEngine` with semantic search using embeddings
- Add persistent storage backends for long-term memory
- Implement more sophisticated optimization strategies
- Add support for different content types and formats

This example provides a foundation for building production-ready context management systems following the LCWMS specification.
