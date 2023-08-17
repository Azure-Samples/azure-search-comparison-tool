import React from "react";
import styles from "./SampleCards.module.css";

interface SampleCardProps {
    query: string;
    onClick: (query: string) => void;
}

const SampleCard: React.FC<SampleCardProps> = ({ query, onClick }) => {
    const handleClick = () => {
        onClick(query);
    };

    return (
        <div className={styles.sampleCard} onClick={handleClick}>
            <p className={styles.sampleCardText}>{query}</p>
        </div>
    );
};

export default SampleCard;
