import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

const formatterMessage =
  "Format numbers and money through utils/formatters.jsx (useMoney, formatCurrency, formatPercentage, formatRatio, toInputDecimal).";

const plugins = {
  react,
  "react-hooks": reactHooks,
  "react-refresh": reactRefresh,
};

const rules = {
  ...react.configs.recommended.rules,
  ...react.configs["jsx-runtime"].rules,
  // Same hook rules as before; the v7 React Compiler rules are not enabled yet
  "react-hooks/rules-of-hooks": "error",
  "react-hooks/exhaustive-deps": "warn",
  "react/prop-types": "off",
  "react-refresh/only-export-components": [
    "warn",
    { allowConstantExport: true },
  ],
  "no-restricted-syntax": [
    "error",
    {
      selector: "CallExpression[callee.property.name='toFixed']",
      message: formatterMessage,
    },
    { selector: "Literal[value=/\\$\\d/]", message: formatterMessage },
    {
      selector: "TemplateElement[value.raw=/\\$\\d|\\$$/]",
      message: formatterMessage,
    },
    {
      selector: "JSXText[value=/\\$(\\d|\\s*$)/]",
      message: formatterMessage,
    },
  ],
};

export default [
  { ignores: ["dist", "src/shared/api/generated/**"] },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: "detect" } },
    plugins,
    rules: { ...js.configs.recommended.rules, ...rules },
  },
  ...tseslint.configs.recommended.map((config) => ({
    ...config,
    files: ["**/*.{ts,tsx}"],
  })),
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: globals.browser },
    settings: { react: { version: "detect" } },
    plugins,
    rules,
  },
  {
    // The formatters themselves, and the glossary's worked examples
    files: [
      "src/utils/formatters.jsx",
      "src/components/FinancialConcepts.jsx",
      "src/**/*.test.{js,jsx,ts,tsx}",
    ],
    rules: { "no-restricted-syntax": "off" },
  },
  {
    files: ["*.config.{js,cjs}"],
    languageOptions: { globals: globals.node },
  },
];
