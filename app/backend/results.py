import logging
from urllib.parse import quote_plus
from postgres import Postgres

class Results:

    def __init__(self, serverName: str, userName: str, password: str):

        self.logger = logging.getLogger(__name__)
        self.serverName = serverName
        self.userName = userName
        self.password = password

    def persist_ranked_results(
            self, 
            search_query: str, 
            approach: str, 
            ndcg3: float,
            ndcg10: float,
            ideal_results: list, 
            actual_results: list):
        """
        Persist a set of search results with NDCG and associated ideal result rankings
        """

        db = self.__connect()

        result_id = self.__get_result_id(db, search_query, approach)

        if result_id is not None:
            self.logger.info(f"Deleting existing result for {search_query} / {approach}")
            self.__delete_result_(result_id)

        result_id = self.__add_result(db, search_query, approach, ndcg3, ndcg10)

        self.__add_ideal_results(db, result_id, ideal_results)
        self.__add_actual_results(db, result_id, actual_results)

    def persist_results(self, search_query: str, approach: str, actual_results: list):
        """
        Persist a set of search results without NDCG and associated ideal result rankings
        """

        db = self.__connect()

        result_id = self.__get_result_id(db, search_query, approach)

        if result_id is not None:
            self.logger.info(f"Deleting existing result for {search_query} / {approach}")
            self.__delete_result_(db, result_id)
        
        result_id = self.__add_result(db, search_query, approach, None)

        self.__add_actual_results(db, result_id, actual_results)

    def __add_result(self, db: Postgres, search_query: str, approach: str, ndcg3: float = None, ndcg10: float = None) -> str:

        query = """
        INSERT INTO public.poc_results (search_query, approach_code, ndcg_3, ndcg_10, search_time)
        VALUES(%(query)s, %(approach)s, %(ndcg3)s, %(ndcg10)s, NOW())
        RETURNING result_id;
        """ if ndcg3 != None else """
        INSERT INTO public.poc_results (search_query, approach_code, search_time)
        VALUES(%(query)s, %(approach)s, NOW())
        RETURNING result_id;
        """
        
        params = {
            "query": search_query,
            "approach": approach
        }

        if ndcg3 != None:
            params["ndcg3"] = ndcg3

        if ndcg10 != None:
            params["ndcg10"] = ndcg10

        result_id = db.one(query, params)

        self.logger.debug(result_id)

        return result_id

    def __add_ideal_results(self, db: Postgres, result_id: int, ideal_results: list):

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

            db.run(query, params)

    def __add_actual_results(self, db: Postgres, result_id: int, actual_results: list):

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

            db.run(query, params)

    def __get_result_id(self, db: Postgres, search_query: str, approach: str) -> str | None:

        query = """
        SELECT result_id
        FROM public.poc_results
        WHERE search_query = %(query)s
        AND approach_code = %(approach)s
        """
        
        params = {
            "query": search_query,
            "approach": approach
        }

        result_id = db.one(query, params)

        # self.logger.debug(f"Found result {result_id} for {search_query}/{approach}")

        return result_id
    
    def __delete_result_(self, db: Postgres, result_id: str):

        query = """
        DELETE
        FROM public.poc_results
        WHERE result_id = %(result_id)s
        """
        
        params = {
            "result_id": result_id
        }

        db.run(query, params)

    def __connect(self):
        try:
            return Postgres(f"postgresql://{self.userName}:{quote_plus(self.password)}@{self.serverName}.postgres.database.azure.com:5432/postgres?sslmode=require")

        except Exception as e:
            self.logger.error(str(e))

            raise e