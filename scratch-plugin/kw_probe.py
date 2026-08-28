from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
with driver.session() as s:
    # variant A: simple contains
    rA = s.run("""
        MATCH (n:Embeddable)
        WHERE n.name IS NOT NULL AND toLower(n.name) CONTAINS $q
        RETURN n.name AS name, n.qualified_name AS qname LIMIT 5
    """, q="vector")
    print("variant A:", [dict(x) for x in rA])
    # variant B: any list
    rB = s.run("""
        MATCH (n:Embeddable)
        WHERE any(h IN [n.name, n.qualified_name, n.docstring]
                  WHERE h IS NOT NULL AND toLower(h) CONTAINS $q)
        RETURN n.name AS name LIMIT 5
    """, q="vector_store")
    print("variant B:", [dict(x) for x in rB])
    # check whether CodeFile nodes have name set
    rC = s.run("MATCH (n:CodeFile) RETURN n.name AS name, n.relative_path AS rel LIMIT 3")
    print("CodeFile names:", [dict(x) for x in rC])
driver.close()
