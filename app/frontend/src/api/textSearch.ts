import axios from "axios";
import { Approach, SearchResponse, TextSearchRequest, TextSearchResult } from "./types";

export const getTextSearchResults = async (
    approach: Approach,
    searchQuery: string,
    useSemanticCaptions: boolean,
    dataSet?: string,
    queryVector?: number[],
    k?: number
): Promise<SearchResponse<TextSearchResult>> => {
    const requestBody: TextSearchRequest = {
        query: searchQuery,
        dataSet: dataSet,
        approach: approach.key
    };

    if (approach.use_vector_search ?? false) {
        requestBody.k = k;
        requestBody.queryVector = queryVector;

        if (approach.key === "hssr") {
            requestBody.useSemanticCaptions = useSemanticCaptions;
        }
    }

    const response = await axios.post<SearchResponse<TextSearchResult>>("/searchText", requestBody);

    return response.data;
};

export const getEmbeddings = async (query: string, approach: string): Promise<number[]> => {
    const response = await axios.post<number[]>("/embedQuery", { query, approach });
    return response.data;
};
