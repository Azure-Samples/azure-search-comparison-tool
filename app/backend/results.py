import logging
from urllib.parse import quote_plus
from postgres import Postgres

class Results:

    def __init__(self, serverName: str, userName: str, password: str):

        self.logger = logging.getLogger(__name__)
        self.serverName = serverName
        self.userName = userName
        self.password = password

    def add(self, search_query: str, approach: str, ndcg, ideal_results, actual_results):

        db = self.__connect()

        query = """
        INSERT INTO public.poc_results (search_query, approach_code, ndcg, search_time)
        VALUES(%(query)s, %(approach)s, %(ndcg)s, NOW())
        RETURNING result_id;
        """
        
        params = {
            "query": search_query,
            "approach": approach,
            "ndcg": ndcg
        }

        result_id = db.one(query, params)

        self.logger.debug(result_id)

        query = """
        INSERT INTO public.poc_ideal_result_rankings (result_id, rank, article_id, relevance_score)
        VALUES(%(r_id)s, %(rank)s, %(article)s, %(relevance)s);
        """
        
        for rank, ideal_result in enumerate(ideal_results):
            
            params = {
                "r_id": result_id,
                "rank": rank,
                "article": ideal_result["id"],
                "relevance": ideal_result["relevance"]
            }

            db.one(query, params)

        query = """
        INSERT INTO public.poc_actual_result_rankings (result_id, rank, article_id, relevance_score, azure_ai_score)
        VALUES(%(r_id)s, %(rank)s, %(article)s, %(relevance)s, %(score)s);
        """

        for rank, actual_result in enumerate(actual_results):
            
            params = {
                "r_id": result_id,
                "rank": rank,
                "article": actual_result["id"],
                "relevance": actual_result["relevance"],
                "score": actual_result["score"]
            }

            db.one(query, params)

    def __connect(self):
        try:
            return Postgres(f"postgresql://{self.userName}:{quote_plus(self.password)}@{self.serverName}.postgres.database.azure.com:5432/postgres?sslmode=require")

        except Exception as e:
            self.logger.error(str(e))

        return None