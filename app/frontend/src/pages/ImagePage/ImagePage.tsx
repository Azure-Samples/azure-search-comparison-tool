import React, { useState, useCallback } from "react";
import { Spinner, Stack, TextField, Text, IIconProps, CommandButton, MessageBar, MessageBarType } from "@fluentui/react";
import { DismissCircle24Filled, ImageAdd24Regular, ImageSearch24Regular, Search24Regular } from "@fluentui/react-icons";

import styles from "./ImagePage.module.css";

import { getImageSearchResults } from "../../api/imageSearch";
import { ImageSearchResult } from "../../api/types";

export const ImagePage = () => {
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [searchResults, setSearchResults] = useState<ImageSearchResult[]>([]);
    const [isImageSearch, setIsImageSearch] = React.useState(false);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = React.useState<string>("");
    const [textValue, setTextValue] = React.useState("");

    const handleOnKeyDown = useCallback(
        async (e: React.KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (searchQuery.length === 0) {
                    setSearchResults([]);
                    setErrorMessage("");
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
        try {
            const results = await getImageSearchResults(query, dataType);
            setSearchResults(results.results);
        } catch (e) {
            setErrorMessage(
                `Failed to fetch results. Details: ${String(e)}. Only publicly reachable URL of an image is supported. Please double check the image URL.`
            );
        }
        setLoading(false);
    };
    const cancelIcon: IIconProps = { iconName: "Cancel" };

    const onDrop: React.DragEventHandler = e => {
        e.preventDefault();
        setSearchResults([]);
        setErrorMessage("");
        setSelectedImage("");

        console.log("ett", e);
        const item = e.dataTransfer?.files?.[0];
        if (item && item.type.startsWith("image")) {
            onFileSelected(item);
        }
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
                    setTextValue(urlString || "");
                });
            }
        }
    };

    const onFileInput: React.ChangeEventHandler<HTMLInputElement> = e => {
        e.preventDefault();
        setSearchResults([]);
        setErrorMessage("");
        setSelectedImage("");

        e.target.files?.[0].type.startsWith("image") && onFileSelected(e.target.files[0]);
    };

    // const onTextInput: React.ChangeEventHandler<HTMLInputElement> = e => {
    //     if (!e.target.value.startsWith("http")) {
    //         setErrorMessage(`Invalid image URL`);
    //     }
    // };
    return (
        <div className={styles.vectorContainer}>
            {isImageSearch ? (
                <Stack horizontal horizontalAlign="center" tokens={{ childrenGap: 50 }}>
                    <label htmlFor="file-upload" className={styles.fileInputLabel}>
                        <Stack horizontal horizontalAlign="end" className={styles.dropZone}>
                            <Stack
                                className={styles.imageInput}
                                tokens={{ childrenGap: 10 }}
                                verticalAlign="center"
                                horizontalAlign="center"
                                onDragOver={onDragOver}
                                onDrop={onDrop}
                            >
                                <input className={styles.fileInput} type="file" id="file-upload" onChange={onFileInput} />
                                <ImageAdd24Regular />
                                <Text variant="large" className={styles.text}>
                                    {"Click to upload an image or drag an image here"}
                                </Text>
                                <h6>------OR------</h6>
                                <TextField
                                    className={styles.imagePaste}
                                    type="text"
                                    onPaste={onPaste}
                                    // onChange={onTextInput}
                                    value={textValue}
                                    placeholder="Paste an image or an image URL here"
                                />
                            </Stack>
                            <CommandButton
                                iconProps={cancelIcon}
                                onClick={() => {
                                    setIsImageSearch(false);
                                    setSelectedImage("");
                                    setSearchResults([]);
                                    setErrorMessage("");
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
                    <ImageSearch24Regular
                        onClick={() => {
                            setIsImageSearch(true);
                            setSearchQuery("");
                            setSearchResults([]);
                            setErrorMessage("");
                        }}
                    />
                    {searchQuery.length > 0 && <DismissCircle24Filled onClick={() => setSearchQuery("")} />}
                </Stack>
            )}

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
