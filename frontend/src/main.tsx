import React from 'react';
import ReactDOM from 'react-dom/client';
import '../../artifacts/shared/site-navigation.js';
import '../../artifacts/shared/site-navigation.css';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
