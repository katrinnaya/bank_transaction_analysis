import random
from datetime import datetime, timedelta
from time import sleep
from json import dumps
from kafka import KafkaProducer

def generate_transactions(num_transactions):
    producer = KafkaProducer(bootstrap_servers=['localhost:9094'], value_serializer=lambda x: dumps(x).encode('utf-8'))

    locations = ["New York", "Los Angeles", "Chicago", "Boston"]
    
    for _ in range(num_transactions):
        transaction_id = random.randint(1000, 9999)
        user_id = random.randint(100, 199)
        amount = round(random.uniform(500, 1500), 2)
        current_time = datetime.utcnow()
        location = random.choice(locations)

        transaction = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": amount,
            "timestamp": current_time.isoformat(),
            "location": location
        }

        print(f"Sending transaction: {transaction}")
        producer.send("bank_transactions", value=transaction)
        sleep(1)  # Имитация реальной задержки между транзакциями

    producer.flush()  # Обеспечиваем отправку всех сообщений до завершения программы

if __name__ == "__main__":
    num_transactions = 10  # Замените на нужное количество транзакций
    generate_transactions(num_transactions)
