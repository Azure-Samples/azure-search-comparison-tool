CREATE TABLE IF NOT EXISTS public.poc_results
(
    result_id integer GENERATED ALWAYS AS IDENTITY,
    search_query character varying(256) COLLATE pg_catalog."default" NOT NULL,
    approach_code character varying(64) COLLATE pg_catalog."default" NOT NULL,
    ndcg_3 numeric(21,20),
    ndcg_10 numeric(21,20),
    search_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT poc_results_pkey PRIMARY KEY (result_id),
    UNIQUE (search_query, approach_code)
)

TABLESPACE pg_default;

ALTER TABLE public.poc_results
    OWNER to resultsadmin;

CREATE TABLE IF NOT EXISTS public.poc_actual_result_rankings
(
    actual_result_ranking_id integer GENERATED ALWAYS AS IDENTITY,
    result_id integer NOT NULL,
    rank integer NOT NULL,
    article_id character varying(256) COLLATE pg_catalog."default" NOT NULL,
    relevance_score numeric(60,30),
    azure_ai_score numeric(60,30),
    CONSTRAINT poc_actual_result_rankings_pkey PRIMARY KEY (actual_result_ranking_id),
    CONSTRAINT poc_actual_result_rankings_fk_result_id FOREIGN KEY (result_id)
        REFERENCES public.poc_results (result_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE public.poc_actual_result_rankings
    OWNER to resultsadmin;

CREATE TABLE IF NOT EXISTS public.poc_ideal_result_rankings
(
    ideal_result_ranking_id integer GENERATED ALWAYS AS IDENTITY,
    result_id integer NOT NULL,
    rank integer NOT NULL,
    article_id character varying(256) COLLATE pg_catalog."default" NOT NULL,
    relevance_score numeric(60,30),
    CONSTRAINT poc_ideal_result_rankings_pkey PRIMARY KEY (ideal_result_ranking_id),
    CONSTRAINT poc_ideal_result_rankings_fk_result_id FOREIGN KEY (result_id)
        REFERENCES public.poc_results (result_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE public.poc_ideal_result_rankings
    OWNER to resultsadmin;

CREATE OR REPLACE VIEW public.poc_ndcg_rankings_3
AS
SELECT DISTINCT lower(search_query) as search_query, approach_code, ndcg_3
FROM public.poc_results
WHERE ndcg_3 IS NOT NULL
ORDER BY lower(search_query), ndcg_3 DESC, approach_code;

ALTER TABLE public.poc_ndcg_rankings_3
    OWNER TO resultsadmin;


CREATE OR REPLACE VIEW public.poc_ranked_results
AS
SELECT
    R.result_id,
    R.search_query,
    R.approach_code,
    R.ndcg_3,
    R.ndcg_10,
    ARR.rank,
    ARR.article_id,
    CAST(ARR.relevance_score AS NUMERIC(6, 3)) as relevance,
    ARR.azure_ai_score,
    IRR.article_id as expected_article_id,
    CAST(IRR.relevance_score AS NUMERIC(6, 3)) as expected_relevance
FROM public.poc_results R
    JOIN public.poc_actual_result_rankings ARR ON R.result_id = ARR.result_id
    LEFT JOIN public.poc_ideal_result_rankings IRR ON R.result_id = IRR.result_id AND IRR.rank = ARR.rank
ORDER BY R.result_id DESC, ARR.rank;

ALTER TABLE public.poc_ranked_results
    OWNER TO resultsadmin;

CREATE OR REPLACE FUNCTION public.poc_compare_search_query_results(search_query TEXT, approach_code_1 TEXT, approach_code_2 TEXT)
RETURNS TABLE(
    rank_1 INT,
    article_id_1 TEXT,
    relevance_1 NUMERIC(6, 3),
    rank_2 INT,
    article_id_2 TEXT,
    relevance_2 NUMERIC(6, 3)
)
AS $$
    WITH result_1 AS (
        SELECT ARR.rank, ARR.article_id, ARR.relevance_score
        FROM public.poc_results R
        JOIN public.poc_actual_result_rankings ARR ON R.result_id = ARR.result_id
        WHERE lower(R.search_query) = lower($1) AND R.approach_code = $2),
    result_2 AS (
        SELECT ARR.rank, ARR.article_id, ARR.relevance_score
        FROM public.poc_results R
        JOIN public.poc_actual_result_rankings ARR ON R.result_id = ARR.result_id
        WHERE lower(R.search_query) = lower($1) AND R.approach_code = $3)
    SELECT 
        R_1.rank,
        R_1.article_id as article_id_1,
        CAST(R_1.relevance_score AS NUMERIC(6, 3)) AS relevance_1,
        R_2.rank,
        R_2.article_id as article_id_2,
        CAST(R_2.relevance_score AS NUMERIC(6, 3)) as relevance_2
    FROM result_1 R_1
    FULL JOIN result_2 R_2 ON R_1.rank = R_2.rank
    ORDER BY R_1.rank, R_2.rank;
$$
LANGUAGE SQL;

ALTER FUNCTION public.poc_compare_search_query_results(search_query TEXT, approach_code_1 TEXT, approach_code_2 TEXT)
    OWNER TO resultsadmin;

CREATE OR REPLACE FUNCTION public.poc_combined_rrf(search_query TEXT)
RETURNS TABLE(
    article_id_1 TEXT,
    rrf_score NUMERIC(6, 5)
)
AS $$
    WITH reciprocal_ranks AS (
        SELECT
            ARR.article_id,
            R.approach_code,
            ARR.rank + 1 as rank,
            1.0 / (ARR.rank + 1 + 60) AS reciprocal_rank
        FROM
            public.poc_actual_result_rankings ARR
        JOIN
            public.poc_results R ON ARR.result_id = R.result_id AND lower(R.search_query) = lower($1)
        WHERE R.approach_code IN ('hs_large', 'hssr_large', 'hssr_large_kw', 'hssr_large_kw_title_weighted')
        ),
    aggregated_ranks AS (
        SELECT
            article_id,
            SUM(reciprocal_rank) AS rrf_score
        FROM
            reciprocal_ranks
        GROUP BY
            article_id
    )
    SELECT
        article_id,
        rrf_score
    FROM
        aggregated_ranks
    WHERE rrf_score > 0.025
    ORDER BY
        rrf_score DESC;
$$
LANGUAGE SQL;

ALTER FUNCTION public.poc_combined_rrf(search_query TEXT)
    OWNER TO resultsadmin;