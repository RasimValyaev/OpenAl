import os
import psycopg2
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение данных для подключения из переменных окружения
user = os.getenv("PG_USER")
password = os.getenv("PG_PASSWORD")
host = os.getenv("PG_HOST")
port = os.getenv("PG_PORT")
dbname = os.getenv("PG_DBNAME_MEDOC")

# Подключение к базе данных
conn = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port
)

# Создание таблицы логов, если она не существует
with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS integrity_log (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            table_name VARCHAR(255),
            issue TEXT,
            action TEXT
        )
    """)
conn.commit()

# Получение списка таблиц из схемы 'public'
with conn.cursor() as cur:
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    tables = [row[0] for row in cur.fetchall()]

# Функция для получения имени таблицы по OID
def get_table_name(conn, relid):
    with conn.cursor() as cur:
        cur.execute("SELECT relname FROM pg_class WHERE oid = %s", (relid,))
        return cur.fetchone()[0]

# Функция для получения имен столбцов по номеру столбца
def get_column_names(conn, table, column_numbers):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT attname
            FROM pg_attribute
            WHERE attrelid = %s::regclass AND attnum IN %s
        """, (table, tuple(column_numbers)))
        return [row[0] for row in cur.fetchall()]

# Функция для записи в лог
def log_issue(conn, table, issue, action="logged"):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO integrity_log (table_name, issue, action)
            VALUES (%s, %s, %s)
        """, (table, issue, action))
    conn.commit()

# Проверка целостности для каждой таблицы
for table in tables:
    try:
        # Логируем начало проверки
        log_issue(conn, table, f"Начало проверки целостности таблицы {table}")

        # Получение списка ограничений
        with conn.cursor() as cur:
            cur.execute("""
                SELECT oid, conname, contype, conkey
                FROM pg_constraint
                WHERE conrelid = %s::regclass
            """, (table,))
            constraints = cur.fetchall()

        # Проверка первичных и уникальных ключей
        for constraint in constraints:
            oid, conname, contype, conkey = constraint
            if contype in ('p', 'u'):  # 'p' - первичный ключ, 'u' - уникальный ключ
                columns = get_column_names(conn, table, conkey)
                column_list = ', '.join(columns)
                query = f"""
                    SELECT COUNT(*) FROM (
                        SELECT {column_list}, COUNT(*)
                        FROM {table}
                        GROUP BY {column_list}
                        HAVING COUNT(*) > 1
                    ) AS sub
                """
                with conn.cursor() as cur:
                    cur.execute(query)
                    count = cur.fetchone()[0]
                if count > 0:
                    issue = f"Найдены дубликаты в ограничении {conname} ({column_list})"
                    log_issue(conn, table, issue)

            # Проверка внешних ключей
            elif contype == 'f':  # 'f' - внешний ключ
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT confrelid, confkey
                        FROM pg_constraint
                        WHERE oid = %s
                    """, (oid,))
                    confrelid, confkey = cur.fetchone()
                target_table = get_table_name(conn, confrelid)
                target_columns = get_column_names(conn, target_table, confkey)
                source_columns = get_column_names(conn, table, conkey)
                join_conditions = ' AND '.join([f"t.{src} = tt.{tgt}" for src, tgt in zip(source_columns, target_columns)])
                query = f"""
                    SELECT COUNT(*) FROM {table} t
                    LEFT JOIN {target_table} tt ON {join_conditions}
                    WHERE tt.{target_columns[0]} IS NULL
                """
                with conn.cursor() as cur:
                    cur.execute(query)
                    count = cur.fetchone()[0]
                if count > 0:
                    issue = f"Найдены некорректные ссылки в ограничении внешнего ключа {conname}"
                    log_issue(conn, table, issue)

        # Проверка столбцов NOT NULL
        with conn.cursor() as cur:
            cur.execute("""
                SELECT attname
                FROM pg_attribute
                WHERE attrelid = %s::regclass AND attnotnull = true AND attnum > 0
            """, (table,))
            notnull_columns = [row[0] for row in cur.fetchall()]
        for column in notnull_columns:
            query = f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL"
            with conn.cursor() as cur:
                cur.execute(query)
                count = cur.fetchone()[0]
            if count > 0:
                issue = f"Найдены NULL значения в столбце {column} с ограничением NOT NULL"
                log_issue(conn, table, issue)

        # Проверка связей с pg_toast
        with conn.cursor() as cur:
            cur.execute("""
                SELECT reltoastrelid
                FROM pg_class
                WHERE relname = %s AND relkind = 'r'
            """, (table,))
            toast_relid = cur.fetchone()
            if toast_relid and toast_relid[0] != 0:
                toast_table = get_table_name(conn, toast_relid[0])
                # В PostgreSQL 12 и выше столбец relhasoids был удален
                # Проверяем версию PostgreSQL
                cur.execute("SHOW server_version")
                version = cur.fetchone()[0]
                major_version = int(version.split('.')[0])
                
                if major_version < 12:
                    # Для PostgreSQL до версии 12
                    cur.execute("""
                        SELECT relhasoids
                        FROM pg_class
                        WHERE relname = %s
                    """, (table,))
                    has_oids = cur.fetchone()[0]
                    if has_oids:
                        # Проверка на наличие осиротевших записей в TOAST-таблице
                        query = f"""
                            SELECT COUNT(*) FROM {toast_table} t
                            LEFT JOIN {table} m ON t.chunk_id = m.oid
                            WHERE m.oid IS NULL
                        """
                        with conn.cursor() as cur:
                            cur.execute(query)
                            count = cur.fetchone()[0]
                        if count > 0:
                            issue = f"Найдены осиротевшие записи в TOAST-таблице {toast_table} для таблицы {table}"
                            log_issue(conn, table, issue)
                    else:
                        issue = f"Таблица {table} не имеет OID, проверка TOAST не применима"
                        log_issue(conn, table, issue)
                else:
                    # Для PostgreSQL 12 и выше
                    issue = f"Проверка TOAST для PostgreSQL 12+ не реализована для таблицы {table}"
                    log_issue(conn, table, issue)

        # Логируем успешное завершение проверки
        log_issue(conn, table, f"Проверка целостности таблицы {table} завершена")

    except Exception as e:
        # Логируем ошибку выполнения
        issue = f"Ошибка при проверке таблицы {table}: {str(e)}"
        log_issue(conn, table, issue, action="ошибка зафиксирована")

# Закрытие соединения
conn.close()