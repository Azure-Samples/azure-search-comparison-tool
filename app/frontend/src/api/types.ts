export type ApproachKey = "text" | "vec" | "hs" | "hssr";

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
    dataSet?: string;
    approach: "text" | "vec" | "hs" | "hssr" | undefined;
}

export interface SearchResponse<T extends SearchResult> {
    results: T[];
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
    category?: string;
    url?: string;
}

export interface ResultCard {
    approachKey: string;
    searchResults: TextSearchResult[];
}

export interface AxiosErrorResponseData {
    error: {
        code: string;
        message: string;
    };
}
