import sqlite3
import pandas as pd
from json import loads
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime


def create_db_table_from_csv(csv_file_path):
    conn = sqlite3.connect('clients.db')
    c = conn.cursor()

    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            registration_address TEXT,
            last_known_location TEXT,
            suspicious BOOLEAN DEFAULT FALSE
        )
    ''')

    # Load data from CSV file
    df_clients = pd.read_csv(csv_file_path)

    # Insert data into the table
    df_clients.to_sql('clients', conn, if_exists='replace', index=False)

    conn.commit()
    conn.close()


def is_suspicious(timestamp, amount, location, known_locations):
    # Check if transaction occurs at night
    time_of_day = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").time()
    if time_of_day.hour >= 23 or time_of_day.hour <= 5:
        return True

    # Check if amount exceeds threshold
    if amount > 1000:
        return True

    # Check if location differs from known locations
    if location not in known_locations:
        return True

    return False


def consume_and_process():
    consumer = KafkaConsumer(
        'bank_transactions',
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='my-group',
        value_deserializer=lambda x: loads(x.decode('utf-8')),
    )

    conn = sqlite3.connect('clients.db')
    c = conn.cursor()

    for message in consumer:
        transaction = message.value
        user_id = transaction['user_id']
        amount = transaction['amount']
        timestamp = transaction['timestamp']
        location = transaction['location']

        print(f"Received transaction: {transaction}")

        # Check if user exists in database
        c.execute("SELECT * FROM clients WHERE user_id=?", (user_id,))
        client = c.fetchone()

        if client:
            print(f"Client found: {client[1]} ({client[0]})")

            known_locations = [client[2], client[3]]

            # Determine if transaction is suspicious
            if is_suspicious(timestamp, amount, location, known_locations):
                print(f"Transaction is suspicious: {transaction}")
                c.execute("UPDATE clients SET suspicious=? WHERE user_id=?", (True, user_id))
                conn.commit()

                # Send to new topic with suspicious activity
                producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
                producer.send('suspicious_activity', key=b'suspicious', value=bytes(transaction))
                producer.flush()
        else:
            print(f"No client found for user_id {user_id}. Skipping.")


if __name__ == "__main__":
    csv_file_path = 'data/clients.csv'
    create_db_table_from_csv(csv_file_path)
    consume_and_process()
