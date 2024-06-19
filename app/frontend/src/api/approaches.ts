import axios from "axios";
import { Approach } from "./types";

export const getApproaches = async (): Promise<Approach[]> => {
    const response = await axios.get<Approach[]>("/approaches");
    return response.data;
};
