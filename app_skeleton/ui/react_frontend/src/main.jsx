import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './fonts.css';   /* Source Sans 3, Source Serif 4, JetBrains Mono */
import './index.css';
import './typography.css';
import './theme/themeManager.css';
import './theme/consistency.css';

import { ApiProvider } from './api/ApiContext.jsx';
import { LocaleProvider } from './contexts/LocaleContext.jsx';
import { ThemeProvider } from './contexts/ThemeContext.jsx';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Farkki Lab Assistant could not start because #root was not found.');
}

createRoot(rootElement).render(
  <StrictMode>
    <ApiProvider>
      <LocaleProvider>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </LocaleProvider>
    </ApiProvider>
  </StrictMode>,
);
