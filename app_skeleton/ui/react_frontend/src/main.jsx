import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './fonts.css';   /* Source Sans 3, Source Serif 4, JetBrains Mono */
import './index.css';
import './typography.css';

import App from './App.jsx';
import { ApiProvider } from './api/ApiContext.jsx';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Farkki Lab Assistant could not start because #root was not found.');
}

createRoot(rootElement).render(
  <StrictMode>
    <ApiProvider>
      <App />
    </ApiProvider>
  </StrictMode>,
);
