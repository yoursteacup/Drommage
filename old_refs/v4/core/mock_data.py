# core/mock_data.py

from datetime import date

# Моковые версии документа (имена файлов должны совпадать с тем, что в /docs/)
VERSIONS = [
    {
        "version": "v0.1",
        "date": date(2024, 4, 12),
        "summary": "Initial draft",
        "filename": "v0.1.txt",
    },
    {
        "version": "v0.3",
        "date": date(2024, 5, 2),
        "summary": "Added API examples",
        "filename": "v0.3.txt",
    },
    {
        "version": "v0.6",
        "date": date(2024, 6, 10),
        "summary": "Refactoring and cleanup",
        "filename": "v0.6.txt",
    },
    {
        "version": "v1.0",
        "date": date(2024, 8, 1),
        "summary": "Stable release",
        "filename": "v1.0.txt",
    },
]
