#!/usr/bin/env python3
"""
DevFlow - Development Workflow Management Tool
Standalone execution protocol and task tracking system

ФИЛОСОФИЯ:
DevFlow - это отдельный инструмент для управления workflow разработки.
Он может работать с любым проектом (не только DRommage) и предоставляет
структурированный подход к принятию решений и отслеживанию задач.

ИСПОЛЬЗОВАНИЕ:
    python devflow.py status                    # Статус проекта и workflow
    python devflow.py task add "title" "desc"   # Создать задачу  
    python devflow.py task list                 # Список задач
    python devflow.py task start <id>           # Начать выполнение
    python devflow.py task complete <id>        # Завершить задачу
    python devflow.py protocol problem "title" "desc"    # Зафиксировать проблему
    python devflow.py protocol solution "desc"  # Предложить решение
    python devflow.py protocol result "desc"    # Записать результат
    python devflow.py analyze                   # Анализ workflow паттернов
    python devflow.py sync drommage            # Синхронизация с DRommage
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Добавляем путь к модулям для совместимости
sys.path.append(str(Path(__file__).parent))

from devflow_core import TaskTracker, TaskStatus, TaskPriority, TaskType
from devflow_core import ExecutionProtocol, DecisionType, ExecutionPhase
from drommage.core.git_integration import GitIntegration


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{text}{Colors.ENDC}")


def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.ENDC}")


class DevFlowManager:
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.task_tracker = TaskTracker(self.project_root)
        self.execution_protocol = ExecutionProtocol(self.project_root)
        self.git = GitIntegration()
        
        # DevFlow metadata
        self.devflow_dir = self.project_root / ".devflow"
        self.devflow_dir.mkdir(exist_ok=True)
        self.config_file = self.devflow_dir / "config.json"
        
        self._init_config()
    
    def _init_config(self):
        """Initialize DevFlow configuration"""
        default_config = {
            "project_name": self.project_root.name,
            "created_at": datetime.now().isoformat(),
            "workflow_type": "standard",  # standard, agile, experimental
            "integration": {
                "drommage": False,
                "git": True
            },
            "preferences": {
                "auto_link_commits": True,
                "decision_notifications": True,
                "daily_standup": False
            }
        }
        
        if not self.config_file.exists():
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
    
    def status(self):
        """Показать статус DevFlow и проекта"""
        print_header("📊 DevFlow Project Status")
        
        # Конфигурация проекта
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n🎯 Project: {config['project_name']}")
        print(f"📁 Location: {self.project_root}")
        print(f"⚡ Workflow: {config['workflow_type']}")
        print(f"📅 Created: {config['created_at'][:10]}")
        
        # Git информация
        if self.git.is_git_repo():
            repo_info = self.git.get_repo_info()
            print(f"\n📝 Git Integration:")
            print(f"   🌿 Branch: {repo_info.get('branch', 'unknown')}")
            print(f"   📝 Current commit: {repo_info.get('current_commit', 'unknown')[:8]}")
        else:
            print_warning("Not in a git repository - limited functionality")
        
        # Статистика задач
        stats = self.task_tracker.get_statistics()
        print(f"\n📋 Workflow Overview:")
        print(f"   Total tasks: {stats['total']}")
        print(f"   Completion rate: {stats['completion_rate']:.1f}%")
        
        print("\n📊 Task Status:")
        for status, count in stats['by_status'].items():
            status_icons = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅", 
                "blocked": "🚫",
                "cancelled": "❌"
            }
            # Обрабатываем как строку, так и енум
            status_str = status if isinstance(status, str) else str(status).split('.')[-1].lower()
            icon = status_icons.get(status_str, "❓")
            print(f"   {icon} {status_str}: {count}")
        
        print("\n🎯 Priority Distribution:")
        priority_names = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
        for priority, count in stats['by_priority'].items():
            # Обрабатываем как число, так и енум
            priority_val = priority if isinstance(priority, int) else getattr(priority, 'value', priority)
            name = priority_names.get(priority_val, f"Priority {priority}")
            print(f"   {name}: {count}")
        
        # Активные сессии выполнения
        sessions = self.execution_protocol._load_json(self.execution_protocol.sessions_file)
        active_sessions = [s for s in sessions.values() if s['status'] == 'active']
        
        print(f"\n⚡ Active Execution Sessions:")
        if active_sessions:
            for session in active_sessions:
                print(f"   🔄 {session['id'][:8]} - Task {session['task_id']} - {session['current_phase']}")
        else:
            print("   No active sessions")
        
        # Последние решения в протоколе
        decisions = self.execution_protocol._load_json(self.execution_protocol.decisions_file)
        recent_decisions = sorted(
            decisions.values(),
            key=lambda x: x['timestamp'],
            reverse=True
        )[:3]
        
        print(f"\n🧭 Recent Protocol Decisions:")
        if recent_decisions:
            for decision in recent_decisions:
                type_icons = {
                    "problem": "🐛",
                    "analysis": "🔍",
                    "solution": "💡", 
                    "result": "✅",
                    "investigation": "🕵️"
                }
                icon = type_icons.get(decision['decision_type'], "📝")
                timestamp = decision['timestamp'][:16]
                print(f"   {icon} {timestamp} {decision['title']}")
        else:
            print("   No decisions recorded")
    
    def task_add(self, title: str, description: str, priority: str = "medium", task_type: str = "feature"):
        """Создать новую задачу"""
        # Преобразуем строковые параметры в енумы
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }
        
        type_map = {
            "bug": TaskType.BUG_FIX,
            "feature": TaskType.FEATURE,
            "refactor": TaskType.REFACTOR,
            "docs": TaskType.DOCS,
            "analysis": TaskType.ANALYSIS,
            "investigation": TaskType.INVESTIGATION
        }
        
        task_priority = priority_map.get(priority.lower(), TaskPriority.MEDIUM)
        task_type_enum = type_map.get(task_type.lower(), TaskType.FEATURE)
        
        task_id = self.task_tracker.create_task(
            title=title,
            description=description,
            priority=task_priority,
            task_type=task_type_enum
        )
        
        print_success(f"Created task {task_id[:8]}: {title}")
        
        # Записываем решение о создании задачи в протокол
        self.execution_protocol.record_decision(
            DecisionType.ANALYSIS,
            f"Created task: {title}",
            f"Task {task_id} created via DevFlow: {description}",
            task_id=task_id
        )
    
    def task_list(self, status: str = None, priority: str = None):
        """Показать список задач с фильтрацией"""
        # Фильтры
        status_filter = None
        if status:
            status_map = {
                "pending": TaskStatus.PENDING,
                "progress": TaskStatus.IN_PROGRESS,
                "completed": TaskStatus.COMPLETED,
                "blocked": TaskStatus.BLOCKED,
                "cancelled": TaskStatus.CANCELLED
            }
            status_filter = status_map.get(status.lower())
        
        priority_filter = None
        if priority:
            priority_map = {
                "low": TaskPriority.LOW,
                "medium": TaskPriority.MEDIUM,
                "high": TaskPriority.HIGH,
                "critical": TaskPriority.CRITICAL
            }
            priority_filter = priority_map.get(priority.lower())
        
        tasks = self.task_tracker.list_tasks(
            status=status_filter,
            priority=priority_filter
        )
        
        if not tasks:
            print_info("No tasks found")
            return
        
        print_header(f"📋 DevFlow Tasks ({len(tasks)} found)")
        
        for task in tasks:
            # Иконки статуса
            status_icons = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "blocked": "🚫", 
                "cancelled": "❌"
            }
            
            # Цвета приоритета
            priority_colors = {
                1: "",  # Low - без цвета
                2: Colors.BLUE,  # Medium
                3: Colors.WARNING,  # High  
                4: Colors.FAIL  # Critical
            }
            
            icon = status_icons.get(task.get('status', 'pending'), "❓")
            priority_color = priority_colors.get(task.get('priority', 2), "")
            
            task_id = task['id'][:8]
            title = task['title']
            created = task.get('created_at', 'unknown')[:10]
            
            print(f"{priority_color}{icon} {task_id} {title} ({created}){Colors.ENDC}")
            
            # Дополнительная информация
            if task.get('description'):
                desc = task['description'][:80] + "..." if len(task['description']) > 80 else task['description']
                print(f"   {desc}")
            
            if task.get('commit_hash'):
                print(f"   📝 Commit: {task['commit_hash'][:8]}")
            
            deps = task.get('dependencies', [])
            if deps:
                print(f"   🔗 Dependencies: {', '.join([d[:6] for d in deps])}")
    
    def task_start(self, task_id: str):
        """Начать выполнение задачи"""
        # Найти задачу
        task = self.task_tracker.get_task(task_id)
        if not task:
            print_error(f"Task {task_id} not found")
            return
        
        # Проверить зависимости
        if not self.task_tracker.can_start_task(task_id):
            print_error("Task has unresolved dependencies")
            return
        
        # Начать выполнение
        session_id = self.execution_protocol.start_task_execution(task_id)
        print_success(f"Started execution session {session_id[:8]} for task {task_id[:8]}")
        print_info(f"Task: {task['title']}")
        print_info("Use 'protocol' commands to track progress")
    
    def task_complete(self, task_id: str, result_description: str = "Task completed via DevFlow"):
        """Завершить задачу"""
        task = self.task_tracker.get_task(task_id)
        if not task:
            print_error(f"Task {task_id} not found")
            return
        
        # Обновить статус
        if self.task_tracker.update_task_status(task_id, TaskStatus.COMPLETED):
            print_success(f"Completed task {task_id[:8]}: {task['title']}")
            
            # Записать результат в протокол
            self.execution_protocol.record_decision(
                DecisionType.RESULT,
                f"Task {task_id[:8]} completed",
                result_description,
                task_id=task_id
            )
        else:
            print_error("Failed to update task status")
    
    def protocol_problem(self, title: str, description: str):
        """Зафиксировать проблему в протоколе выполнения"""
        decision_id = self.execution_protocol.report_problem(title, description)
        print_success(f"Reported problem {decision_id[:8]}: {title}")
        print_info("Use 'protocol solution' to propose a solution")
    
    def protocol_solution(self, description: str, problem_id: str = None):
        """Предложить решение проблемы"""
        if problem_id:
            decision_id = self.execution_protocol.propose_solution(problem_id, description)
            if decision_id:
                print_success(f"Proposed solution {decision_id[:8]}")
            else:
                print_error(f"Problem {problem_id} not found")
        else:
            # Создать общее решение
            decision_id = self.execution_protocol.record_decision(
                DecisionType.SOLUTION,
                "General solution",
                description
            )
            print_success(f"Recorded solution {decision_id[:8]}")
    
    def protocol_result(self, description: str):
        """Записать результат выполнения"""
        decision_id = self.execution_protocol.record_decision(
            DecisionType.RESULT,
            "Execution result",
            description
        )
        print_success(f"Recorded result {decision_id[:8]}")
    
    def analyze(self):
        """Анализ workflow паттернов и продуктивности"""
        print_header("🔍 DevFlow Workflow Analysis")
        
        analysis = self.execution_protocol.analyze_workflow_patterns()
        
        print("\n📊 Decision Patterns:")
        for dec_type, count in analysis['decision_patterns'].items():
            print(f"   {dec_type}: {count}")
        
        print("\n⚡ Phase Productivity:")
        for phase, decisions in analysis['most_productive_phases'].items():
            if decisions:
                avg = sum(decisions) / len(decisions)
                print(f"   {phase}: {avg:.1f} avg decisions")
        
        # Git активность
        if self.git.is_git_repo():
            recent_commits = self.git.get_recent_commits(limit=10)
            print(f"\n📝 Recent Git Activity:")
            print(f"   Last 10 commits span: {len(recent_commits)} commits")
            if recent_commits:
                latest = recent_commits[0]
                print(f"   Latest: {latest.hash[:8]} - {latest.message}")
        
        # Workflow рекомендации
        print("\n💡 Workflow Recommendations:")
        
        stats = self.task_tracker.get_statistics()
        if stats['completion_rate'] < 50:
            print("   🎯 Focus on completing existing tasks before creating new ones")
        
        if len(analysis['decision_patterns']) < 5:
            print("   📝 Use protocol commands more frequently to track decisions")
        
        active_tasks = self.task_tracker.list_tasks(status=TaskStatus.IN_PROGRESS)
        if len(active_tasks) > 3:
            print("   ⚠️  Consider reducing work-in-progress tasks for better focus")
        
        # Productivity insights
        print("\n📈 Productivity Insights:")
        total_decisions = sum(analysis['decision_patterns'].values())
        if total_decisions > 0:
            problem_ratio = analysis['decision_patterns'].get('DecisionType.PROBLEM', 0) / total_decisions
            solution_ratio = analysis['decision_patterns'].get('DecisionType.SOLUTION', 0) / total_decisions
            
            if problem_ratio > 0.3:
                print("   🚨 High problem-to-solution ratio - consider preventive measures")
            elif solution_ratio > problem_ratio:
                print("   ✨ Good solution generation - proactive problem solving")
    
    def sync_drommage(self):
        """Синхронизация с DRommage (если доступен)"""
        print_header("🔗 DevFlow ↔ DRommage Sync")
        
        drommage_dir = self.project_root / ".drommage"
        if not drommage_dir.exists():
            print_warning("DRommage not detected in this project")
            print_info("DevFlow can work independently or alongside DRommage")
            return
        
        print_info("DRommage integration detected")
        
        # Проверяем есть ли анализы DRommage
        llm_cache_dir = self.project_root / ".llm_cache"
        if llm_cache_dir.exists():
            cache_files = list(llm_cache_dir.glob("*.json"))
            print(f"   📊 Found {len(cache_files)} DRommage analyses")
            
            # Можно создать задачи на основе проблемных коммитов
            print_info("Consider creating tasks for commits with identified issues")
        
        # Обновляем конфигурацию
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['integration']['drommage'] = True
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print_success("DevFlow ↔ DRommage integration enabled")


def show_help():
    """Показать справку DevFlow"""
    print_header("📖 DevFlow - Development Workflow Management")
    print("""
