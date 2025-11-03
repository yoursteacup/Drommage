#!/usr/bin/env python3
"""
Show control hints for DRommage v8
"""

def show_controls():
    print("\n" + "=" * 60)
    print(" DRommage v8 - Управление")
    print("=" * 60)
    
    print("\n📍 ОСНОВНОЙ РЕЖИМ (View):")
    print("  [↑↓]      - навигация по версиям")
    print("  [D]       - глубокий LLM анализ изменений")
    print("  [R]       - детальный просмотр региона")
    print("  [PgUp/Dn] - прокрутка документа")
    print("  [Q]       - выход из программы")
    
    print("\n🔍 РЕЖИМ ГЛУБОКОГО АНАЛИЗА (Deep Analysis):")
    print("  [ESC]     - вернуться назад")
    print("  [↑↓]      - прокрутка анализа")
    
    print("\n🧩 РЕЖИМ ДЕТАЛЕЙ РЕГИОНА (Region Detail):")
    print("  [ESC]     - вернуться назад")
    
    print("\n" + "-" * 60)
    print("💡 ПОДСКАЗКИ:")
    print("  • Подсказки всегда видны внизу экрана")
    print("  • Во время анализа показывается статус:")
    print("    - 📦 Using cached analysis")
    print("    - 📊 Analyzing: X lines, Y chars diff")  
    print("    - 📝 Prompt size: X chars, Level: brief/detailed")
    print("    - 🤖 Starting LLM inference...")
    print("    - ✅ Analysis complete (X.Xs)")
    print("    - ⏱️ LLM timeout (30s)")
    print("    - ❌ LLM error: ...")
    
    print("\n" + "-" * 60)
    print("🎨 ВИЗУАЛЬНЫЕ ИНДИКАТОРЫ:")
    print("  • Цвета регионов:")
    print("    - Фиолетовый - часто изменяемые (volatile)")
    print("    - Синий      - стабильные")
    print("    - Желтый     - умеренно изменяемые")
    print("  • Типы изменений:")
    print("    - 📝 Documentation")
    print("    - 🚀 Feature")
    print("    - 🔧 Refactor")
    print("    - 🐛 Bugfix")
    print("    - ⚡ Performance")
    print("    - 🔒 Security")
    print("    - 💥 Breaking changes")
    print("    - ✨ Minor changes")
    
    print("\n" + "=" * 60)
    print("🚀 Запустите 'python main_v8.py' для старта")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    show_controls()