import axios from "axios";
import { ImageSearchRequest, ImageSearchResult, SearchResponse } from "./types";

export const getImageSearchResults = async (query: string): Promise<SearchResponse<ImageSearchResult>> => {
    const requestBody: ImageSearchRequest = {
        query: query
    };
    const response = await axios.post<SearchResponse<ImageSearchResult>>("/searchImages", requestBody);
    return response.data;
};
