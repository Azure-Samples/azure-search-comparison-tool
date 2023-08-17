module.exports = {
    root: true,
    env: { browser: true, es2020: true },
    extends: [
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended-type-checked",
        "plugin:@typescript-eslint/stylistic-type-checked",
        "plugin:react-hooks/recommended",
        "plugin:react/recommended",
        "plugin:react/jsx-runtime",
        "eslint-config-prettier"
    ],
    ignorePatterns: ["dist", "public", "build", ".eslintrc.cjs", "vite.config.ts", "node_modules"],
    parser: "@typescript-eslint/parser",
    parserOptions: {
        ecmaversion: "latest",
        sourceType: "module",
        project: ["./tsconfig.json"],
        tsconfigRootDir: __dirname
    },
    plugins: ["react-refresh"],
    settings: {
        react: {
            version: "detect"
        },
        "import/resolver": {
            node: {
                paths: ["src"],
                extensions: [".js", ".jsx", ".ts", ".tsx"]
            }
        }
    },
    rules: {
        "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
        "@typescript-eslint/no-misused-promises": ["error", { checksVoidReturn: { attributes: false } }]
    }
};
