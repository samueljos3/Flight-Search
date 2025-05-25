from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
from airflow.exceptions import AirflowException

# DEFINE VARIABLES
exit_location = Variable.get("exit_location")
arrival_location = Variable.get("arrival_location")
departure_date = Variable.get("departure_date")

# DEFINE DAG
dag = DAG("daily_flight_report", 
          "Dag to generate daily flight report",
          schedule_interval="@daily",
          start_date=datetime(2025, 1, 1),
          catchup=False,
            #default_args={
                #'retries': 1,
                #'retry_delay': timedelta(minutes=5)
            #}
            )

#FUNCTION TO SELECT FLIGHTS FROM THE DATABASE
def select_flights_from_db(**kwargs):
    pg_hook = PostgresHook(postgres_conn_id="postgres")
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT AVG(total_price) AS avg_price,
                MIN(total_price) AS min_price,
                MAX(total_price) AS max_price
                FROM flights
                WHERE exit_location = %s
                AND arrival_location = %s
                AND departure_date = %s
                GROUP BY exit_location, arrival_location, departure_date
                """, (exit_location, arrival_location, departure_date))   
    daily_flights = cursor.fetchone()
    
    cursor.execute("""
        SELECT segments, total_price, last_ticketing_date, bookable_seats, checked_bags
        FROM flights
        WHERE exit_location = %s
        AND arrival_location = %s
        AND departure_date = %s
        ORDER BY total_price ASC
        LIMIT 1
        """, (exit_location, arrival_location, departure_date))
    segment_cheapest_daily_flight = cursor.fetchone()
                   
    cursor.execute("""
        select min(total_price) as min_price,
                max(total_price) as max_price,
                avg(total_price) as avg_price
                from flights
                where exit_location = %s
                and arrival_location = %s
                """, (exit_location, arrival_location))
    historical_flights = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "daily_flights": daily_flights,
        "historical_flights": historical_flights,
        "segment_cheapest_daily_flight": segment_cheapest_daily_flight
    }


# FUNCTION TO PRINT FLIGHT REPORT
def print_flight_report(**kwargs):
    flights = kwargs['ti'].xcom_pull(task_ids='select_flights_from_db')
    
    daily_flights = flights.get("daily_flights", [])
    historical_flights = flights.get("historical_flights", [])
    segment_cheapest_daily_flight = flights.get("segment_cheapest_daily_flight", [])
    
    if not daily_flights or not historical_flights or not segment_cheapest_daily_flight:
        raise AirflowException("No flight data found for the specified criteria.")
    
    print(f"Daily Flight Report: *{departure_date}* -> {exit_location} to {arrival_location}")
    print(f"""média diária: {daily_flights[0]},
            mínimo diário: {daily_flights[1]},
            máximo diário: {daily_flights[2]}\n""")   
      
    print(f"Historical Flight Data: {exit_location} to {arrival_location}")
    print(f"""mínimo histórico: {historical_flights[0]},
            máximo histórico: {historical_flights[1]},
            média histórica: {historical_flights[2]}\n""")

    print(f"Cheapest Daily Flight Segment: {exit_location} to {arrival_location}")
    print(f"""segmento: {segment_cheapest_daily_flight[0]},
            preço total: {segment_cheapest_daily_flight[1]},
            última data de emissão: {segment_cheapest_daily_flight[2]},
            assentos disponíveis: {segment_cheapest_daily_flight[3]},
            bagagens despachadas: {segment_cheapest_daily_flight[4]}""")


# DEFINE TASKS
select_flights_task = PythonOperator(
    task_id='select_flights_from_db',
    python_callable=select_flights_from_db,
    provide_context=True,
    dag=dag
)

print_report_task = PythonOperator(
    task_id='print_flight_report',
    python_callable=print_flight_report,
    provide_context=True,
    dag=dag
)

select_flights_task >> print_report_task