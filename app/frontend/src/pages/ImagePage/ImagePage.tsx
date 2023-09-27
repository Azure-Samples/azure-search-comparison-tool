import React, { useState, useCallback } from "react";
import { Spinner, Stack, TextField, Text, IIconProps, CommandButton } from "@fluentui/react";
import { DismissCircle24Filled, Image28Regular, ImageAdd24Regular, Search24Regular } from "@fluentui/react-icons";

import styles from "./ImagePage.module.css";

import { getImageSearchResults } from "../../api/imageSearch";
import { ImageSearchResult } from "../../api/types";

// const IMAGE_FILE_TYPE = "image/png";

export const ImagePage = () => {
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [searchResults, setSearchResults] = useState<ImageSearchResult[]>([]);
    const [isImageSearch, setIsImageSearch] = React.useState(false);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);
    // const [isDraggedOver, setIsDraggedOver] = React.useState(false);
    // const [fileFormatError, setFileFormatError] = React.useState(false);

    const handleOnKeyDown = useCallback(
        async (e: React.KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (searchQuery.length === 0) {
                    setSearchResults([]);
                    return;
                }

                setLoading(true);
                const results = await getImageSearchResults(searchQuery, "text");

                setSearchResults(results.results);
                setLoading(false);
            }
        },
        [searchQuery]
    );

    const handleOnChange = useCallback((_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setSearchQuery(newValue ?? "");
    }, []);

    const reader = new FileReader();

    const onFileSelected = (file: File) => {
        reader.onload = async () => {
            const imageData = reader.result as string;
            setSelectedImage(imageData);
            setLoading(true);
            const results = await getImageSearchResults(imageData, "imageFile");
            setSearchResults(results.results);
            setLoading(false);
        };
        reader.readAsDataURL(file);
    };

    const onImageUrlPasted = async (query: string, dataType: string) => {
        setSelectedImage(query);
        setLoading(true);
        const results = await getImageSearchResults(query, dataType);
        setSearchResults(results.results);
        setLoading(false);
    };
    const cancelIcon: IIconProps = { iconName: "Cancel" };

    const onDrop: React.DragEventHandler = e => {
        e.preventDefault();
        setSearchResults([]);

        console.log("ett", e);
        const item = e.dataTransfer?.files?.[0];
        if (item && item.type.startsWith("image")) {
            // setIsDraggedOver(false);
            onFileSelected(item);
        }
    };

    const onDragOver: React.DragEventHandler = e => {
        e.preventDefault();
        e.stopPropagation();
        // setFileFormatError(false);
        // setIsDraggedOver(true);
    };

    const onPaste: React.ClipboardEventHandler = e => {
        e.preventDefault();
        setSearchResults([]);
        const item = e.clipboardData?.items?.[0];
        console.log("item", item);
        if (item && item.kind === "file" && item.type.startsWith("image")) {
            const f = item.getAsFile();
            if (f) {
                onFileSelected(f);
            }
        } else if (item && item.kind === "string") {
            if (item.type === "text/html") {
                item.getAsString(htmlString => {
                    const tempContainer = document.createElement("div");
                    tempContainer.innerHTML = htmlString;
                    const imgElements = tempContainer.getElementsByTagName("img");
                    void onImageUrlPasted(imgElements[0].src, "imageUrl");
                    tempContainer.remove();
                });
            } else if (item.type === "text/plain") {
                item.getAsString(urlString => {
                    void onImageUrlPasted(urlString, "imageUrl");
                });
            }
        }
    };

    return (
        <div className={styles.vectorContainer}>
            {isImageSearch ? (
                <Stack horizontal tokens={{ childrenGap: 16 }}>
                    <label htmlFor="file-upload" className={styles.fileInputLabel}>
                        <Stack horizontal tokens={{ childrenGap: 16 }} className={styles.dropZone}>
                            <Stack
                                tokens={{ childrenGap: 10 }}
                                verticalAlign="center"
                                horizontalAlign="center"
                                onDragOver={onDragOver}
                                onDrop={onDrop}
                                // onDragLeave={() => {
                                //     setIsDraggedOver(false);
                                //     // setFileFormatError(false);
                                // }}
                            >
                                <input
                                    className={styles.fileInput}
                                    type="file"
                                    id="file-upload"
                                    accept="image/*"
                                    disabled={loading}
                                    onChange={e => e.target.files && onFileSelected(e.target.files[0])}
                                />
                                <Image28Regular />
                                <Text>{"Click to upload an image or drag an image here"}</Text>
                                <h6>OR</h6>
                                <input type="text" onPaste={onPaste} placeholder="Paste an image here" />
                            </Stack>
                            <CommandButton
                                iconProps={cancelIcon}
                                onClick={() => {
                                    setIsImageSearch(false);
                                    setSelectedImage("");
                                    setSearchResults([]);
                                }}
                            />
                        </Stack>
                    </label>

                    {selectedImage && (
                        <div className={styles.selectedImageContainer}>
                            <img src={selectedImage} alt="Selected" className={styles.selectedImage} />
                        </div>
                    )}
                </Stack>
            ) : (
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
                    <ImageAdd24Regular
                        onClick={() => {
                            setIsImageSearch(true);
                            setSearchQuery("");
                            setSearchResults([]);
                        }}
                    />
                    {searchQuery.length > 0 && <DismissCircle24Filled onClick={() => setSearchQuery("")} />}
                </Stack>
            )}

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
