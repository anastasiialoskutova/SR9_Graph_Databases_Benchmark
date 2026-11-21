# СР 9 — графові бази даних для e-commerce

## 1. Склад тестового набору
- 100 користувачів;
- 400 товарів;
- 20 категорій;
- 1000 подій покупки;
- 520 вузлів LPG у Neo4j/Memgraph.
У GraphDB ті самі сутності подані RDF-трійками; кількість трійок не дорівнює кількості вузлів LPG.

## 2. Запуск Neo4j і Memgraph
```bash
docker compose up -d
```
Neo4j Browser: http://localhost:7474 (neo4j / password123)  
Memgraph Bolt: bolt://localhost:7688

## 3. Запуск GraphDB
Встановіть GraphDB Free або запустіть сумісний Docker-образ GraphDB.
Відкрийте Workbench на http://localhost:7200 та створіть repository з ID `ecommerce`.
У версіях GraphDB, де Free потребує окремої ліцензії, активуйте її відповідно до офіційної документації.

## 4. Python
```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\\Scripts\\activate
pip install -r requirements.txt
python benchmark.py --load --run
```

За потреби можна задати GRAPHDB_QUERY, GRAPHDB_STATEMENTS, NEO4J_URI, NEO4J_USER,
NEO4J_PASSWORD та MEMGRAPH_URI через змінні середовища.

## 5. Вихідні файли
`results/benchmark_results.csv` — час та JSON результатів кожного запиту.  
`results/benchmark_summary.csv` — компактна таблиця для звіту.

## 6. Методика
Кожен запит запускається 6 разів: перший запуск вважається прогрівальним,
а для п'яти наступних обчислюється медіана часу. У вимірювання входить час
мережевого обміну з сервером та обробки відповіді Python-клієнтом. Тому це
прикладний час відповіді, а не чистий час внутрішнього рушія БД.

## 7. Важливе зауваження щодо еквівалентності
Запити однакові за бізнес-сенсом, але використовують різні мови та моделі.
Для повної перевірки порівнюйте не лише кількість рядків, а й ідентифікатори
товарів/категорій та значення score. Різниця у сортуванні однакових score
може бути зумовлена порядком обробки; у роботі передбачене сортування за ID
як додатковий критерій детермінованості.
# SR9_Graph_Databases_Benchmark
