import React, { useState, useCallback, useMemo, useEffect } from "react";
import { Checkbox, DefaultButton, Dropdown, IDropdownOption, MessageBar, MessageBarType, Panel, Spinner, Stack, TextField, Toggle } from "@fluentui/react";
import { DismissCircle24Filled, Search24Regular, Settings20Regular } from "@fluentui/react-icons";

import styles from "./Vector.module.css";

import { TextSearchResult, Approach, ResultCard, ApproachKey, AxiosErrorResponseData } from "../../api/types";
import { getEmbeddings, getTextSearchResults } from "../../api/textSearch";
import SampleCard from "../../components/SampleCards";
import { AxiosError } from "axios";
import { getEfSearch, updateEfSearch } from "../../api/indexSchema";

const MaxSelectedModes = 4;

const Vector: React.FC = () => {
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [textQueryVector, setTextQueryVector] = useState<number[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [resultCards, setResultCards] = useState<ResultCard[]>([]);
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState<boolean>(false);
    const [selectedApproachKeys, setSelectedApproachKeys] = useState<ApproachKey[]>(["text", "vec", "hs", "hssr"]);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [hideScores, setHideScores] = React.useState<boolean>(true);
    const [errors, setErrors] = React.useState<string[]>([]);
    const [efSearchInSchema, setEfSearchInSchema] = React.useState<string>("");
    const [efSearch, setEfSearch] = React.useState<string>("");
    const [validationError, setValidationError] = React.useState<string>("");
    const [selectedDatasetKey, setSelectedDatasetKey] = React.useState<string>("sample");

    const approaches: Approach[] = useMemo(
        () => [
            { key: "text", title: "Text Only (BM25)" },
            { key: "vec", title: "Vectors Only (ANN)" },
            { key: "hs", title: "Vectors + Text (Hybrid Search)" },
            { key: "hssr", title: "Hybrid + Semantic Reranking" }
        ],
        []
    );

    const Datasets: IDropdownOption[] = useMemo(
        () => [
            { key: "sample", text: "Azure Services", title: "Sample text data" },
            { key: "wikipedia", text: "Wikipedia Articles", title: "Wikipedia articles data" }
        ],
        []
    );

    let sampleQueries: string[] = [];
    if (selectedDatasetKey === "sample") {
        sampleQueries = ["tools for software development", "herramientas para el desarrollo de software", "scalable storage solution"];
    } else if (selectedDatasetKey === "wikipedia") {
        sampleQueries = ["species of tigers", "world history", "global delicious food"];
    }

    useEffect(() => {
        if (searchQuery === "") {
            setResultCards([]);
        }

        if (efSearchInSchema === "") {
            const getEfSearchInSchema = async () => {
                try {
                    const currentEfSearch = await getEfSearch();
                    setEfSearchInSchema(currentEfSearch);
                    setEfSearch(currentEfSearch);
                } catch (e) {
                    setErrors([`Failed to get efSearch value ${String(e)}`]);
                }
            };
            void getEfSearchInSchema();
        }
    }, [efSearch, efSearchInSchema, searchQuery]);

    const executeSearch = useCallback(
        async (query: string) => {
            if (query.length === 0) {
                setResultCards([]);
                return;
            }
            setTextQueryVector([]);
            setLoading(true);

            let searchApproachKeys = selectedApproachKeys;
            if (selectedApproachKeys.length === 0) {
                searchApproachKeys = ["text", "vec", "hs", "hssr"];
            }
            setSelectedApproachKeys(searchApproachKeys);

            let resultsList: ResultCard[] = [];
            let searchErrors: string[] = [];
            let queryVector: number[] = [];

            if (Number(efSearch) !== Number(efSearchInSchema)) {
                try {
                    const newEfSearch = await updateEfSearch(efSearch);
                    setEfSearchInSchema(newEfSearch);
                } catch (e) {
                    searchErrors = searchErrors.concat(`Failed to update efSearch value ${String(e)}`);
                    setErrors(searchErrors);
                    setLoading(false);
                    return;
                }
            }

            if (!(searchApproachKeys.length === 1 && searchApproachKeys[0] === "text")) {
                try {
                    queryVector = await getEmbeddings(query);
                    setTextQueryVector(queryVector);
                } catch (e) {
                    searchErrors = searchErrors.concat(`Failed to generate embeddings ${String(e)}`);
                    setErrors(searchErrors);
                    setLoading(false);
                    return;
                }
            }

            Promise.allSettled(
                searchApproachKeys.map(async approachKey => {
                    const results = await getTextSearchResults(approachKey, query, useSemanticCaptions, selectedDatasetKey, queryVector);
                    const searchResults = results.results;
                    const resultCard: ResultCard = {
                        approachKey,
                        searchResults
                    };
                    return resultCard;
                })
            )
                .then(results => {
                    const promiseResultsList = results.filter(result => result.status === "fulfilled") as PromiseFulfilledResult<ResultCard>[];
                    resultsList = promiseResultsList.map(r => r.value);
                    const errors = results.filter(result => result.status === "rejected") as PromiseRejectedResult[];
                    errors.map(e => {
                        const err = e.reason as AxiosError;
                        const data = err.response?.data as AxiosErrorResponseData;
                        data ? (searchErrors = [`${String(data.error)}`, ...searchErrors]) : (searchErrors = [`${err.message}`, ...searchErrors]);
                    });
                })
                .catch(e => (searchErrors = searchErrors.concat(String(e))))
                .finally(() => {
                    setResultCards(resultsList);
                    setErrors(searchErrors);
                    setLoading(false);
                });
        },
        [selectedApproachKeys, efSearch, efSearchInSchema, useSemanticCaptions, selectedDatasetKey]
    );

    const handleOnKeyDown = useCallback(
        async (e: React.KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                await executeSearch(searchQuery);
            }
        },
        [searchQuery, executeSearch]
    );

    const handleSampleCardClick = (query: string) => {
        setSearchQuery(query);
        void executeSearch(query);
    };

    const handleOnChange = useCallback((_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setSearchQuery(newValue ?? "");
    }, []);

    const onApproachChange = useCallback(
        (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean, approach?: Approach) => {
            if (approach?.key) {
                checked
                    ? !selectedApproachKeys.includes(approach.key) && setSelectedApproachKeys([...selectedApproachKeys, approach.key])
                    : setSelectedApproachKeys(selectedApproachKeys.filter(a => a !== approach.key));
            }
        },
        [selectedApproachKeys]
    );

    const onUseSemanticCaptionsChange = useCallback((_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticCaptions(!!checked);
    }, []);

    const onEfSearchChanged = React.useCallback(
        (event: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, value?: string) => {
            const numberValue = Number(value);
            if (!!value && isNaN(numberValue)) {
                event.preventDefault();
            } else {
                setEfSearch(value ?? efSearchInSchema);
                numberValue > 1000 || numberValue < 100 ? setValidationError("The allowable range is 100 to 1000.") : setValidationError("");
            }
        },
        [efSearchInSchema]
    );

    const onDatasetChange = React.useCallback((_event: React.FormEvent<HTMLDivElement>, item?: IDropdownOption): void => {
        setResultCards([]);
        setSelectedDatasetKey(String(item?.key) ?? "sample");
    }, []);

    return (
        <div className={styles.vectorContainer}>
            <p className={styles.approach}>Dataset: {Datasets.find(d => d.key === selectedDatasetKey)?.text}</p>
            <Stack horizontal className={styles.questionInputContainer}>
                <Search24Regular />
                <TextField
                    className={styles.questionInputTextArea}
                    resizable={false}
                    borderless
                    value={searchQuery}
                    placeholder="Type something here (e.g. networking services)"
                    onChange={handleOnChange}
                    onKeyDown={handleOnKeyDown}
                />
                <Settings20Regular onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)} />
                {searchQuery.length > 0 && <DismissCircle24Filled onClick={() => setSearchQuery("")} />}
            </Stack>
            <div className={styles.spinner}>{loading && <Spinner label="Getting results" />}</div>
            <div className={styles.searchResultsContainer}>
                {errors &&
                    !!errors.length &&
                    errors.map(e => (
                        <MessageBar key={e} messageBarType={MessageBarType.error}>
                            {e}
                        </MessageBar>
                    ))}
                {resultCards.length === 0 && !loading ? (
                    <div className={styles.sampleCardsContainer}>
                        {sampleQueries.map(query => (
                            <SampleCard key={query} query={query} onClick={handleSampleCardClick} />
                        ))}
                    </div>
                ) : (
                    <>
                        <Stack horizontal tokens={{ childrenGap: "12px" }}>
                            {resultCards.map(resultCard => (
                                <div key={resultCard.approachKey} className={styles.resultCardContainer}>
                                    <p className={styles.approach}>{approaches.find(a => a.key === resultCard.approachKey)?.title} </p>
                                    {!resultCard.searchResults.length && <p className={styles.searchResultCardTitle}>{"No results found"} </p>}
                                    {resultCard.searchResults.map((result: TextSearchResult) => (
                                        <Stack horizontal className={styles.searchResultCard} key={result.id}>
                                            <div className={styles.textContainer}>
                                                <Stack horizontal horizontalAlign="space-between">
                                                    <div className={styles.titleContainer}>
                                                        <p className={styles.searchResultCardTitle}>{result.title} </p>
                                                        {selectedDatasetKey === "sample" && <p className={styles.category}>{result.category}</p>}
                                                    </div>
                                                    {!hideScores && (
                                                        <div className={styles.scoreContainer}>
                                                            <p className={styles.score}>
                                                                {`Score: ${
                                                                    resultCard.approachKey === "hssr"
                                                                        ? result["@search.reranker_score"]?.toFixed(3)
                                                                        : result["@search.score"]?.toFixed(3)
                                                                }`}
                                                            </p>
                                                        </div>
                                                    )}
                                                </Stack>
                                                <p
                                                    className={styles.content}
                                                    dangerouslySetInnerHTML={{
                                                        __html: result["@search.captions"]?.[0].highlights
                                                            ? result["@search.captions"][0].highlights
                                                            : result["@search.captions"]?.[0].text
                                                            ? result["@search.captions"][0].text
                                                            : result.content
                                                    }}
                                                />
                                            </div>
                                        </Stack>
                                    ))}
                                </div>
                            ))}
                        </Stack>
                    </>
                )}
            </div>

            <Panel
                headerText="Settings"
                isOpen={isConfigPanelOpen}
                isBlocking={false}
                onDismiss={() => setIsConfigPanelOpen(false)}
                closeButtonAriaLabel="Close"
                onRenderFooterContent={() => <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>Close</DefaultButton>}
                isFooterAtBottom={true}
            >
                <Toggle
                    label="Show scores"
                    checked={!hideScores}
                    inlineLabel
                    onChange={(_, checked) => {
                        checked ? setHideScores(false) : setHideScores(true);
                    }}
                />
                <p className={styles.retrievalMode}>Retrieval mode</p>
                {approaches.map(approach => (
                    <div key={approach.key}>
                        <Checkbox
                            className={styles.vectorSettingsSeparator}
                            checked={selectedApproachKeys.includes(approach.key)}
                            label={approach.title}
                            onChange={(_ev, checked) => onApproachChange(_ev, checked, approach)}
                            disabled={selectedApproachKeys.length == MaxSelectedModes && !selectedApproachKeys.includes(approach.key)}
                        />
                        {approach.key === "hssr" && selectedApproachKeys.includes("hssr") && (
                            <>
                                <Checkbox
                                    className={styles.checkboxSemanticCaption}
                                    checked={useSemanticCaptions}
                                    label="Use semantic captions"
                                    onChange={onUseSemanticCaptionsChange}
                                    styles={{ checkbox: { borderRadius: "100%" } }}
                                />
                            </>
                        )}
                    </div>
                ))}
                <TextField className={styles.efSearch} label="efSearch" value={efSearch} onChange={onEfSearchChanged} errorMessage={validationError} />
                <Dropdown label="Dataset" selectedKey={selectedDatasetKey} onChange={onDatasetChange} options={Datasets} />
                {textQueryVector && (
                    <>
                        <p>Embedding model name:</p>
                        <code className={styles.textQueryVectorModel}>openai text-embedding-ada-002</code>
                        <p>Text query vector:</p>
                        <code className={styles.textQueryVector}>[{textQueryVector.join(", ")}]</code>
                    </>
                )}
            </Panel>
        </div>
    );
};

export default Vector;
