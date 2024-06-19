import React, { useState, useCallback, useMemo, useEffect } from "react";
import { Checkbox, DefaultButton, Dropdown, IDropdownOption, MessageBar, MessageBarType, Panel, Spinner, Stack, TextField, Toggle } from "@fluentui/react";
import { DismissCircle24Filled, Search24Regular, Settings20Regular } from "@fluentui/react-icons";

import styles from "./Vector.module.css";

import { TextSearchResult, Approach, ResultCard, AxiosErrorResponseData } from "../../api/types";
import { getEmbeddings, getTextSearchResults } from "../../api/textSearch";
import { getApproaches } from "../../api/approaches";
import SampleCard from "../../components/SampleCards";
import { AxiosError } from "axios";

const MaxSelectedModes = 4;

const Vector: React.FC = () => {
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [textQueryVector, setTextQueryVector] = useState<number[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [resultCards, setResultCards] = useState<ResultCard[]>([]);
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState<boolean>(false);
    const [selectedApproachKeys, setSelectedApproachKeys] = useState<string[]>(["text"]);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [hideScores, setHideScores] = React.useState<boolean>(true);
    const [errors, setErrors] = React.useState<string[]>([]);
    const [selectedDatasetKey, setSelectedDatasetKey] = React.useState<string>("conditions");
    const [allApproaches, setAllApproaches] = React.useState<Approach[]>([]);

    useEffect(() => {
        async function loadApproaches() {
            const all_approaches = await getApproaches();

            setAllApproaches(all_approaches);
        }
        loadApproaches().catch(() => console.log("oh no!"));
    }, []);

    const getApproachesForDataSet = useCallback(() => {
        return allApproaches.filter(a => a.data_set == selectedDatasetKey).map(a => a);
    }, [allApproaches, selectedDatasetKey]);

    const approaches: Approach[] = useMemo(() => getApproachesForDataSet(), [getApproachesForDataSet]);

    const Datasets: IDropdownOption[] = useMemo(
        () => [
            { key: "conditions", text: "NHSUK Conditions", title: "Short conditions articles" },
            { key: "combined", text: "NHSUK Combined Conditions & Medicines", title: "Conditions & Medicines documents" }
        ],
        []
    );

    let sampleQueries: string[] = [];
    if (selectedDatasetKey === "combined") {
        sampleQueries = ["acupuncture", "alendronic acid", "side effects"];
    } else if (selectedDatasetKey === "conditions") {
        sampleQueries = ["heart attack", "cancer", "ADHD"];
    }

    const executeSearch = useCallback(
        async (query: string) => {
            if (query.length === 0) {
                setResultCards([]);
                return;
            }
            setTextQueryVector([]);
            setLoading(true);

            const searchApproaches = allApproaches.filter(a => selectedApproachKeys.includes(a.key)).map(a => a);

            let resultsList: ResultCard[] = [];
            let searchErrors: string[] = [];
            let queryVector: number[] = [];

            if (searchApproaches.filter(a => a.use_vector_search === true).length > 0) {
                const approachKey = searchApproaches.filter(a => a.use_vector_search === true).map(a => a)[0].key;

                try {
                    queryVector = await getEmbeddings(query, approachKey);
                    setTextQueryVector(queryVector);
                } catch (e) {
                    searchErrors = searchErrors.concat(`Failed to generate embeddings ${String(e)}`);
                    setErrors(searchErrors);
                    setLoading(false);
                    return;
                }
            }

            Promise.allSettled(
                searchApproaches.map(async approach => {
                    const results = await getTextSearchResults(approach, query, useSemanticCaptions, selectedDatasetKey, queryVector);
                    const searchResults = results.results;
                    const resultCard: ResultCard = {
                        approachKey: approach.key,
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
        [selectedApproachKeys, useSemanticCaptions, selectedDatasetKey, allApproaches]
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

    const onDatasetChange = React.useCallback((_event: React.FormEvent<HTMLDivElement>, item?: IDropdownOption): void => {
        setResultCards([]);

        const dataSet = String(item?.key) ?? "conditions";
        const selectedApproach = dataSet === "conditions" ? "text" : "text_2";

        setSelectedDatasetKey(dataSet);
        setSelectedApproachKeys([selectedApproach]);
    }, []);

    function isChecked(approachKey: string): boolean {
        return selectedApproachKeys.includes(approachKey);
    }

    function isDisabled(approachKey: string): boolean {
        return selectedApproachKeys.length == MaxSelectedModes && !selectedApproachKeys.includes(approachKey);
    }

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
                                                        {selectedDatasetKey === "conditions" && <p className={styles.category}>{result.category}</p>}
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
                            checked={isChecked(approach.key)}
                            label={approach.title}
                            onChange={(_ev, checked) => onApproachChange(_ev, checked, approach)}
                            disabled={isDisabled(approach.key)}
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
