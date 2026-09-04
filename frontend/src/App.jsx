import { useState } from 'react';
import {
  Shield,
  LayoutDashboard,
  Users,
  Map,
  Layers,
  History,
  Radio,
  Cpu,
} from 'lucide-react';
import { api } from './api';
import Dashboard from './pages/Dashboard';
import Usuarios from './pages/Usuarios';
import Zonas from './pages/Zonas';
import Niveles from './pages/Niveles';
import Historial from './pages/Historial';
import Dispositivos from './pages/Dispositivos';
import Simulador from './pages/Simulador';

const VISTAS = [
  { id: 'dashboard', label: 'En vivo', icon: LayoutDashboard },
  { id: 'usuarios', label: 'Clientes y llaves', icon: Users },
  { id: 'zonas', label: 'Zonas', icon: Map },
  { id: 'niveles', label: 'Niveles', icon: Layers },
  { id: 'historial', label: 'Auditoría', icon: History },
  { id: 'dispositivos', label: 'Controladoras', icon: Radio },
  { id: 'simulador', label: 'Tótem virtual', icon: Cpu },
];

function Login({ onLogin }) {
  const [username, setUsername] = useState('operador');
  const [password, setPassword] = useState('apl2026');
  const [error, setError] = useState('');

  const enviar = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const data = await api.post('/auth/login/', { username, password });
      onLogin(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>SGCA-APL</h1>
        <p>Panel del operador — entradas y salidas en vivo</p>
        <form onSubmit={enviar}>
          <label>
            Usuario
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <div className="error">{error}</div>}
          <button className="btn btn-primary" type="submit">
            Entrar
          </button>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [vista, setVista] = useState('dashboard');
  const [operador, setOperador] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('sgca_operador') || 'null');
    } catch {
      return null;
    }
  });

  const login = (data) => {
    localStorage.setItem('sgca_operador', JSON.stringify(data));
    setOperador(data);
  };

  const logout = () => {
    localStorage.removeItem('sgca_operador');
    setOperador(null);
  };

  if (!operador) {
    return <Login onLogin={login} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Shield size={32} color="#3b82f6" />
          <h2>SGCA-APL</h2>
        </div>
        <nav className="nav">
          {VISTAS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={vista === id ? 'active' : ''}
              onClick={() => setVista(id)}
            >
              <Icon size={18} /> {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div>
            {operador.nombre}
            <br />
            Turno {operador.turno_asignado}
          </div>
          <button type="button" onClick={logout}>
            Salir
          </button>
        </div>
      </aside>
      <main className="content">
        {vista === 'dashboard' && <Dashboard operador={operador} />}
        {vista === 'usuarios' && <Usuarios />}
        {vista === 'zonas' && <Zonas />}
        {vista === 'niveles' && <Niveles />}
        {vista === 'historial' && <Historial />}
        {vista === 'dispositivos' && <Dispositivos />}
        {vista === 'simulador' && <Simulador />}
      </main>
    </div>
  );
}
