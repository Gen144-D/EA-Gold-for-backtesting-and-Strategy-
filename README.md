
# 🏆 EA Gold Backtesting & Strategy Framework

A minimal, high-performance setup utilizing **React**, **TypeScript**, and **Vite** with Fast HMR and structured ESLint rules. This repository is specifically tailored for building front-end user interfaces, backtesting workflows, and data visualizations for the **EA Gold (XAUUSD)** automated trading strategy.

---

## 🛠️ Tech Stack & Features

* **Framework:** [React 19](https://react.dev/) with TypeScript for type-safe frontend UI.
* **Build Tool:** [Vite](https://vite.dev/) for near-instantaneous Hot Module Replacement (HMR).
* **Vite Plugins:** Powered by [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react) utilizing the fast [Oxc](https://oxc.rs) compiler, or optionally [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) via [SWC](https://swc.rs/).

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have [Node.js](https://nodejs.org/) installed (v18+ recommended).

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/Gen144-D/EA-Gold-for-backtesting-and-Strategy-.git
cd EA-Gold-for-backtesting-and-Strategy-
npm install
```

### 3. Development
Start the local development server:
```bash
npm run dev
```

### 4. Build
Compile and bundle the production-ready assets:
```bash
npm run build
```

---

## 🤖 React Compiler (Optional)

The React Compiler is **disabled by default** in this template to maintain maximum development and build speeds. If your strategy dashboard requires intense state optimizations, follow the [React Compiler Installation Guide](https://react.dev/learn/react-compiler/installation) to activate it.

---

## 🧹 Code Quality & Linting

### Type-Aware Lint Rules
For production stability, replace `tseslint.configs.recommended` with type-checked rules in your configuration:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Type-checked rules for robust data handling
      tseslint.configs.recommendedTypeChecked,
      
      // Alternative strict options:
      // tseslint.configs.strictTypeChecked,
      // tseslint.configs.stylisticTypeChecked,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
])
```

### Advanced React Formatting
Install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) to apply specialized rules for UI components:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      reactX.configs['recommended-typescript'],
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
])
```
