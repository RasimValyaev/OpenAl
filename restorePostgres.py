import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
from dotenv import dotenv_values

# Загрузка переменных окружения
config = dotenv_values(".env")


def connect_to_db(config):
    """Подключение к базе данных PostgreSQL."""
    # импортируем данные из файла .env
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("PG_MEDOC"),
            user=os.getenv("PG_MEDOC_USER"),
            password=os.getenv("PG_MEDOC_PASSWORD"),
            host=os.getenv("PG_MEDOC_HOST"),
            port=os.getenv("PG_MEDOC_PORT"),
        )
        return conn
    except Exception as e:
        raise Exception(f"Ошибка подключения к базе данных: {str(e)}")


def create_log_table(conn):
    """Создание таблицы для логов, если она еще не существует."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS integrity_check_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                table_name VARCHAR(255),
                constraint_name VARCHAR(255),
                check_type VARCHAR(50),
                status VARCHAR(10),
                details TEXT,
                suggestion TEXT
            )
        """
        )
        conn.commit()


def log_result(
    cur, table_name, check_type, status, details, suggestion, constraint_name=None
):
    """Запись результатов проверки в таблицу логов."""
    cur.execute(
        """
        INSERT INTO integrity_check_log (table_name, constraint_name, check_type, status, details, suggestion)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
        (table_name, constraint_name, check_type, status, details, suggestion),
    )


def get_tables(conn):
    """Получение списка всех таблиц в схеме 'public'."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """
        )
        return [row[0] for row in cur.fetchall()]


def get_constraints(conn, table_name):
    """Получение всех ограничений для указанной таблицы."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT conname, contype, conkey, confrelid, confkey, consrc
            FROM pg_constraint
            WHERE conrelid = %s::regclass
        """,
            (table_name,),
        )
        return cur.fetchall()


def get_column_names(conn, table_name, column_numbers):
    """Получение имен столбцов по их номерам."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT attname
            FROM pg_attribute
            WHERE attrelid = %s::regclass AND attnum = ANY(%s)
            ORDER BY array_position(%s, attnum)
        """,
            (table_name, column_numbers, column_numbers),
        )
        return [row[0] for row in cur.fetchall()]


def get_referenced_table_name(conn, confrelid):
    """Получение имени целевой таблицы для foreign key."""
    with conn.cursor() as cur:
        cur.execute("SELECT relname FROM pg_class WHERE oid = %s", (confrelid,))
        return cur.fetchone()[0]


def check_primary_or_unique(conn, table_name, conname, contype, columns):
    """Проверка первичного ключа или уникального ограничения."""
    with conn.cursor() as cur:
        check_type = "PRIMARY KEY" if contype == "p" else "UNIQUE"
        columns_str = ", ".join(columns)
        where_not_null = " AND ".join([f"{col} IS NOT NULL" for col in columns])
        query = f"""
            SELECT COUNT(*) FROM (
                SELECT {columns_str} 
                FROM {table_name} 
                WHERE {where_not_null} 
                GROUP BY {columns_str} 
                HAVING COUNT(*) > 1
            ) AS subquery
        """
        cur.execute(query)
        violation_count = cur.fetchone()[0]
        status = "FAIL" if violation_count > 0 else "PASS"
        details = (
            f"Найдено {violation_count} групп дубликатов"
            if violation_count > 0
            else "Дубликаты отсутствуют"
        )
        suggestion = (
            "Удалите дублирующиеся строки или измените ограничение"
            if violation_count > 0
            else ""
        )

        # Для первичного ключа дополнительно проверяем NULL
        if contype == "p":
            null_check_query = (
                f"SELECT COUNT(*) FROM {table_name} WHERE "
                + " OR ".join([f"{col} IS NULL" for col in columns])
            )
            cur.execute(null_check_query)
            null_count = cur.fetchone()[0]
            if null_count > 0:
                status = "FAIL"
                details += (
                    f"; Найдено {null_count} строк с NULL в столбцах первичного ключа"
                )
                suggestion += (
                    "; Убедитесь, что столбцы первичного ключа не содержат NULL"
                )

        log_result(cur, table_name, check_type, status, details, suggestion, conname)


