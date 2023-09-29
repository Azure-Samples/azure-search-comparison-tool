import React, { useState, useCallback, useMemo } from "react";
import { Spinner, Stack, TextField, Text, MessageBar, MessageBarType } from "@fluentui/react";
import { DismissCircle24Filled, ImageAdd24Regular, ImageSearch24Regular } from "@fluentui/react-icons";

import styles from "./ImagePage.module.css";

import { getImageSearchResults } from "../../api/imageSearch";
import { ImageSearchResult } from "../../api/types";

export const ImagePage = () => {
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [searchResults, setSearchResults] = useState<ImageSearchResult[]>([]);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = React.useState<string>("");

    const onTextSearch = useCallback(async (searchQuery: string) => {
        setSearchResults([]);
        setErrorMessage("");
        setSelectedImage("");

        setLoading(true);
        const results = await getImageSearchResults(searchQuery, "text");

        setSearchResults(results.results);
        setLoading(false);
    }, []);

    const onImageUrl = useCallback(async (query: string, dataType: string) => {
        setSearchResults([]);
        setErrorMessage("");

        setSelectedImage(query);
        setLoading(true);
        try {
            const results = await getImageSearchResults(query, dataType);
            setSearchResults(results.results);
        } catch (e) {
            setErrorMessage(
                `Failed to fetch results. Details: ${String(e)}. Only publicly reachable URL of an image is supported. Please double check the image URL.`
            );
        }
        setLoading(false);
    }, []);

    const isValidFileType = useCallback((type: string) => {
        if (type.split("/")[0] === "image") {
            return true;
        }
        return false;
    }, []);

    const isValidHttpUrl = useCallback((s: string) => {
        let url;
        try {
            url = new URL(s);
        } catch {
            return false;
        }
        return url.protocol === "http:" || url.protocol === "https:";
    }, []);

    const handleOnKeyDown = useCallback(
        (e: React.KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (searchQuery.length === 0) {
                    setSearchResults([]);
                    setErrorMessage("");
                    return;
                }

                if (isValidHttpUrl(searchQuery)) {
                    void onImageUrl(searchQuery, "imageUrl");
                } else {
                    void onTextSearch(searchQuery);
                }
            }
        },
        [isValidHttpUrl, onImageUrl, onTextSearch, searchQuery]
    );

    const handleOnChange = useCallback((_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setSearchQuery(newValue ?? "");
    }, []);

    const reader = useMemo(() => new FileReader(), []);

    const onFileSelected = useCallback(
        (file: File) => {
            reader.onload = async () => {
                const imageData = String(reader.result);
                setSelectedImage(imageData);
                setLoading(true);
                const results = await getImageSearchResults(imageData, "imageFile");
                setSearchResults(results.results);
                setLoading(false);
            };
            reader.readAsDataURL(file);
        },
        [reader]
    );

    const handleFile = (item: File) => {
        setSearchResults([]);
        setErrorMessage("");
        setSelectedImage("");
        setSearchQuery("");
        if (isValidFileType(item.type)) {
            onFileSelected(item);
        } else {
            setErrorMessage("The file type is not supported.");
        }
    };

    const onDrop: React.DragEventHandler = e => {
        e.preventDefault();
        const item = e.dataTransfer?.files?.[0];
        item && handleFile(item);
    };

    const onDragOver: React.DragEventHandler = e => {
        e.preventDefault();
        e.stopPropagation();
    };

    const onPaste: React.ClipboardEventHandler = e => {
        e.preventDefault();
        setSearchResults([]);
        setErrorMessage("");
        setSelectedImage("");
        setSearchQuery("");
        const item = e.clipboardData?.items?.[0];
        if (item && item.kind === "file") {
            const f = item.getAsFile();
            f && handleFile(f);
        } else if (item && item.kind === "string") {
            if (item.type === "text/html") {
                item.getAsString(htmlString => {
                    const tempContainer = document.createElement("div");
                    tempContainer.innerHTML = htmlString;
                    const imgElements = tempContainer.getElementsByTagName("img");
                    void onImageUrl(imgElements[0].src, "imageUrl");
                    tempContainer.remove();
                });
            } else if (item.type === "text/plain") {
                item.getAsString(urlString => {
                    setSearchQuery(urlString || "");
                    if (isValidHttpUrl(urlString)) {
                        void onImageUrl(urlString, "imageUrl");
                    } else {
                        void onTextSearch(urlString);
                    }
                });
            }
        }
    };

    const onFileInput: React.ChangeEventHandler<HTMLInputElement> = e => {
        e.preventDefault();
        const item = e.target.files?.[0];
        item && handleFile(item);
    };

    return (
        <div className={styles.vectorContainer}>
            {
                <Stack horizontal horizontalAlign="center" tokens={{ childrenGap: 50 }}>
                    <div className={styles.dropZone}>
                        <Stack horizontal horizontalAlign="center" className={styles.dropZoneContent}>
                            <Stack
                                className={styles.imageInput}
                                tokens={{ childrenGap: 10 }}
                                verticalAlign="center"
                                horizontalAlign="center"
                                onDragOver={onDragOver}
                                onDrop={onDrop}
                            >
                                <Stack horizontal className={styles.questionInputContainer} horizontalAlign="center">
                                    <ImageSearch24Regular />
                                    <TextField
                                        className={styles.questionInputTextArea}
                                        resizable={false}
                                        borderless
                                        onPaste={onPaste}
                                        value={searchQuery}
                                        placeholder="Type something here (e.g. fancy shoes) or paste image or URL here"
                                        onChange={handleOnChange}
                                        onKeyDown={handleOnKeyDown}
                                    />
                                    {searchQuery.length > 0 && <DismissCircle24Filled onClick={() => setSearchQuery("")} />}
                                </Stack>
                                <label htmlFor="file-upload" className={styles.uploadContainer}>
                                    <Stack>
                                        <Text>------OR------</Text>
                                        <input className={styles.fileInput} type="file" id="file-upload" onChange={onFileInput} />
                                        <ImageAdd24Regular className={styles.uploadButton} />
                                        <Text variant="large" className={styles.text}>
                                            {"Click to upload or drag an image here"}
                                        </Text>
                                    </Stack>
                                </label>
                            </Stack>
                        </Stack>
                    </div>

                    {!errorMessage && selectedImage && (
                        <div className={styles.selectedImageContainer}>
                            <img src={selectedImage} alt="Selected" className={styles.selectedImage} />
                        </div>
                    )}
                </Stack>
            }

            <div className={styles.spinner}>{loading && <Spinner label="Getting results" />}</div>
            {errorMessage && <MessageBar messageBarType={MessageBarType.error}>{errorMessage}</MessageBar>}
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
