import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import { ref, onValue } from 'firebase/database';
import { database } from './firebase-config';
import logoDashboard from './assets/ia.png';
import deficitIcon from './assets/deficit.png';
import recomposicionIcon from './assets/recomposicion.png';
import superavitIcon from './assets/superavit.png';
import proteinasIcon from './assets/proteinas.png';
import carbsIcon from './assets/carbs.png';
import grasasIcon from './assets/grasas.png';

// Supongo que tienes estos componentes definidos en otro lugar
const CircleProgress = ({ progress }) => {
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <svg width="120" height="120" viewBox="0 0 120 120" className="progress-circle">
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke="#e6e6e6"
        strokeWidth="10"
      />
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke="#90ee90"
        strokeWidth="10"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.5s ease-in-out' }}
      />
      <text x="60" y="60" textAnchor="middle" dy=".3em" fontSize="20" fill="#2e8b57">
        {`${progress}%`}
      </text>
    </svg>
  );
};

const ProgressBar = ({ label, icon, value, max }) => {
  const progress = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="progress-bar-container">
      <div className="progress-label-row">
        <div className="progress-icon-container">
          <img src={icon} alt={`${label} icon`} className="progress-icon" />
        </div>
        <p className="progress-label">{label}</p>
        <p className="progress-value">{`${Math.round(value)} / ${Math.round(max)}`}</p>
      </div>
      <div className="bar-background">
        <div 
          className="bar-fill" 
          style={{ width: `${progress}%`, transition: 'width 0.5s ease-in-out' }}
        ></div>
      </div>
    </div>
  );
};

