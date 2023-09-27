import * as React from "react";

import { Icon, Stack, Text } from "@fluentui/react";

interface Props {
    onFileSelected: (file: File) => void;
    acceptFileType: string;
    disabled: boolean;
}

const DropZone = ({ acceptFileType, disabled, onFileSelected }: Props) => {
    const [isDraggedOver, setIsDraggedOver] = React.useState(false);
    const [fileFormatError, setFileFormatError] = React.useState(false);

    const onDragOver: React.DragEventHandler = e => {
        e.preventDefault();
        e.stopPropagation();
        setFileFormatError(false);

        if (disabled) {
            return;
        }

        // Select the first file if multiple files were dragged
        if ((e?.dataTransfer?.items || [])[0]?.type === acceptFileType) {
            setIsDraggedOver(true);
        } else {
            setFileFormatError(true);
        }
    };

    const onDrop: React.DragEventHandler = e => {
        e.preventDefault();

        if (disabled) {
            return;
        }

        if (e.dataTransfer.files?.[0] && e.dataTransfer.files[0].type === acceptFileType) {
            setIsDraggedOver(false);
            onFileSelected(e.dataTransfer.files[0]);
        }
    };

    return (
        <Stack
            tokens={{ childrenGap: 10 }}
            verticalAlign="center"
            horizontalAlign="center"
            className={`${isDraggedOver ? "" : ""}`}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onDragLeave={() => {
                setIsDraggedOver(false);
                setFileFormatError(false);
            }}
        >
            <Icon iconName="Add" />
            <Text className={fileFormatError ? "" : ""}>
                {fileFormatError ? "ClientResources.Serverless.Add.formatError" : "ClientResources.Serverless.Add.drag"}
            </Text>
        </Stack>
    );
};

export default DropZone;
