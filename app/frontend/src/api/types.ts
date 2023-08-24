export type ApproachKey = "text" | "vec" | "vecf" | "hs" | "hssr";

export interface Approach {
    key: ApproachKey;
    title: string;
}

export interface TextSearchRequest {
    query: string;
    vectorSearch?: boolean;
    hybridSearch?: boolean;
    select?: string;
    k?: number;
    filter?: string;
    useSemanticRanker?: boolean;
    useSemanticCaptions?: boolean;
    queryVector?: number[];
}

export interface ImageSearchRequest {
    query: string;
}

export interface SearchResponse<T extends SearchResult> {
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

export interface ResultCard {
    approachKey: string;
    searchResults: TextSearchResult[];
    semanticAnswer: SemanticAnswer | null;
}

export interface AxiosErrorResponseData {
    error: {
        code: string;
        message: string;
    };
}
