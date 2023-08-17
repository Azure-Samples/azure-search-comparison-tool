export enum Approach {
    Vector = "vec",
    VectorFilter = "vecf",
    Hybrid = "hs"
}

export interface TextSearchRequest {
    approach: Approach;
    query: string;
    useSemanticRanker?: boolean;
    useSemanticCaptions?: boolean;
    overrides?: {
        vectorFields?: string;
        k?: number;
        filter?: string;
        select?: string;
    };
}

export interface ImageSearchRequest {
    query: string;
}

export interface SearchResponse<T extends SearchResult> {
    queryVector: number[];
    semanticAnswers: SemanticAnswer[] | null;
    results: T[];
}

export interface SemanticAnswer {
    key: string;
    text: string;
    highlights: string;
    score: number;
}

interface SearchResult {
    "@search.score": number;
    "@search.reranker_score"?: number;
    "@search.captions"?: SearchCaptions[];
}

interface SearchCaptions {
    text: string;
    highlights: string;
}

export interface TextSearchResult extends SearchResult {
    id: string;
    title: string;
    titleVector: number[];
    content: string;
    contentVector: number[];
    category: string;
}

export interface ImageSearchResult extends SearchResult {
    id: string;
    title: string;
    imageUrl: string;
}
