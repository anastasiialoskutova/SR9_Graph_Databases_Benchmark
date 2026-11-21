import time
import random
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password123")  # Заміни "password", якщо в docker-compose вказано інший пароль (або None, якщо без пароля)

MEMGRAPH_URI = "bolt://localhost:7688"
MEMGRAPH_AUTH = ("", "")

random.seed(42)

def generate_dataset(driver, db_name):
    random.seed(42)
    print(f"[{db_name}] Очищення та генерація датасету (520 вузлів)...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        
        # 20 категорій
        categories = [{"id": f"cat_{i}", "name": f"Category_{i}"} for i in range(1, 21)]
        session.run("UNWIND $rows AS row CREATE (:Category {id: row.id, name: row.name})", rows=categories)
        
        # 200 товарів
        products = [{"id": f"prod_{i}", "name": f"Product_{i}", "price": round(random.uniform(10, 500), 2), "cat_id": f"cat_{random.randint(1, 20)}"} for i in range(1, 201)]
        session.run("""
            UNWIND $rows AS row
            MATCH (c:Category {id: row.cat_id})
            CREATE (p:Product {id: row.id, name: row.name, price: row.price})-[:IN_CATEGORY]->(c)
        """, rows=products)
        
        # 300 користувачів
        users = [{"id": f"user_{i}", "name": f"User_{i}", "tier": random.choice(["basic", "pro", "vip"])} for i in range(1, 301)]
        session.run("UNWIND $rows AS row CREATE (:User {id: row.id, name: row.name, tier: row.tier})", rows=users)
        
        # ~900 покупок та ~600 переглядів
        purchases = [{"u": f"user_{random.randint(1, 300)}", "p": f"prod_{random.randint(1, 200)}", "amount": random.randint(1, 3)} for _ in range(900)]
        session.run("""
            UNWIND $rows AS row
            MATCH (u:User {id: row.u}), (p:Product {id: row.p})
            CREATE (u)-[:PURCHASED {amount: row.amount}]->(p)
        """, rows=purchases)
        
        views = [{"u": f"user_{random.randint(1, 300)}", "p": f"prod_{random.randint(1, 200)}"} for _ in range(600)]
        session.run("""
            UNWIND $rows AS row
            MATCH (u:User {id: row.u}), (p:Product {id: row.p})
            CREATE (u)-[:VIEWED]->(p)
        """, rows=views)
        
        count_res = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
        print(f"[{db_name}] Створено вузлів: {count_res}")

QUERIES = {
    "Q1 (Фільтрація за категорією)": """
        MATCH (u:User)-[r:PURCHASED]->(p:Product)-[:IN_CATEGORY]->(c:Category {id: 'cat_5'})
        RETURN count(r) AS total_purchases
    """,
    "Q2 (Топ-5 товарів за продажами)": """
        MATCH (:User)-[r:PURCHASED]->(p:Product)
        RETURN p.id AS product, sum(r.amount) AS sold
        ORDER BY sold DESC, product ASC LIMIT 5
    """,
    "Q3 (Колаборативні рекомендації - 2 хопи)": """
        MATCH (target:User {id: 'user_10'})-[:PURCHASED]->(p:Product)<-[:PURCHASED]-(other:User)-[:PURCHASED]->(rec:Product)
        WHERE target <> other AND NOT (target)-[:PURCHASED]->(rec)
        RETURN rec.id AS recommended, count(*) AS score
        ORDER BY score DESC, recommended ASC LIMIT 5
    """,
    "Q4 (Схожі інтереси через категорії - 4 хопи)": """
        MATCH (u1:User {id: 'user_1'})-[:PURCHASED]->(:Product)-[:IN_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(:Product)<-[:PURCHASED]-(u2:User)
        WHERE u1 <> u2
        RETURN u2.id AS similar_user, count(DISTINCT c) AS shared_categories
        ORDER BY shared_categories DESC, similar_user ASC LIMIT 5
    """,
    "Q5 (Запис нової транзакції)": """
        MATCH (u:User {id: 'user_1'}), (p:Product {id: 'prod_1'})
        CREATE (u)-[r:PURCHASED {amount: 1, tag: 'benchmark'}]->(p)
        RETURN count(r) AS created
    """
}

def run_benchmark(driver, db_name):
    results = {}
    with driver.session() as session:
        # Прогрів з'єднання
        session.run("RETURN 1").consume()
        for q_name, query in QUERIES.items():
            # Виконуємо 5 прогонів для середнього часу (окрім Q5, який змінює стан)
            runs = 1 if "Q5" in q_name else 5
            times = []
            last_records = []
            for _ in range(runs):
                t0 = time.perf_counter()
                res = session.run(query)
                last_records = [dict(r) for r in res]
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1000)  # мс
            avg_ms = sum(times) / len(times)
            results[q_name] = (round(avg_ms, 3), last_records)
    return results

if __name__ == "__main__":
    # Підключення до Neo4j (якщо пароль не підійде, спробує без автентифікації)
    try:
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        neo4j_driver.verify_connectivity()
    except Exception:
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=None)

    memgraph_driver = GraphDatabase.driver(MEMGRAPH_URI, auth=MEMGRAPH_AUTH)

    generate_dataset(neo4j_driver, "Neo4j")
    generate_dataset(memgraph_driver, "Memgraph")

    print("\nЗапуск бенчмарку запитів...")
    neo_res = run_benchmark(neo4j_driver, "Neo4j")
    mem_res = run_benchmark(memgraph_driver, "Memgraph")

    print("\n" + "="*85)
    print(f"{'Запит':<45} | {'Neo4j (мс)':<12} | {'Memgraph (мс)':<14} | {'Збіг'}")
    print("="*85)
    for q_name in QUERIES:
        n_time, n_data = neo_res[q_name]
        m_time, m_data = mem_res[q_name]
        match = "ТАК (100%)" if n_data == m_data else f"НІ ({n_data} vs {m_data})"
        print(f"{q_name:<45} | {n_time:<12} | {m_time:<14} | {match}")
    print("="*85)

    neo4j_driver.close()
    memgraph_driver.close()
