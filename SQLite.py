# Description: Пример создания сводной таблицы в SQLite
# вычисляет ABC и XYZ -анализ по выручке, прибыли и количеству

import sqlite3
from typing import List, Tuple
import pandas as pd
import numpy as np

def coefficient_of_variation(data):
    x_mean = np.mean(data)  # Среднее значение x̄
    n = len(data)  # Количество элементов n
    variance = sum((x - x_mean) ** 2 for x in data) / n  # Дисперсия
    std_dev = np.sqrt(variance)  # Стандартное отклонение
    v = (std_dev / x_mean) * 100  # Коэффициент вариации в процентах
    return round(v,2)



def create_table(cursor):
    sql = """
        CREATE TABLE "transactions" (
            id INTEGER PRIMARY KEY,  -- уникальный идентификатор id
            doc_date TEXT,  -- дата документа
            sku TEXT NOT NULL,  -- артикул
            quantity INTEGER NOT NULL,  -- количество
            amount REAL,  -- сумма продаж
            profit REAL  -- прибыль
        );
    """
    cursor.execute(sql)


def get_unique_months(cursor) -> List[str]:
    cursor.execute("""
        SELECT DISTINCT 
            strftime('%Y.%m', doc_date) as month
        FROM transactions
        WHERE doc_date IS NOT NULL
        ORDER BY month
    """)
    return [row[0] for row in cursor.fetchall()]


def create_pivot_query(months: List[str]) -> str:
    month_columns = []
    for month in months:
        case_stmt = f"""
        SUM(CASE 
            WHEN strftime('%Y.%m', doc_date)= '{month}' 
            THEN amount 
            ELSE 0 
        END) as '{month}'"""
        month_columns.append(case_stmt)

    # Join all month columns with commas
    month_columns_str = ",\n        ".join(month_columns)

    # Create the full pivot query
    query = f"""
    SELECT 
        sku,
        sum(quantity) as quantity,
        sum(amount) as revenue,  -- выручка от продаж
        sum(profit) as profit,  -- прибыль
        {month_columns_str}
    FROM transactions
    GROUP BY sku
    ORDER BY sku
    """
    return query


def format_row(row: Tuple) -> str:
    return " | ".join(f"{str(val):12}" for val in row)


def main():
    try:
        # Connect to existing SQLite database
        conn = sqlite3.connect('transactions.db')
        cursor = conn.cursor()

        # Get unique months from the data
        months = get_unique_months(cursor)

        if not months:
            print("No data found in the transactions table")
            return

        # Create and execute the pivot query
        pivot_query = create_pivot_query(months)
        cursor.execute(pivot_query)
        df = pd.read_sql_query(pivot_query, conn)
        df['coefficient_of_variation'] = df.apply(lambda row: coefficient_of_variation(row[4:]), axis=1)
        print(df)
        df.to_excel("pivot_table.xlsx", index=False)

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    list1 = [0,	0,	0,	0,	0,	0,	0,	0]
    print(coefficient_of_variation(list1))
    main()
# 0       250.20
# 1       373.18
# 2      -377.97