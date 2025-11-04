#!/usr/bin/env python3
"""
Task Tracker for DRommage
Отслеживание задач разработки с привязкой к git коммитам и анализам
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


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskType(Enum):
    BUG_FIX = "bug_fix"
    FEATURE = "feature" 
    REFACTOR = "refactor"
    DOCS = "docs"
    ANALYSIS = "analysis"
    INVESTIGATION = "investigation"


@dataclass
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    task_type: TaskType
    created_at: datetime
    updated_at: datetime
    commit_hash: Optional[str] = None
    branch: Optional[str] = None
    tags: List[str] = None
    analysis_ref: Optional[str] = None  # Ссылка на LLM анализ
    dependencies: List[str] = None
    estimated_time: Optional[int] = None  # в минутах
    actual_time: Optional[int] = None
    assignee: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []


class TaskTracker:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.metadata_dir = project_root / ".drommage"
        self.metadata_dir.mkdir(exist_ok=True)
        
        self.tasks_file = self.metadata_dir / "tasks.json"
        self.git = GitIntegration()
        
        # Инициализация файла задач
        if not self.tasks_file.exists():
            self._save_tasks({})
    
    def _load_tasks(self) -> Dict[str, Dict]:
        """Загрузить задачи из файла"""
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_tasks(self, tasks: Dict[str, Dict]):
        """Сохранить задачи в файл"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False, default=str)
    
    def create_task(
        self, 
        title: str, 
        description: str, 
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_type: TaskType = TaskType.FEATURE,
        tags: List[str] = None,
        estimated_time: Optional[int] = None
    ) -> str:
        """Создать новую задачу"""
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        
        # Получаем текущий git контекст
        current_commit = None
        current_branch = None
        if self.git.is_git_repo():
            repo_info = self.git.get_repo_info()
            current_commit = repo_info.get('current_commit')
            current_branch = repo_info.get('branch')
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            task_type=task_type,
            created_at=now,
            updated_at=now,
            commit_hash=current_commit,
            branch=current_branch,
            tags=tags or [],
            estimated_time=estimated_time
        )
        
        tasks = self._load_tasks()
        task_dict = asdict(task)
        # Преобразуем енумы в их значения для JSON сериализации
        task_dict['status'] = task.status.value
        task_dict['priority'] = task.priority.value  
        task_dict['task_type'] = task.task_type.value
        tasks[task_id] = task_dict
        self._save_tasks(tasks)
        
        return task_id
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Обновить статус задачи"""
        tasks = self._load_tasks()
        if task_id not in tasks:
            return False
        
        tasks[task_id]['status'] = status.value
        tasks[task_id]['updated_at'] = datetime.now().isoformat()
        
        # Если задача завершена, записываем текущий коммит
        if status == TaskStatus.COMPLETED and self.git.is_git_repo():
            repo_info = self.git.get_repo_info()
            tasks[task_id]['completion_commit'] = repo_info.get('current_commit')
        
        self._save_tasks(tasks)
        return True
    
    def link_analysis(self, task_id: str, analysis_data: Dict) -> bool:
        """Привязать LLM анализ к задаче"""
        tasks = self._load_tasks()
        if task_id not in tasks:
            return False
        
        # Сохраняем ссылку на анализ
        analysis_id = str(uuid.uuid4())[:8]
        analysis_file = self.metadata_dir / f"analysis_{analysis_id}.json"
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
        
        tasks[task_id]['analysis_ref'] = analysis_id
        tasks[task_id]['updated_at'] = datetime.now()
        self._save_tasks(tasks)
        
        return True
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Получить задачу по ID"""
        tasks = self._load_tasks()
        return tasks.get(task_id)
    
    def list_tasks(
        self, 
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        task_type: Optional[TaskType] = None,
        branch: Optional[str] = None
    ) -> List[Dict]:
        """Получить список задач с фильтрацией"""
        tasks = self._load_tasks()
        result = []
        
        for task_data in tasks.values():
            # Применяем фильтры
            if status and task_data.get('status') != status.value:
                continue
            if priority and task_data.get('priority') != priority.value:
                continue
            if task_type and task_data.get('task_type') != task_type.value:
                continue
            if branch and task_data.get('branch') != branch:
                continue
            
            result.append(task_data)
        
        # Сортируем по приоритету и дате создания
        result.sort(key=lambda x: (
            -(x.get('priority', TaskPriority.MEDIUM.value) if isinstance(x.get('priority'), int) else TaskPriority.MEDIUM.value),
            x.get('created_at', '')
        ))
        
        return result
    
    def get_active_tasks(self) -> List[Dict]:
        """Получить активные задачи (pending + in_progress)"""
        return self.list_tasks() 
    
    def get_commit_tasks(self, commit_hash: str) -> List[Dict]:
        """Получить задачи связанные с коммитом"""
        tasks = self._load_tasks()
        result = []
        
        for task_data in tasks.values():
            if (task_data.get('commit_hash') == commit_hash or 
                task_data.get('completion_commit') == commit_hash):
                result.append(task_data)
        
        return result
    
    def add_dependency(self, task_id: str, dependency_id: str) -> bool:
        """Добавить зависимость между задачами"""
        tasks = self._load_tasks()
        if task_id not in tasks or dependency_id not in tasks:
            return False
        
        if 'dependencies' not in tasks[task_id]:
            tasks[task_id]['dependencies'] = []
        
        if dependency_id not in tasks[task_id]['dependencies']:
            tasks[task_id]['dependencies'].append(dependency_id)
            tasks[task_id]['updated_at'] = datetime.now()
            self._save_tasks(tasks)
        
        return True
    
    def can_start_task(self, task_id: str) -> bool:
        """Проверить можно ли начать выполнение задачи (все зависимости выполнены)"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        dependencies = task.get('dependencies', [])
        if not dependencies:
            return True
        
        tasks = self._load_tasks()
        for dep_id in dependencies:
            dep_task = tasks.get(dep_id)
            if not dep_task or dep_task.get('status') != TaskStatus.COMPLETED.value:
                return False
        
        return True
    
    def get_statistics(self) -> Dict:
        """Получить статистику по задачам"""
        tasks = self._load_tasks()
        
        stats = {
            'total': len(tasks),
            'by_status': {},
            'by_priority': {},
            'by_type': {},
            'completion_rate': 0.0
        }
        
        for task_data in tasks.values():
            status = task_data.get('status', TaskStatus.PENDING.value)
            priority = task_data.get('priority', TaskPriority.MEDIUM.value)
            task_type = task_data.get('task_type', TaskType.FEATURE.value)
            
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
            stats['by_type'][task_type] = stats['by_type'].get(task_type, 0) + 1
        
        completed = stats['by_status'].get(TaskStatus.COMPLETED.value, 0)
        if stats['total'] > 0:
            stats['completion_rate'] = completed / stats['total'] * 100
        
        return stats