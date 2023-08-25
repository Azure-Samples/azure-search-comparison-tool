import axios from "axios";

export const getEfSearch = async (): Promise<string> => {
    const response = await axios.get<string>("/getEfSearch");
    return response.data;
};

export const updateEfSearch = async (efSearch: string): Promise<string> => {
    const response = await axios.post<string>("/updateEfSearch", { efSearch });
    return response.data;
};