function Dashboard() {
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('diario');
  const [showModal, setShowModal] = useState(false);
  const [selectedFood, setSelectedFood] = useState(null);
  const [details, setDetails] = useState(null);

  const togglePeriod = () => {
    if (period === 'semanal') {
      setPeriod('mensual');
    } else if (period === 'mensual') {
      setPeriod('diario');
    } else {
      setPeriod('semanal');
    }
  };

  const handleFoodClick = (comida, detalle) => {
    setSelectedFood(comida);
    setDetails(detalle);
    setShowModal(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('currentUserChatId');
    window.location.reload();
  };

  useEffect(() => {
    const currentUserChatId = localStorage.getItem('currentUserChatId');

    if (!currentUserChatId) {
      setError("No hay un usuario logueado. Por favor, inicia sesión.");
      setLoading(false);
      return;
    }

    const userRef = ref(database, `usuarios/${currentUserChatId}`);

    const unsubscribe = onValue(userRef, (snapshot) => {
      if (snapshot.exists()) {
        const data = snapshot.val();
        setUserData(data);
        setLoading(false);
      } else {
        setError("No se encontraron datos para este usuario.");
        setLoading(false);
      }
    }, (err) => {
      setError("Error al cargar los datos: " + err.message);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // --- COMPROBACIONES DE ESTADO (CORREGIDAS) ---
  if (loading) {
    return <p>Cargando datos...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  // --- AHORA QUE SABEMOS QUE USERDATA EXISTE, PODEMOS DESESTRUCTURAR ---
  const { perfil, registros, macros_necesarios, recetas_generadas } = userData;

  const getMetasPeriodo = () => {
    const baseMacros = {
      calorias: macros_necesarios?.calorias || 0,
      proteina: macros_necesarios?.proteina || 0,
      grasa: macros_necesarios?.grasa || 0,
      carbohidratos: macros_necesarios?.carbohidratos || 0,
    };

    const multiplier = period === 'semanal' ? 7 : period === 'mensual' ? 28 : 1;

    return {
      calorias: baseMacros.calorias * multiplier,
      proteina: baseMacros.proteina * multiplier,
      grasa: baseMacros.grasa * multiplier,
      carbohidratos: baseMacros.carbohidratos * multiplier,
    };
  };

  const metasPeriodo = getMetasPeriodo();

  const selectedDieta = perfil?.tipoDieta || "Déficit calórico";
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');;
  const hoy = `${year}-${month}-${day}`;
  const totalesDeHoy = registros?.[hoy]?.totales_diarios
  const comidasDeHoy = Object.entries(registros?.[hoy]?.comidas || {});

  // Extraer la última receta generada para cada tipo de comida
  const obtenerUltimaReceta = (tipo_comida) => {
    const recetasDelTipo = recetas_generadas?.[tipo_comida.toLowerCase()] || {};
    const timestamps = Object.keys(recetasDelTipo).sort();
    if (timestamps.length === 0) return null;
    const ultimoTimestamp = timestamps[timestamps.length - 1];
    return recetasDelTipo[ultimoTimestamp]?.nombre || null;
  };

  const getDietaIcon = (dieta) => {
    switch (dieta) {
      case "Déficit calórico": return deficitIcon;
      case "Recomposición muscular": return recomposicionIcon;
      case "Superávit calórico": return superavitIcon;
      default: return null;
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1 className="dashboard-title">
          <img src={logoDashboard} alt="Logo de Nutria" className="dashboard-logo" />
          NutrIA Dashboard
        </h1>
        <div className="user-info">
          <span className="user-name">Hola, {perfil?.nombre}!</span>
          <button onClick={handleLogout} className="logout-button">Cerrar Sesión</button>
        </div>
      </header>
      <div className="bento-grid">
        {/* Columna 1: Información Personal */}
        <div className="bento-item user-project-container">
          <div className="inner-bento-item">
            <h3 className="bento-title">Datos del Usuario</h3>
            <p><strong>Altura:</strong> {perfil?.altura} cm</p>
            <p><strong>Peso:</strong> {perfil?.peso} kg</p>
            <p><strong>Sexo:</strong> {perfil?.genero}</p>
            <p><strong>Actividad Física:</strong> {perfil?.nivelActividad}</p>
          </div>
          <div className="inner-bento-item">
            <h3 className="bento-title">Datos del Proyecto</h3>
            <p><strong>Plataforma:</strong> Bot de Telegram</p>
            <p><strong>Desarrolladores:</strong> Jaime García - Daniel Chavez Jesúa Camuendo - Anthony Loja</p>
          </div>
        </div>
        {/* Cuadro 2: Dieta Seleccionada */}
        <div className="bento-item selected-dieta-box">
          <h3 className="bento-title">Tu Dieta Actual</h3>
          <img src={getDietaIcon(selectedDieta)} alt={`${selectedDieta} icon`} className="dieta-icon" />
          <p className="selected-dieta-text">{selectedDieta}</p>
        </div>
        {/* Cuadro 3: Progreso y Metas */}
        <div className="bento-item progress-and-goals-box">
          <div className="progress-header">
            <h3 className="bento-title">
              Progreso {period === 'semanal' ? 'Semanal' : period === 'mensual' ? 'Mensual' : 'Diario'}
            </h3>
            <button onClick={togglePeriod} className="period-toggle-btn">
              {period === 'semanal' ? 'Ver Mensual' : period === 'mensual' ? 'Ver Diario' : 'Ver Semanal'}
            </button>
          </div>
          <div className="progress-content">
            <div className="c
                progress={Math.round(
                  (totalesDeHoy?.total_calorias / metasPeriodo.calorias) * 100
                )}
             ircleProgress progress={Math.round(
                (totalesDeHoy?.total_calorias / metasPeriodo.calorias) * 100
              )} />
              <p>{totalesDeHoy?.total_calorias || 0} / {metasPeriodo.calorias} kcal</p>
            </div>
            <div className="macro-bars-container">
              <ProgressBar
                label="Proteínas"
                icon={proteinasIcon}
                value={totalesDeHoy?.total_proteina || 0}
                max={metasPeriodo.proteina || 0}
              />
              <ProgressBar
                label="Carbohidratos"
                icon={carbsIcon}
                value={totalesDeHoy?.total_carbohidratos || 0}
                max={metasPeriodo.carbohidratos || 0}
              />
              <ProgressBar
                label="Grasas"
                icon={grasasIcon}
                value={totalesDeHoy?.total_grasa || 0}
                max={metasPeriodo.grasa || 0}
              />
            </div>
          </div>
        </div>
        <div className="bento-item recommended-meals-box">
          <h3 className="bento-title">Recetas de Comidas</h3>
          <table>
            <thead>
              <tr>
                <th>Tipo de Comida</th>
                <th>Receta Recomendada</th>
              </tr>
            </thead>
            <tbody>
              {['Desayuno', 'Almuerzo', 'Cena'].map((tipo, index) => {
                const receta = obtenerUltimaReceta(tipo);
                return (
                  <tr key={index}>
                    <td><strong>{tipo}</strong></td>
                    <td>{receta || 'No hay recomendación aún'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {/* Cuadro 4: Comidas Registradas hoy */}
        <div className="bento-item meals-box">
          <h3 className="bento-title">Comidas Registradas</h3>
          <table>
            <thead>
              <tr>
                <th>Comida</th>
            <tbody>
              {comidasDeHoy.length > 0 ? (
                comidasDeHoy.map(([nombre, detalle], index) => (
                  <tr
                    key={index}
                    onClick={() => handleFoodClick(nombre, detalle)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>{nombre}</td>
                    <td>{hoy}</td>
                    <td>{detalle.calorias} kcal</td>
                  </tr>
                ))
              )}
            </tbody>
            </table>
            ))
        </div>
      </div>

      {/* Modal - Detalles de Comida */}
      {showModal && selectedFood && details && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button
              className="modal-close-btn"
              onClick={() => setShowModal(false)}
            >
              &times;
            </button>
            <h3 className="modal-title">Detalles de: {selectedFood}</h3>
            <p>
              <strong>Calorías:</strong> {details.calorias} kcal
            </p>
            <p>
              <strong>Proteínas:</strong> {details.proteinas} g
            </p>
            <p>
              <strong>Carbohidratos:</strong> {details.carbohidratos} g
            </p>
            <p>
              <strong>Grasas:</strong> {details.grasas} g
            
            <button className="modal-close-btn" onClick={() => setShowModal(false)}>
              &times;
            </button>
            <h3 className="modal-title">Detalles de: {selectedFood}</h3>
            <p><strong>Calorías:</strong> {Deatils.calorias} kcal</p>
            <p><strong>Proteínas:</strong> {Deatils.proteinas} g</p>
            <p><strong>Carbohidratos:</strong> {Deatils.carbohidratos} g</p>
            <p><strong>Grasas:</strong> {Deatils.grasas} g</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;