#!/usr/bin/env python3
"""
Execution Protocol for DRommage
Протокол исполнения задач и управления контекстом разработки
Адаптация системы решений из TrendDemic для DRommage
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from drommage.core.git_integration import GitIntegration
from .task_tracker import TaskTracker, TaskStatus, TaskType


class DecisionType(Enum):
    PROBLEM = "problem"
    ANALYSIS = "analysis"
    SOLUTION = "solution"
    RESULT = "result"
    INVESTIGATION = "investigation"


class ExecutionPhase(Enum):
    PLANNING = "planning"
    INVESTIGATION = "investigation"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOYMENT = "deployment"


@dataclass
class Decision:
    id: str
    decision_type: DecisionType
    title: str
    description: str
    context: Dict[str, Any]
    timestamp: datetime
    task_id: Optional[str] = None
    commit_hash: Optional[str] = None
    branch: Optional[str] = None
    phase: Optional[ExecutionPhase] = None
    tags: List[str] = None
    related_decisions: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.related_decisions is None:
            self.related_decisions = []


@dataclass
class ExecutionSession:
    id: str
    task_id: str
    started_at: datetime
    current_phase: ExecutionPhase
    decisions: List[str]
    context: Dict[str, Any]
    status: str = "active"
    ended_at: Optional[datetime] = None


class ExecutionProtocol:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.metadata_dir = project_root / ".drommage"
        self.metadata_dir.mkdir(exist_ok=True)
        
        self.decisions_file = self.metadata_dir / "decisions.json"
        self.sessions_file = self.metadata_dir / "sessions.json"
        self.context_file = self.metadata_dir / "context.json"
        
        self.git = GitIntegration()
        self.task_tracker = TaskTracker(project_root)
        
        # Инициализация файлов
        for file_path in [self.decisions_file, self.sessions_file, self.context_file]:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
    
    def _load_json(self, file_path: Path) -> Dict:
        """Загрузить JSON данные"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_json(self, file_path: Path, data: Dict):
        """Сохранить JSON данные"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def _get_current_context(self) -> Dict[str, Any]:
        """Получить текущий контекст"""
        context = {
            'timestamp': datetime.now(),
            'git': {},
            'tasks': {}
        }
        
        # Git контекст
        if self.git.is_git_repo():
            repo_info = self.git.get_repo_info()
            context['git'] = repo_info
            
            # Получаем последние коммиты
            recent_commits = self.git.get_recent_commits(limit=5)
            context['git']['recent_commits'] = [
                {'hash': c.hash[:8], 'message': c.message, 'date': c.date}
                for c in recent_commits
            ]
        
        # Контекст задач
        active_tasks = self.task_tracker.get_active_tasks()
        context['tasks'] = {
            'active_count': len(active_tasks),
            'active_tasks': [
                {'id': t['id'], 'title': t['title'], 'status': t['status']}
                for t in active_tasks[:3]  # Последние 3
            ]
        }
        
        return context
    
    def record_decision(
        self, 
        decision_type: DecisionType,
        title: str,
        description: str,
        task_id: Optional[str] = None,
        phase: Optional[ExecutionPhase] = None,
        tags: List[str] = None
    ) -> str:
        """Зафиксировать решение в протоколе"""
        decision_id = str(uuid.uuid4())[:8]
        
        # Получаем текущий git контекст
        current_commit = None
        current_branch = None
        if self.git.is_git_repo():
            repo_info = self.git.get_repo_info()
            current_commit = repo_info.get('current_commit')
            current_branch = repo_info.get('branch')
        
        decision = Decision(
            id=decision_id,
            decision_type=decision_type,
            title=title,
            description=description,
            context=self._get_current_context(),
            timestamp=datetime.now(),
            task_id=task_id,
            commit_hash=current_commit,
            branch=current_branch,
            phase=phase,
            tags=tags or []
        )
        
        decisions = self._load_json(self.decisions_file)
        decisions[decision_id] = asdict(decision)
        self._save_json(self.decisions_file, decisions)
        
        return decision_id
    
    def start_task_execution(self, task_id: str) -> str:
        """Начать выполнение задачи"""
        session_id = str(uuid.uuid4())[:8]
        
        session = ExecutionSession(
            id=session_id,
            task_id=task_id,
            started_at=datetime.now(),
            current_phase=ExecutionPhase.PLANNING,
            decisions=[],
            context=self._get_current_context()
        )
        
        sessions = self._load_json(self.sessions_file)
        sessions[session_id] = asdict(session)
        self._save_json(self.sessions_file, sessions)
        
        # Обновляем статус задачи
        self.task_tracker.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
        # Записываем решение о начале
        self.record_decision(
            DecisionType.ANALYSIS,
            f"Начато выполнение задачи {task_id}",
            f"Инициирована сессия выполнения {session_id}",
            task_id=task_id,
            phase=ExecutionPhase.PLANNING
        )
        
        return session_id
    
    def advance_phase(self, session_id: str, new_phase: ExecutionPhase, description: str = "") -> bool:
        """Перейти к следующей фазе выполнения"""
        sessions = self._load_json(self.sessions_file)
        if session_id not in sessions:
            return False
        
        old_phase = sessions[session_id]['current_phase']
        sessions[session_id]['current_phase'] = new_phase.value
        
        # Записываем решение о переходе
        decision_id = self.record_decision(
            DecisionType.ANALYSIS,
            f"Переход к фазе {new_phase.value}",
            description or f"Переход из {old_phase} в {new_phase.value}",
            task_id=sessions[session_id]['task_id'],
            phase=new_phase
        )
        
        sessions[session_id]['decisions'].append(decision_id)
        self._save_json(self.sessions_file, sessions)
        
        return True
    
    def complete_task_execution(self, session_id: str, result_description: str) -> bool:
        """Завершить выполнение задачи"""
        sessions = self._load_json(self.sessions_file)
        if session_id not in sessions:
            return False
        
        session = sessions[session_id]
        task_id = session['task_id']
        
        # Записываем результат
        decision_id = self.record_decision(
            DecisionType.RESULT,
            f"Задача {task_id} выполнена",
            result_description,
            task_id=task_id,
            phase=ExecutionPhase.DEPLOYMENT
        )
        
        # Завершаем сессию
        sessions[session_id]['status'] = "completed"
        sessions[session_id]['ended_at'] = datetime.now()
        sessions[session_id]['decisions'].append(decision_id)
        self._save_json(self.sessions_file, sessions)
        
        # Обновляем статус задачи
        self.task_tracker.update_task_status(task_id, TaskStatus.COMPLETED)
        
        return True
    
    def report_problem(self, title: str, description: str, task_id: Optional[str] = None) -> str:
        """Зафиксировать проблему"""
        # Если проблема связана с задачей, создаем новую задачу для её решения
        if task_id is None:
            problem_task_id = self.task_tracker.create_task(
                title=f"🐛 {title}",
                description=description,
                task_type=TaskType.BUG_FIX
            )
        else:
            problem_task_id = task_id
        
        decision_id = self.record_decision(
            DecisionType.PROBLEM,
            title,
            description,
            task_id=problem_task_id,
            tags=["problem", "needs_investigation"]
        )
        
        return decision_id
    
    def propose_solution(self, problem_decision_id: str, solution_description: str) -> str:
        """Предложить решение проблемы"""
        decisions = self._load_json(self.decisions_file)
        if problem_decision_id not in decisions:
            return None
        
        problem = decisions[problem_decision_id]
        
        solution_id = self.record_decision(
            DecisionType.SOLUTION,
            f"Решение: {problem['title']}",
            solution_description,
            task_id=problem.get('task_id'),
            tags=["solution", "ready_for_implementation"]
        )
        
        # Связываем решение с проблемой
        decisions = self._load_json(self.decisions_file)
        decisions[solution_id]['related_decisions'] = [problem_decision_id]
        self._save_json(self.decisions_file, decisions)
        
        return solution_id
    
    def get_project_status(self) -> Dict[str, Any]:
        """Получить полный статус проекта"""
        context = self._get_current_context()
        
        # Статистика задач
        task_stats = self.task_tracker.get_statistics()
        
        # Активные сессии
        sessions = self._load_json(self.sessions_file)
        active_sessions = [s for s in sessions.values() if s['status'] == 'active']
        
        # Последние решения
        decisions = self._load_json(self.decisions_file)
        recent_decisions = sorted(
            decisions.values(), 
            key=lambda x: x['timestamp'], 
            reverse=True
        )[:5]
        
        return {
            'context': context,
            'tasks': task_stats,
            'active_sessions': len(active_sessions),
            'recent_decisions': recent_decisions,
            'current_phase': active_sessions[0]['current_phase'] if active_sessions else None
        }
    
    def get_decision_chain(self, decision_id: str) -> List[Dict]:
        """Получить цепочку связанных решений"""
        decisions = self._load_json(self.decisions_file)
        if decision_id not in decisions:
            return []
        
        chain = [decisions[decision_id]]
        current = decisions[decision_id]
        
        # Собираем связанные решения
        related = current.get('related_decisions', [])
        for rel_id in related:
            if rel_id in decisions:
                chain.append(decisions[rel_id])
        
        return sorted(chain, key=lambda x: x['timestamp'])
    
    def analyze_workflow_patterns(self) -> Dict[str, Any]:
        """Анализ паттернов рабочего процесса"""
        decisions = self._load_json(self.decisions_file)
        sessions = self._load_json(self.sessions_file)
        
        analysis = {
            'decision_patterns': {},
            'phase_transitions': {},
            'problem_resolution_time': [],
            'most_productive_phases': {}
        }
        
        # Анализ типов решений
        for decision in decisions.values():
            dec_type = decision['decision_type']
            analysis['decision_patterns'][dec_type] = analysis['decision_patterns'].get(dec_type, 0) + 1
        
        # Анализ переходов между фазами
        for session in sessions.values():
            if session['status'] == 'completed':
                phase_count = len([d for d in session.get('decisions', [])])
                phase = session.get('current_phase', 'unknown')
                if phase not in analysis['most_productive_phases']:
                    analysis['most_productive_phases'][phase] = []
                analysis['most_productive_phases'][phase].append(phase_count)
        
        return analysis