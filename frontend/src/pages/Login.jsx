import React, { useState } from 'react';
import './Login.css'; // Importando o nosso arquivo de estilos separado

export default function LoginRegulacao() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    console.log('Tentando logar com:', { username, password });
    // Integração com o backend Python
  };

  return (
    <div className="login-wrapper">
      <div className="login-container">
        
        {/* Logo e Título do Sistema */}
        <div className="logo-header">
          <div className="logo-circle">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
          </div>
          <span className="logo-text">Regulação</span>
        </div>

        {/* Título da tela */}
        <div className="title-wrapper">
          <h1 className="login-title">Login</h1>
        </div>

        {/* Formulário */}
        <form onSubmit={handleLogin} className="login-form">
          
          <div className="input-group">
            <label className="input-label">Usuário SISREG</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="login-input"
            />
          </div>

          <div className="input-group">
            <label className="input-label">Senha</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="login-input"
            />
          </div>

          <div className="btn-wrapper">
            <button type="submit" className="login-button">
              Login
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}