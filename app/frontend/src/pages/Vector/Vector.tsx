import React, { useState, useCallback, useMemo, useEffect } from "react";
import { Checkbox, ChoiceGroup, DefaultButton, IChoiceGroupOption, Panel, Spinner, Stack, TextField } from "@fluentui/react";
import { DismissCircle24Filled, Search24Regular, Settings20Regular } from "@fluentui/react-icons";

import styles from "./Vector.module.css";

import { TextSearchResult, SemanticAnswer, Approach } from "../../api/types";
import { getTextSearchResults } from "../../api/textSearch";
import SampleCard from "../../components/SampleCards";

const Vector: React.FC = () => {
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [textQueryVector, setTextQueryVector] = useState<number[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [searchResults, setSearchResults] = useState<TextSearchResult[]>([]);
    const [semanticAnswer, setSemanticAnswer] = useState<SemanticAnswer | null>(null);
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState<boolean>(false);
    const [approach, setApproach] = useState<Approach>(Approach.Vector);
    const [filterText, setFilterText] = useState<string>("");
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(false);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);

    const approaches: IChoiceGroupOption[] = useMemo(
        () => [
            { key: Approach.Vector, text: "Vectors Only" },
            { key: Approach.VectorFilter, text: "Vectors with Filter" },
            { key: Approach.Hybrid, text: "Vectors + Text (Hybrid Search)" }
        ],
        []
    );

    useEffect(() => {
        if (searchQuery === "") {
            setSearchResults([]);
        }
    }, [searchQuery]);

    const executeSearch = useCallback(
        async (query: string) => {
            if (query.length === 0) {
                setSearchResults([]);
                return;
            }

            setLoading(true);
            const results = await getTextSearchResults(approach, query, useSemanticRanker, useSemanticCaptions, filterText);
            setTextQueryVector(results.queryVector);
            setSearchResults(results.results);
            setSemanticAnswer(results.semanticAnswers?.[0] ? results.semanticAnswers[0] : null);
            setLoading(false);
        },
        [approach, filterText, useSemanticCaptions, useSemanticRanker]
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

    const onApproachChange = useCallback((_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IChoiceGroupOption) => {
        setApproach((option?.key as Approach) ?? Approach.Vector);
    }, []);

    const onUseSemanticRankerChange = useCallback((_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticRanker(!!checked);
    }, []);

    const onUseSemanticCaptionsChange = useCallback((_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticCaptions(!!checked);
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
                    placeholder="Type something here (e.g. networking services)"
                    onChange={handleOnChange}
                    onKeyDown={handleOnKeyDown}
                />
                <Settings20Regular onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)} />
                {searchQuery.length > 0 && <DismissCircle24Filled onClick={() => setSearchQuery("")} />}
            </Stack>
            <div className={styles.spinner}>{loading && <Spinner label="Getting results" />}</div>
            <div className={styles.searchResultsContainer}>
                {searchResults.length === 0 && !loading ? (
                    <div className={styles.sampleCardsContainer}>
                        <SampleCard query="tools for software development" onClick={handleSampleCardClick} />
                        <SampleCard query="herramientas para el desarrollo de software" onClick={handleSampleCardClick} />
                        <SampleCard query="scalable storage solution" onClick={handleSampleCardClick} />
                    </div>
                ) : (
                    <>
                        {semanticAnswer && (
                            <Stack horizontal className={styles.semanticAnswerCard}>
                                <div className={styles.textContainer}>
                                    <p
                                        dangerouslySetInnerHTML={{
                                            __html: semanticAnswer.highlights
                                        }}
                                    ></p>
                                </div>
                            </Stack>
                        )}
                        {searchResults.map((result: TextSearchResult) => (
                            <Stack horizontal className={styles.searchResultCard} key={result.id}>
                                <div className={styles.textContainer}>
                                    <p className={styles.searchResultCardTitle}>{result.title} </p>
                                    <p className={styles.category}>{result.category}</p>
                                    <p
                                        dangerouslySetInnerHTML={{
                                            __html: result["@search.captions"]?.[0].highlights
                                                ? result["@search.captions"][0].highlights
                                                : result["@search.captions"]?.[0].text
                                                ? result["@search.captions"][0].text
                                                : result.content
                                        }}
                                    ></p>
                                </div>
                                <div className={styles.scoreContainer}>
                                    <p className={styles.score}>
                                        {`Score: ${
                                            approach === Approach.Hybrid && useSemanticRanker ? result["@search.reranker_score"] : result["@search.score"]
                                        }`}
                                    </p>
                                </div>
                            </Stack>
                        ))}
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
                <ChoiceGroup label="Retrieval mode" options={approaches} defaultSelectedKey={Approach.Vector} onChange={onApproachChange} />
                {approach === Approach.VectorFilter && (
                    <TextField
                        label="Filter"
                        value={filterText}
                        onChange={(_ev, newValue) => setFilterText(newValue ?? "")}
                        placeholder="(e.g. category eq 'Databases')"
                    />
                )}
                {approach === Approach.Hybrid && (
                    <>
                        <Checkbox
                            className={styles.vectorSettingsSeparator}
                            checked={useSemanticRanker}
                            label="Use semantic ranker for retrieval"
                            onChange={onUseSemanticRankerChange}
                        />
                        <Checkbox
                            className={styles.vectorSettingsSeparator}
                            checked={useSemanticCaptions}
                            label="Use semantic captions"
                            onChange={onUseSemanticCaptionsChange}
                            disabled={!useSemanticRanker}
                        />
                    </>
                )}

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
