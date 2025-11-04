#!/usr/bin/env python3
"""
Прямой тест анализа без интерфейса
"""

from drommage.core.git_integration import GitIntegration
from drommage.core.llm_analyzer import LLMAnalyzer, AnalysisLevel

def test_direct():
    print("🔍 Тестирую анализ напрямую...")
    
    # Инициализация
    git = GitIntegration()
    commits = git.get_recent_commits(limit=5)
    
    if len(commits) < 2:
        print("❌ Нужно минимум 2 коммита")
        return
    
    current = commits[0]
    prev = commits[1]
    
    print(f"📄 Анализ: {prev.short_hash} → {current.short_hash}")
    
    # Получить diff
    diff = git.get_commit_diff(prev.hash, current.hash)
    if not diff:
        print("❌ Не могу получить diff")
        return
        
    print(f"📝 Diff получен: {len(diff.diff_text)} символов")
    
    # Получить содержимое файлов
    if diff.files:
        main_file = diff.files[0]
        prev_content = git.get_file_content_at_commit(prev.hash, main_file)
        curr_content = git.get_file_content_at_commit(current.hash, main_file)
        
        print(f"📁 Файл: {main_file}")
        print(f"📄 Prev content: {len(prev_content) if prev_content else 0} chars")
        print(f"📄 Curr content: {len(curr_content) if curr_content else 0} chars")
        
        # Запуск анализа
        analyzer = LLMAnalyzer()
        if not analyzer.ollama_available:
            print("❌ Ollama недоступен")
            return
            
        print("🤖 Запускаю LLM анализ...")
        
        try:
            result = analyzer.analyze_diff(
                prev_content or "",
                curr_content or diff.diff_text,
                f"{prev.short_hash}→{current.short_hash}: {current.message[:30]}",
                AnalysisLevel.BRIEF
            )
            
            print("✅ АНАЛИЗ ЗАВЕРШЕН!")
            print(f"📋 Summary: {result.summary}")
            print(f"🏷️  Type: {result.change_type}")
            print(f"📊 Impact: {result.impact_level}")
            
        except Exception as e:
            print(f"❌ Ошибка анализа: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Нет измененных файлов")

if __name__ == "__main__":
    test_direct()