from neo4j import GraphDatabase

class neo4j:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self,query):
        session = self.driver.session()
        result = session.run(query)
        return result
    
