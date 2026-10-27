/**
 * INDEX.JSX - APPLICATION ENTRY POINT
 * 
 * This is the main entry point of our React application. It's the first file that runs
 * when the application starts. Think of it as the "main" function in other programming languages.
 * 
 * What this file does:
 * 1. Imports React and ReactDOM libraries
 * 2. Imports our main App component
 * 3. Imports global CSS styles
 * 4. Creates a root element in the HTML and renders our App component there
 * 
 * Key concepts for beginners:
 * - ReactDOM.createRoot(): Creates a root container where our React app will be rendered
 * - document.getElementById('root'): Finds the HTML element with id="root" in our index.html file
 * - root.render(): Actually puts our React app into that HTML element
 * - React.StrictMode: A development tool that helps catch potential problems
 */

// Import React library - this is the core library for building user interfaces
import { QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Import ReactDOM - this handles rendering React components to the DOM (Document Object Model)
// The DOM is how web browsers represent HTML elements as objects that can be manipulated
import ReactDOM from 'react-dom/client';

// Import our global CSS styles - this applies styling to the entire application
import './index.css';

// Import our main App component - this is the root component that contains all other components
import App from './App.jsx';
import { queryClient } from './shared/api/queryClient';
import { onSessionCleared } from './shared/auth/tokenStore';

onSessionCleared(() => queryClient.clear());

// Create a root container for our React application
// This tells React where in the HTML to render our app
const root = ReactDOM.createRoot(document.getElementById('root'));

// Render our App component inside the root container
// React.StrictMode is a wrapper that helps catch potential issues during development
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
