// Configuración de Firebase para el Dashboard de NutrIA
import { initializeApp } from "firebase/app";
import { getDatabase } from "firebase/database";

// Objeto de configuración de Firebase
const firebaseConfig = {
  apiKey: "AIzaSyAOhdoyWmzl1zrDLPmY7s0mkOUVS8uAVlQ",
  authDomain: "nutribot-3d198.firebaseapp.com",
  projectId: "nutribot-3d198",
  storageBucket: "nutribot-3d198.appspot.com",
  messagingSenderId: "TU_MESSAGING_SENDER_ID",
  appId: "1:1021861298825:web:c2a9756d97a58a7c60fc58",
  databaseURL: "https://nutribot-3d198-default-rtdb.firebaseio.com/",
};

// Inicializar aplicación Firebase
const app = initializeApp(firebaseConfig);

// Obtener instancia de Base de Datos en Tiempo Real
export const database = getDatabase(app);