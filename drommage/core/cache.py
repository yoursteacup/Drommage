"""
SQLite-based analysis cache with versioning support.
Stores analysis results for git commits with version management.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from .analysis import AnalysisResult, AnalysisMode


class AnalysisCache:
    """SQLite-based cache for commit analysis results with versioning."""
    
    def __init__(self, cache_dir: Path):
        """
        Initialize cache with SQLite database.
        
        Args:
            cache_dir: Directory to store cache database
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    commit_hash TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    summary TEXT,
                    details TEXT,
                    risks TEXT,  -- JSON array
                    recommendations TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (commit_hash, mode, version)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS provider_usage (
                    provider TEXT PRIMARY KEY,
                    total_calls INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    avg_response_time REAL DEFAULT 0.0,
                    last_used TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_lookup 
                ON analyses(commit_hash, mode)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_date 
                ON analyses(created_at DESC)
            """)
            
            conn.commit()
    
    def get_analysis(self, commit_hash: str, mode: AnalysisMode) -> Optional[AnalysisResult]:
        """
        Get latest cached analysis for commit and mode.
        
        Args:
            commit_hash: Git commit hash
            mode: Analysis mode (PAT/BRIEF/DEEP)
            
        Returns:
            AnalysisResult if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM analyses 
                WHERE commit_hash = ? AND mode = ?
                ORDER BY version DESC
                LIMIT 1
            """, (commit_hash, mode.value))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            # Deserialize JSON fields
            risks = json.loads(row['risks']) if row['risks'] else []
            recommendations = json.loads(row['recommendations']) if row['recommendations'] else []
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
            created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
            
            return AnalysisResult(
                mode=AnalysisMode(row['mode']),
                commit_hash=row['commit_hash'],
                provider=row['provider'],
                version=row['version'],
                summary=row['summary'],
                details=row['details'],
                risks=risks,
                recommendations=recommendations,
                metadata=metadata,
                created_at=created_at
            )
    
    def store_analysis(self, result: AnalysisResult):
        """
        Store analysis result with automatic version increment.
        
        Args:
            result: AnalysisResult to store
        """
        with sqlite3.connect(self.db_path) as conn:
            # Get next version number
            cursor = conn.execute("""
                SELECT COALESCE(MAX(version), 0) + 1 as next_version
                FROM analyses
                WHERE commit_hash = ? AND mode = ?
            """, (result.commit_hash, result.mode.value))
            
            next_version = cursor.fetchone()[0]
            
            # Store new analysis
            conn.execute("""
                INSERT INTO analyses (
                    commit_hash, mode, provider, version,
                    summary, details, risks, recommendations, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.commit_hash,
                result.mode.value,
                result.provider,
                next_version,
                result.summary,
                result.details,
                json.dumps(result.risks) if result.risks else None,
                json.dumps(result.recommendations) if result.recommendations else None,
                json.dumps(result.metadata) if result.metadata else None,
                result.created_at.isoformat()
            ))
            
            conn.commit()
    
    def clear_cache(self, mode: Optional[AnalysisMode] = None, commit_hash: Optional[str] = None) -> int:
        """
        Clear cached analyses.
        
        Args:
            mode: Specific mode to clear (None = all modes)
            commit_hash: Specific commit to clear (None = all commits)
            
        Returns:
            Number of entries cleared
        """
        with sqlite3.connect(self.db_path) as conn:
            if mode and commit_hash:
                # Clear specific commit and mode
                cursor = conn.execute("""
                    DELETE FROM analyses 
                    WHERE commit_hash = ? AND mode = ?
                """, (commit_hash, mode.value))
            elif mode:
                # Clear all commits for specific mode
                cursor = conn.execute("""
                    DELETE FROM analyses WHERE mode = ?
                """, (mode.value,))
            elif commit_hash:
                # Clear all modes for specific commit
                cursor = conn.execute("""
                    DELETE FROM analyses WHERE commit_hash = ?
                """, (commit_hash,))
            else:
                # Clear everything
                cursor = conn.execute("DELETE FROM analyses")
            
            deleted = cursor.rowcount
            conn.commit()
            return deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Overall stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(DISTINCT commit_hash) as unique_commits,
                    COUNT(DISTINCT provider) as unique_providers
                FROM analyses
            """)
            overall = dict(cursor.fetchone())
            
            # Mode breakdown
            cursor = conn.execute("""
                SELECT mode, COUNT(*) as count
                FROM analyses
                GROUP BY mode
            """)
            by_mode = {row['mode']: row['count'] for row in cursor.fetchall()}
            
            # Provider usage
            cursor = conn.execute("""
                SELECT provider, COUNT(*) as count, MAX(created_at) as last_used
                FROM analyses
                GROUP BY provider
                ORDER BY count DESC
            """)
            by_provider = [dict(row) for row in cursor.fetchall()]
            
            # Recent activity
            cursor = conn.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM analyses
                WHERE created_at >= date('now', '-7 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            recent_activity = [dict(row) for row in cursor.fetchall()]
            
            return {
                'overall': overall,
                'by_mode': by_mode,
                'by_provider': by_provider,
                'recent_activity': recent_activity
            }
    
    def cleanup_old_versions(self, keep_versions: int = 3) -> int:
        """
        Clean up old versions, keeping only the most recent ones.
        
        Args:
            keep_versions: Number of versions to keep per commit/mode
            
        Returns:
            Number of entries deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            # Delete all but the latest N versions for each commit/mode combo
            cursor = conn.execute("""
                DELETE FROM analyses
                WHERE rowid IN (
                    SELECT rowid FROM (
                        SELECT rowid,
                               ROW_NUMBER() OVER (
                                   PARTITION BY commit_hash, mode 
                                   ORDER BY version DESC
                               ) as row_num
                        FROM analyses
                    ) ranked
                    WHERE row_num > ?
                )
            """, (keep_versions,))
            
            deleted = cursor.rowcount
            conn.commit()
            return deleted
    
    def vacuum(self):
        """Optimize database by running VACUUM."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")
    
    def has_analysis(self, commit_hash: str, mode: AnalysisMode) -> bool:
        """Check if analysis exists for commit and mode."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 1 FROM analyses 
                WHERE commit_hash = ? AND mode = ?
                LIMIT 1
            """, (commit_hash, mode.value))
            return cursor.fetchone() is not None
    
    def get_analysis_versions(self, commit_hash: str, mode: AnalysisMode) -> List[Dict[str, Any]]:
        """Get all versions of analysis for a commit and mode."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT version, provider, created_at, summary
                FROM analyses
                WHERE commit_hash = ? AND mode = ?
                ORDER BY version DESC
            """, (commit_hash, mode.value))
            
            return [dict(row) for row in cursor.fetchall()]