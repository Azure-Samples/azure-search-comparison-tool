import axios from "axios";
import { Approach, SearchResponse, TextSearchRequest, TextSearchResult } from "./types";

export const getTextSearchResults = async (
    approach: Approach,
    searchQuery: string,
    useSemanticRanker: boolean,
    useSemanticCaptions: boolean,
    filterText: string
): Promise<SearchResponse<TextSearchResult>> => {
    const requestBody: TextSearchRequest = {
        approach: approach,
        query: searchQuery,
        useSemanticRanker: useSemanticRanker,
        useSemanticCaptions: useSemanticCaptions,
        overrides: {
            filter: filterText
        }
    };

    const response = await axios.post<SearchResponse<TextSearchResult>>("/searchText", requestBody);

    return response.data;
};
