"""
Region index - tracks semantic regions and their evolution through versions
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from .diff_tracker import GitDiffEngine, Region

@dataclass  
class RegionSummary:
    """Summary of a region's history"""
    id: str
    canonical_text: str
    versions_modified: int
    total_additions: int
    total_deletions: int
    stability_score: float  # 0-1, how stable the region has been

class RegionIndex:
    def __init__(self, engine: GitDiffEngine):
        self.engine = engine
        self.region_summaries: Dict[str, RegionSummary] = {}
        self.version_region_map: Dict[str, List[str]] = {}  # version -> list of region IDs
        
    def build_regions(self):
        """Build region index from engine data"""
        for region_id, region in self.engine.regions.items():
            # Calculate statistics
            versions_modified = len(set(h["version"] for h in region.history))
            total_additions = sum(
                len(h.get("new_lines", [])) 
                for h in region.history 
                if h["action"] in ["created", "modify"]
            )
            total_deletions = sum(
                len(h.get("old_lines", [])) 
                for h in region.history 
                if h["action"] in ["remove", "modify"]
            )
            
            # Stability score: fewer changes = more stable
            total_versions = len(self.engine.versions)
            stability = 1.0 - (versions_modified / total_versions)
            
            self.region_summaries[region_id] = RegionSummary(
                id=region_id,
                canonical_text=region.canonical_text[:100] + "..." if len(region.canonical_text) > 100 else region.canonical_text,
                versions_modified=versions_modified,
                total_additions=total_additions,
                total_deletions=total_deletions,
                stability_score=stability
            )
            
            # Build version -> regions map
            for hist in region.history:
                version = hist["version"]
                if version not in self.version_region_map:
                    self.version_region_map[version] = []
                if region_id not in self.version_region_map[version]:
                    self.version_region_map[version].append(region_id)
    
    def get_regions_for_version(self, version: str) -> List[RegionSummary]:
        """Get all regions present in a specific version"""
        region_ids = self.version_region_map.get(version, [])
        return [self.region_summaries[rid] for rid in region_ids if rid in self.region_summaries]
    
    def get_most_volatile_regions(self, limit: int = 5) -> List[RegionSummary]:
        """Get regions that changed most frequently"""
        sorted_regions = sorted(
            self.region_summaries.values(),
            key=lambda r: r.versions_modified,
            reverse=True
        )
        return sorted_regions[:limit]
    
    def get_most_stable_regions(self, limit: int = 5) -> List[RegionSummary]:
        """Get regions that remained most stable"""
        sorted_regions = sorted(
            self.region_summaries.values(),
            key=lambda r: r.stability_score,
            reverse=True
        )
        return sorted_regions[:limit]
    
    def get_region_history(self, region_id: str) -> List[Dict]:
        """Get full history of a specific region"""
        if region_id in self.engine.regions:
            return self.engine.regions[region_id].history
        return []