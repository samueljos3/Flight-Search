from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from airflow.hooks.base import BaseHook
from airflow.exceptions import AirflowException
from airflow.hooks.postgres_hook import PostgresHook
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
import json
import requests
from lib.amadeus_api import AmadeusAPI

# DEFINE DAG
dag = DAG("flight_search",
          description="DAG to search for flights and save (postgres)",
          schedule_interval=None,
          start_date=datetime(2025, 1, 1),
          catchup=False)

# FUNCTION TO MENTION THE CLASS AND FETCH FLIGHTS
def fetch_flights(**kwargs):
    api = AmadeusAPI("api_connection_amadeus")
    flights = api.data_processing("REC", "MAD", "2025-06-20")
    for flight in flights.items():
        print(flight)

    return flights

# FUNCTION TO INSERT FLIGHTS INTO THE DATABASE
def insert_flights_to_db(**kwargs):
    flights = kwargs['ti'].xcom_pull(task_ids='fetch_flights')
    pg_hook = PostgresHook(postgres_conn_id="postgres")
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    for flight in flights.values():
        flight_id = flight.get('id')
        last_ticketing_date = flight.get('lastTicketingDate')
        total_price = flight.get('totalPrice')
        base_price = flight.get('basePrice')
        bookable_seats = flight.get('numberOfBookableSeats')
        checked_bags = flight.get('checkedbags')
        segments = json.dumps(flight.get('segments'))

        cursor.execute(
            """INSERT INTO flights (flight_id, last_ticketing_date, total_price, base_price, bookable_seats, checked_bags, segments)
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (flight_id, last_ticketing_date, total_price,
             base_price, bookable_seats, checked_bags, segments))

    conn.commit()
    cursor.close()
    conn.close()


# DEFINE TASKS
fetch_flights_task = PythonOperator(
    task_id="fetch_flights",
    python_callable=fetch_flights,
    provide_context=True,
    dag=dag
)

create_table_task = SQLExecuteQueryOperator(task_id="create_table",
                                            conn_id="postgres",
                                            sql="""CREATE TABLE IF NOT EXISTS flights(
                                                id SERIAL PRIMARY KEY,
                                                flight_id TEXT,
                                                last_ticketing_date DATE,
                                                total_price NUMERIC,
                                                base_price NUMERIC,
                                                bookable_seats INTEGER,
                                                checked_bags BOOLEAN,
                                                segments JSONB,
                                                created_date DATE DEFAULT CURRENT_DATE,
                                                created_time TIME DEFAULT CURRENT_TIME)""",
                                            dag=dag)

insert_data_task = PythonOperator(
    task_id="insert_flights_to_db",
    python_callable=insert_flights_to_db,
    provide_context=True,
    dag=dag
)


fetch_flights_task >> create_table_task >> insert_data_task
