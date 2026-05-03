import React, { useState } from 'react';
import './Login.css'; 
import logoPet from '../assets/logo-pet.jpeg'; 

export default function LoginRegulacao() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

const handleLogin = async (e) => {
    e.preventDefault();
    console.log('Enviando dados para o backend...');

    try {
      // Aqui você coloca o endereço e a rota exata do seu backend Python
      const resposta = await fetch('http://localhost:8000/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Transforma o usuário e senha em um formato que o Python entende (JSON)
        body: JSON.stringify({ 
          usuario: username, 
          senha: password 
        })
      });

      if (resposta.ok) {
        const dados = await resposta.json();
        console.log('Login com sucesso!', dados);
        // Deu certo! Aqui nós vamos redirecionar o médico para o Dashboard depois
        alert('Login autorizado pelo Python!'); 
      } else {
        // O backend retornou erro (ex: 401 Unauthorized)
        alert('Usuário ou senha incorretos no SISREG!');
      }
    } catch (erro) {
      console.error('Erro de conexão:', erro);
      alert('O backend Python parece estar desligado.');
    }
  };
  return (
    <div className="login-wrapper">
      <div className="login-container">
        
        {/* Logo e Título do Sistema */}
        <div className="logo-header">
          <div className="logo-circle">
            <img src={logoPet} alt="Logo PET-Saúde" className="logo-img" />   
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