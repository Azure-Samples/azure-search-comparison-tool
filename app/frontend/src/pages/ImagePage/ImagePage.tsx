import React, { useState, useCallback } from "react";
import { Spinner, Stack, TextField } from "@fluentui/react";
import { DismissCircle24Filled, Search24Regular } from "@fluentui/react-icons";

import styles from "./ImagePage.module.css";

import { getImageSearchResults } from "../../api/imageSearch";
import { ImageSearchResult } from "../../api/types";

export const ImagePage = () => {
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [searchResults, setSearchResults] = useState<ImageSearchResult[]>([]);

    const handleOnKeyDown = useCallback(
        async (e: React.KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (searchQuery.length === 0) {
                    setSearchResults([]);
                    return;
                }

                setLoading(true);
                const results = await getImageSearchResults(searchQuery);
                setSearchResults(results.results);
                setLoading(false);
            }
        },
        [searchQuery]
    );

    const handleOnChange = useCallback((_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setSearchQuery(newValue ?? "");
    }, []);

    return (
        <div className={styles.vectorContainer}>
            <Stack horizontal className={styles.questionInputContainer}>
                <Search24Regular />
                <TextField
                    className={styles.questionInputTextArea}
                    resizable={false}
                    borderless
                    value={searchQuery}
                    placeholder="Type something here (e.g. fancy shoes)"
                    onChange={handleOnChange}
                    onKeyDown={handleOnKeyDown}
                />
                {searchQuery.length > 0 && <DismissCircle24Filled onClick={() => setSearchQuery("")} />}
            </Stack>
            <div className={styles.spinner}>{loading && <Spinner label="Getting results" />}</div>
            <div className={styles.searchResultsContainer}>
                {searchResults.map(x => (
                    <Stack key={x.id} className={styles.imageSearchResultCard}>
                        <div className={styles.imageContainer}>
                            <img src={x.imageUrl} alt={x.title} />
                        </div>
                    </Stack>
                ))}
            </div>
        </div>
    );
};
