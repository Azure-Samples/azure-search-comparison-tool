import logging
from urllib.parse import quote_plus
from postgres import Postgres

class Results:

    def __init__(self, serverName: str, userName: str, password: str):

        self.logger = logging.getLogger(__name__)
        self.serverName = serverName
        self.userName = userName
        self.password = password

    def add(self, search_query: str, approach: str, ndcg):

        db = self.__connect()

        # Define your SQL query with named parameters
        query = """
        INSERT INTO public.poc_results (search_query, approach_code, ndcg, search_time)
        VALUES(%(q)s, %(a)s, %(ndcg)s, NOW())
        RETURNING result_id;
        """
        
        # Define the parameters to bind
        params = {
            "q": search_query,
            "a": approach,
            "ndcg": ndcg
        }

        result_id = db.one(query, params)

        self.logger.debug(result_id)

    def __connect(self):
        try:
            return Postgres(f"postgresql://{self.userName}:{quote_plus(self.password)}@{self.serverName}.postgres.database.azure.com:5432/postgres?sslmode=require")

        except Exception as e:
            self.logger.error(str(e))

        return None