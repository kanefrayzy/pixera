# FILE: ai_gallery/__init__.py
"""
Инициализация проекта.

- Если установлен PyMySQL, подменяем его как драйвер MySQLdb
  (это упрощает запуск на Windows/macOS без сборки mysqlclient).
- Если установлен mysqlclient (MySQLdb), ничего не делаем — он будет использован Django автоматически.
"""

# Подмена PyMySQL -> MySQLdb (без падений, если пакета нет)
try:
    import pymysql  # type: ignore

    # Важно: вызывать до инициализации Django/ORM
    pymysql.install_as_MySQLdb()
except Exception:
    # Пакет отсутствует или уже есть mysqlclient — просто продолжаем
    pass
