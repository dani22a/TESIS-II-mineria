import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import {loadPlantEnergyModel} from './services/plantEnergy';

// Plant kWh model (optional): loaded once; the twin runs unchanged if it is unavailable.
void loadPlantEnergyModel();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