PHILOSOPHY:
DevFlow is a standalone development workflow management tool that provides
structured decision tracking and task management for any software project.

COMMANDS:

📊 Project Status:
    status                          Show project and workflow status

📋 Task Management:
    task add "title" "description"  Create new task
    task list [status] [priority]   List tasks (optional filters)
    task start <task_id>            Start task execution
    task complete <task_id>         Complete task

⚡ Execution Protocol:
    protocol problem "title" "desc" Report a problem
    protocol solution "description" Propose solution
    protocol result "description"   Record execution result

🔍 Analysis:
    analyze                         Analyze workflow patterns

🔗 Integration:
    sync drommage                   Enable DRommage integration

EXAMPLES:
    python devflow.py task add "Fix authentication bug" "Users can't login via OAuth" high bug
    python devflow.py task list pending high
    python devflow.py task start a1b2c3d4
    python devflow.py protocol problem "API timeout" "External service not responding"
    python devflow.py analyze
    """)


def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    manager = DevFlowManager()
    command = sys.argv[1].lower()
    
    try:
        if command == "status":
            manager.status()
        
        elif command == "task":
            if len(sys.argv) < 3:
                print_error("Task command requires subcommand")
                return
            
            subcommand = sys.argv[2].lower()
            
            if subcommand == "add":
                if len(sys.argv) < 5:
                    print_error("Usage: task add \"title\" \"description\" [priority] [type]")
                    return
                title = sys.argv[3]
                description = sys.argv[4]
                priority = sys.argv[5] if len(sys.argv) > 5 else "medium"
                task_type = sys.argv[6] if len(sys.argv) > 6 else "feature"
                manager.task_add(title, description, priority, task_type)
            
            elif subcommand == "list":
                status_filter = sys.argv[3] if len(sys.argv) > 3 else None
                priority_filter = sys.argv[4] if len(sys.argv) > 4 else None
                manager.task_list(status_filter, priority_filter)
            
            elif subcommand == "start":
                if len(sys.argv) < 4:
                    print_error("Usage: task start <task_id>")
                    return
                task_id = sys.argv[3]
                manager.task_start(task_id)
            
            elif subcommand == "complete":
                if len(sys.argv) < 4:
                    print_error("Usage: task complete <task_id>")
                    return
                task_id = sys.argv[3]
                result = sys.argv[4] if len(sys.argv) > 4 else "Task completed via DevFlow"
                manager.task_complete(task_id, result)
            
            else:
                print_error(f"Unknown task subcommand: {subcommand}")
        
        elif command == "protocol":
            if len(sys.argv) < 3:
                print_error("Protocol command requires subcommand")
                return
            
            subcommand = sys.argv[2].lower()
            
            if subcommand == "problem":
                if len(sys.argv) < 5:
                    print_error("Usage: protocol problem \"title\" \"description\"")
                    return
                title = sys.argv[3]
                description = sys.argv[4]
                manager.protocol_problem(title, description)
            
            elif subcommand == "solution":
                if len(sys.argv) < 4:
                    print_error("Usage: protocol solution \"description\" [problem_id]")
                    return
                description = sys.argv[3]
                problem_id = sys.argv[4] if len(sys.argv) > 4 else None
                manager.protocol_solution(description, problem_id)
            
            elif subcommand == "result":
                if len(sys.argv) < 4:
                    print_error("Usage: protocol result \"description\"")
                    return
                description = sys.argv[3]
                manager.protocol_result(description)
            
            else:
                print_error(f"Unknown protocol subcommand: {subcommand}")
        
        elif command == "analyze":
            manager.analyze()
        
        elif command == "sync":
            if len(sys.argv) > 2 and sys.argv[2].lower() == "drommage":
                manager.sync_drommage()
            else:
                print_error("Usage: sync drommage")
        
        elif command == "help":
            show_help()
        
        else:
            print_error(f"Unknown command: {command}")
            show_help()
    
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()