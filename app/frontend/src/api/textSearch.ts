import axios from "axios";
import { SearchResponse, TextSearchRequest, TextSearchResult } from "./types";

export const getTextSearchResults = async (
    approach: "text" | "vec" | "hs" | "vecf" | "hssr" | undefined,
    searchQuery: string,
    useSemanticCaptions: boolean,
    filterText?: string,
    queryVector?: number[],
    select?: string,
    k?: number
): Promise<SearchResponse<TextSearchResult>> => {
    const requestBody: TextSearchRequest = {
        query: searchQuery,
        select: select,
        vectorSearch: false,
        hybridSearch: false
    };

    if (approach === "vec" || approach === "hs" || approach === "vecf" || approach === "hssr") {
        requestBody.vectorSearch = true;
        requestBody.k = k;
        requestBody.queryVector = queryVector;

        if (approach === "vecf") {
            requestBody.filter = filterText;
        }

        if (approach === "hs") {
            requestBody.hybridSearch = true;
        }

        if (approach === "hssr") {
            requestBody.hybridSearch = true;
            requestBody.useSemanticRanker = true;
            requestBody.useSemanticCaptions = useSemanticCaptions;
        }
    }

    const response = await axios.post<SearchResponse<TextSearchResult>>("/searchText", requestBody);

    return response.data;
};

export const getEmbeddings = async (query: string): Promise<number[]> => {
    const response = await axios.post<number[]>("/embedQuery", { query });
    return response.data;
};
