import React, { useState } from 'react';
import './Login.css';
import { ref, get } from "firebase/database";
import { database } from './firebase-config';
import CryptoJS from 'crypto-js';

function Login({ onLogin }) {
  const [chatId, setChatId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!chatId || !password) {
      setError('Por favor, ingresa tu ID de usuario y tu contraseña.');
      setLoading(false);
      return;
    }

    try {
      // Hashear la contraseña ingresada usando SHA256
      const hashedPassword = CryptoJS.SHA256(password).toString();

      // Crear referencia al perfil del usuario en la base de datos
      const userRef = ref(database, `usuarios/${chatId}/perfil`);

      // Obtener datos del perfil del usuario (lectura única)
      const snapshot = await get(userRef);

      if (snapshot.exists()) {
        const userData = snapshot.val();

        // Verificar si la contraseña hasheada coincide con la almacenada
        if (userData.hashed_password === hashedPassword) {
          // Guardar chat_id en almacenamiento local para usarlo en otras páginas
          localStorage.setItem('currentUserChatId', chatId);
          onLogin(chatId);
        } else {
          setError("Contraseña incorrecta");
        }
      } else {
        setError("Usuario no encontrado");
      }
    } catch (err) {
      console.error("Error al iniciar sesión:", err);
      setError("Ocurrió un error al conectar con la base de datos");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form onSubmit={handleSubmit} className="login-form">
        <h2>Iniciar Sesión</h2>
        {error && <p className="error-message">{error}</p>}
        <div className="form-group">
          <label>Usuario</label>
          <input
            type="text"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label>Contraseña</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />
        </div>
        <button type="submit" className="login-button" disabled={loading}>
          {loading ? 'Cargando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}

export default Login;