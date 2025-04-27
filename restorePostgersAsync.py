import os
import asyncpg
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()

class AsyncPGIntegrityChecker:
    def __init__(self):
        self.pool = None
        self.tables = []
        self.database_name = os.getenv("PG_DBNAME")

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            database=os.getenv("PG_DBNAME"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT"),
            min_size=5,
            max_size=20
        )
        await self._create_log_table()
        await self._get_table_list()

    async def close(self):
        await self.pool.close()

    async def _create_log_table(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DROP TABLE IF EXISTS integrity_log;
                CREATE TABLE IF NOT EXISTS integrity_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    database_name VARCHAR(255),
                    table_name VARCHAR(255),
                    issue TEXT,
                    action TEXT
                )
            """)

    async def _get_table_list(self):
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            self.tables = [r['tablename'] for r in records]

    async def get_table_name(self, relid):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT relname FROM pg_class WHERE oid = $1", relid
            )

    async def get_column_names(self, table, column_numbers):
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT attname
                FROM pg_attribute
                WHERE attrelid = $1::regclass AND attnum = ANY($2::int[])
                ORDER BY attnum
                """,
                table, column_numbers
            )
            return [r['attname'] for r in records]

    async def log_issue(self, table, issue, action="logged"):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO integrity_log (database_name, table_name, issue, action)
                VALUES ($1, $2, $3, $4)
                """,
                self.database_name, table, issue, action
            )

    async def check_constraints(self, table):
        async with self.pool.acquire() as conn:
            # Получение ограничений
            constraints = await conn.fetch(
                """
                SELECT oid, conname, contype, conkey
                FROM pg_constraint
                WHERE conrelid = $1::regclass
                """,
                table
            )

            for constraint in constraints:
                oid = constraint['oid']
                conname = constraint['conname']
                contype = constraint['contype']
                conkey = constraint['conkey']

                if contype in ('p', 'u'):
                    await self._check_unique_constraint(table, conname, conkey)
                elif contype == 'f':
                    await self._check_foreign_key(table, oid, conname, conkey)

    async def _check_unique_constraint(self, table, conname, conkey):
        columns = await self.get_column_names(table, conkey)
        column_list = ', '.join(columns)
        
        async with self.pool.acquire() as conn:
            # Проверка на дубликаты
            duplicates = await conn.fetch(
                f"""
                SELECT {column_list}, COUNT(*)
                FROM {table}
                GROUP BY {column_list}
                HAVING COUNT(*) > 1
                """
            )
            
            if duplicates:
                for dup in duplicates:
                    issue = f"Duplicate values found for unique constraint '{conname}' ({column_list}): {dict(dup)}"
                    await self.log_issue(table, issue)
                    print(f"[WARNING] {issue}")
    
    async def _check_foreign_key(self, table, oid, conname, conkey):
        async with self.pool.acquire() as conn:
            # Получение информации о внешнем ключе
            fk_info = await conn.fetchrow(
                """
                SELECT confrelid, confkey
                FROM pg_constraint
                WHERE oid = $1
                """,
                oid
            )
            
            if not fk_info:
                return
            
            ref_table_oid = fk_info['confrelid']
            ref_columns = fk_info['confkey']
            
            # Получение имени таблицы, на которую ссылается внешний ключ
            ref_table = await self.get_table_name(ref_table_oid)
            
            # Получение имен столбцов
            columns = await self.get_column_names(table, conkey)
            ref_columns = await self.get_column_names(ref_table, ref_columns)
            
            # Проверка целостности внешнего ключа
            orphaned = await conn.fetch(
                f"""
                SELECT t.{columns[0]}
                FROM {table} t
                LEFT JOIN {ref_table} r ON t.{columns[0]} = r.{ref_columns[0]}
                WHERE r.{ref_columns[0]} IS NULL AND t.{columns[0]} IS NOT NULL
                LIMIT 100
                """
            )
            
            if orphaned:
                issue = f"Foreign key constraint '{conname}' violation: {len(orphaned)} rows in '{table}' reference non-existent values in '{ref_table}'"
                await self.log_issue(table, issue)
                print(f"[ERROR] {issue}")
    
    async def check_not_null_constraints(self, table):
        async with self.pool.acquire() as conn:
            # Получение столбцов с ограничением NOT NULL
            not_null_columns = await conn.fetch(
                """
                SELECT attname
                FROM pg_attribute
                WHERE attrelid = $1::regclass
                AND attnotnull = true
                AND attnum > 0
                AND NOT attisdropped
                """,
                table
            )
            
            for column in not_null_columns:
                col_name = column['attname']
                # Проверка на NULL значения
                null_count = await conn.fetchval(
                    f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE {col_name} IS NULL
                    """
                )
                
                if null_count > 0:
                    issue = f"NOT NULL constraint violation: Column '{col_name}' contains {null_count} NULL values"
                    await self.log_issue(table, issue)
                    print(f"[ERROR] {issue}")
    
    async def check_toast_tables(self, table):
        async with self.pool.acquire() as conn:
            # Получение TOAST-таблицы для данной таблицы
            toast_relid = await conn.fetchval(
                """
                SELECT reltoastrelid
                FROM pg_class
                WHERE relname = $1 AND relkind = 'r'
                """,
                table
            )
            
            if toast_relid and toast_relid != 0:
                toast_table = await self.get_table_name(toast_relid)
                
                # Проверка версии PostgreSQL
                version = await conn.fetchval("SHOW server_version")
                major_version = int(version.split('.')[0])
                
                if major_version < 12:
                    # Для PostgreSQL до версии 12
                    has_oids = await conn.fetchval(
                        """
                        SELECT relhasoids
                        FROM pg_class
                        WHERE relname = $1
                        """,
                        table
                    )
                    
                    if has_oids:
                        # Проверка на наличие осиротевших записей в TOAST-таблице
                        orphaned_count = await conn.fetchval(
                            f"""
                            SELECT COUNT(*) FROM {toast_table} t
                            LEFT JOIN {table} m ON t.chunk_id = m.oid
                            WHERE m.oid IS NULL
                            """
                        )
                        
                        if orphaned_count > 0:
                            issue = f"Orphaned records found in TOAST table {toast_table} for table {table}: {orphaned_count} records"
                            await self.log_issue(table, issue)
                            print(f"[ERROR] {issue}")
                    else:
                        issue = f"Table {table} does not have OIDs, TOAST check is not applicable"
                        await self.log_issue(table, issue)
                        print(f"[INFO] {issue}")
                else:
                    # Для PostgreSQL 12 и выше
                    issue = f"TOAST check for PostgreSQL 12+ is not implemented for table {table}"
                    await self.log_issue(table, issue)
                    print(f"[INFO] {issue}")
    
    async def check_table_integrity(self, table):
        print(f"Checking integrity for table: {table}")
        try:
            await self.check_constraints(table)
            await self.check_not_null_constraints(table)
            await self.check_toast_tables(table)
            print(f"Integrity check completed for table: {table}")
        except Exception as e:
            print(f"Error checking table {table}: {str(e)}")
            await self.log_issue(table, f"Error during integrity check: {str(e)}")
    
    async def check_database_integrity(self):
        print(f"Starting database integrity check at {datetime.now()}")
        print(f"Found {len(self.tables)} tables to check")
        
        # Создаем семафор для ограничения количества одновременных задач
        semaphore = asyncio.Semaphore(5)  # Максимум 5 одновременных проверок
        
        async def bounded_check(table):
            async with semaphore:
                await self.check_table_integrity(table)
        
        # Создаем список задач
        tasks = [bounded_check(table) for table in self.tables]
        
        # Запускаем задачи с ограничением параллельности и ждем их завершения
        # Важно: дожидаемся завершения всех задач перед возвратом из функции
        await asyncio.gather(*tasks)
        print(f"Database integrity check completed at {datetime.now()}")

async def main():
    checker = AsyncPGIntegrityChecker()
    try:
        print("Connecting to database...")
        await checker.connect()
        print("Connection established")
        
        # Выполняем проверку целостности базы данных и ждем завершения всех задач
        try:
            await checker.check_database_integrity()
            print("All integrity checks completed successfully")
        finally:
            # Закрываем соединение только после завершения всех задач
            if checker.pool:
                await checker.close()
                print("Database connection closed")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())