CREATE TABLE IF NOT EXISTS public.poc_results
(
    result_id integer GENERATED ALWAYS AS IDENTITY,
    search_query character varying(256) COLLATE pg_catalog."default" NOT NULL,
    approach_code character varying(64) COLLATE pg_catalog."default" NOT NULL,
    ndcg numeric(21,20),
    search_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT poc_results_pkey PRIMARY KEY (result_id)
)

TABLESPACE pg_default;

ALTER TABLE public.poc_results
    OWNER to resultsadmin;

CREATE TABLE IF NOT EXISTS public.poc_actual_result_rankings
(
    actual_result_ranking_id integer GENERATED ALWAYS AS IDENTITY,
    result_id integer NOT NULL,
    rank integer NOT NULL,
    article_id character varying(128) COLLATE pg_catalog."default" NOT NULL,
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
    article_id character varying(128) COLLATE pg_catalog."default" NOT NULL,
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

CREATE OR REPLACE VIEW public.poc_ndcg_rankings
AS
SELECT DISTINCT lower(search_query) as search_query, approach_code, ndcg
FROM public.poc_results
WHERE ndcg IS NOT NULL
ORDER BY lower(search_query), ndcg DESC, approach_code;

ALTER TABLE public.poc_ndcg_rankings
    OWNER TO resultsadmin;


CREATE OR REPLACE VIEW public.poc_ranked_results
AS
SELECT
    R.result_id,
    R.search_query,
    R.approach_code,
    R.ndcg,
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

CREATE OR REPLACE FUNCTION public.poc_compare_search_query_results(search_query TEXT)
RETURNS TABLE(
    rank INT,
    vec_article_id TEXT,
    vec_relevance NUMERIC(6, 3),
    text_article_id TEXT,
    text_relevance NUMERIC(6, 3),
    algolia_article_id TEXT,
    algolia_relevance NUMERIC(6, 3)
)
AS $$
    WITH vec_result AS (
        SELECT R.result_id
        FROM public.poc_results R
        WHERE lower(R.search_query) = lower($1) AND R.approach_code = 'vec'
        ORDER BY R.search_time DESC
        LIMIT 1),
    text_result AS (
        SELECT R.result_id
        FROM public.poc_results R
        WHERE lower(R.search_query) = lower($1) AND R.approach_code = 'text'
        ORDER BY R.search_time DESC
        LIMIT 1),
    algolia_result AS (
        SELECT R.result_id
        FROM public.poc_results R
        WHERE lower(R.search_query) = lower($1) AND R.approach_code = 'algolia'
        ORDER BY R.search_time DESC
        LIMIT 1)
    SELECT 
        VEC_ARR.rank,
        VEC_ARR.article_id as vec_article_id,
        CAST(VEC_ARR.relevance_score AS NUMERIC(6, 3)) AS vec_relevance,
        TEXT_ARR.article_id as text_article_id,
        CAST(TEXT_ARR.relevance_score AS NUMERIC(6, 3)) as text_relevance,
        ALG_ARR.article_id as algolia_article_id,
        CAST(ALG_ARR.relevance_score AS NUMERIC(6, 3)) as algolia_relevance
    FROM
        public.poc_actual_result_rankings VEC_ARR,
        vec_result VEC_R,
        public.poc_actual_result_rankings TEXT_ARR,
        text_result TEXT_R,
        public.poc_actual_result_rankings ALG_ARR,
        algolia_result ALG_R
    WHERE VEC_ARR.result_id = VEC_R.result_id
    AND TEXT_ARR.result_id = TEXT_R.result_id
    AND ALG_ARR.result_id = ALG_R.result_id
    AND VEC_ARR.rank = TEXT_ARR.rank
    AND VEC_ARR.rank = ALG_ARR.rank
    ORDER BY VEC_ARR.rank;
$$
LANGUAGE SQL;

ALTER FUNCTION public.poc_compare_search_query_results(search_query text)
    OWNER TO resultsadmin;