CREATE TABLE IF NOT EXISTS public.poc_results
(
    result_id integer GENERATED ALWAYS AS IDENTITY,
    search_query character varying(256) COLLATE pg_catalog."default" NOT NULL,
    approach_code character varying(64) COLLATE pg_catalog."default" NOT NULL,
    ndcg numeric(21,20),
    search_time timestamp,
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


