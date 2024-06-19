export interface Approach {
    key: string;
    title: string;
    data_set?: string;
    use_vector_search?: boolean;
}

export interface TextSearchRequest {
    query: string;
    k?: number;
    useSemanticCaptions?: boolean;
    queryVector?: number[];
    dataSet?: string;
    approach: string;
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
    content: string;
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
