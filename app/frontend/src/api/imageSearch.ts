import axios from "axios";
import { ImageSearchRequest, ImageSearchResult, SearchResponse } from "./types";

export const getImageSearchResults = async (query: string, dataType: string): Promise<SearchResponse<ImageSearchResult>> => {
    const requestBody: ImageSearchRequest = {
        query,
        dataType
    };
    const response = await axios.post<SearchResponse<ImageSearchResult>>("/searchImages", requestBody);
    return response.data;
};
