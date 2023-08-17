import React from "react";
import ReactDOM from "react-dom/client";
import { initializeIcons } from "@fluentui/react";
import { createHashRouter, RouterProvider } from "react-router-dom";

import "./index.css";

import { Layout } from "./pages/Layout/Layout";
import { ImagePage } from "./pages/ImagePage/ImagePage";
import Vector from "./pages/Vector/Vector";

initializeIcons();

const router = createHashRouter([
    {
        path: "/",
        element: <Layout />,
        children: [
            {
                index: true,
                element: <Vector />
            },
            {
                path: "image",
                element: <ImagePage />
            }
        ]
    }
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);