def check_foreign_key(conn, table_name, conname, fk_columns, ref_table, ref_columns):
    """Проверка внешнего ключа."""
    with conn.cursor() as cur:
        check_type = "FOREIGN KEY"
        where_not_null = " AND ".join(
            [f"{table_name}.{col} IS NOT NULL" for col in fk_columns]
        )
        exists_conditions = " AND ".join(
            [
                f"{ref_table}.{ref_col} = {table_name}.{fk_col}"
                for ref_col, fk_col in zip(ref_columns, fk_columns)
            ]
        )
        query = f"""
            SELECT COUNT(*) 
            FROM {table_name} 
            WHERE {where_not_null} AND NOT EXISTS (
                SELECT 1 FROM {ref_table} WHERE {exists_conditions}
            )
        """
        cur.execute(query)
        violation_count = cur.fetchone()[0]
        status = "FAIL" if violation_count > 0 else "PASS"
        details = (
            f"Найдено {violation_count} строк с некорректными ссылками внешнего ключа"
            if violation_count > 0
            else "Все ссылки внешнего ключа корректны"
        )
        suggestion = (
            "Исправьте значения внешнего ключа или добавьте недостающие строки в целевую таблицу"
            if violation_count > 0
            else ""
        )
        log_result(cur, table_name, check_type, status, details, suggestion, conname)


def check_check_constraint(conn, table_name, conname, consrc):
    """Проверка ограничения CHECK."""
    with conn.cursor() as cur:
        check_type = "CHECK"
        query = f"SELECT COUNT(*) FROM {table_name} WHERE NOT ({consrc})"
        cur.execute(query)
        violation_count = cur.fetchone()[0]
        status = "FAIL" if violation_count > 0 else "PASS"
        details = (
            f"Найдено {violation_count} строк, нарушающих ограничение CHECK"
            if violation_count > 0
            else "Все строки удовлетворяют ограничению CHECK"
        )
        suggestion = (
            "Исправьте данные, чтобы они соответствовали условию проверки"
            if violation_count > 0
            else ""
        )
        log_result(cur, table_name, check_type, status, details, suggestion, conname)


def check_table_readability(conn, table_name):
    """Проверка базовой читаемости таблицы."""
    with conn.cursor() as cur:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cur.fetchone()[0]
            status = "PASS"
            details = f"Таблица содержит {row_count} строк"
            suggestion = ""
        except Exception as e:
            status = "FAIL"
            details = f"Ошибка при чтении таблицы: {str(e)}"
            suggestion = (
                "Проверьте таблицу на наличие повреждений или проблем с доступом"
            )
        log_result(cur, table_name, "TABLE_READ", status, details, suggestion)


def main(config):
    """Основная функция для проверки целостности таблиц."""
    conn = connect_to_db(config)
    try:
        create_log_table(conn)
        tables = get_tables(conn)

        for table in tables:
            print(f"Проверка таблицы: {table}")
            with conn.cursor() as cur:
                # Получение ограничений
                constraints = get_constraints(conn, table)

                for constraint in constraints:
                    conname, contype, conkey, confrelid, confkey, consrc = constraint
                    columns = get_column_names(conn, table, conkey)

                    if contype in ("p", "u"):  # Primary key или Unique
                        check_primary_or_unique(conn, table, conname, contype, columns)
                    elif contype == "f":  # Foreign key
                        ref_table = get_referenced_table_name(conn, confrelid)
                        ref_columns = get_column_names(conn, ref_table, confkey)
                        check_foreign_key(
                            conn, table, conname, columns, ref_table, ref_columns
                        )
                    elif contype == "c":  # Check constraint
                        check_check_constraint(conn, table, conname, consrc)

                # Проверка читаемости таблицы
                check_table_readability(conn, table)
                conn.commit()
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    # Здесь предполагается, что config уже доступен
    main(config)
