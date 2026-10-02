import { useEffect, useState } from 'react';
import {
  Shield,
  LayoutDashboard,
  Users,
  Map,
  Layers,
  History,
  Radio,
  Cpu,
  Wrench,
} from 'lucide-react';
import { api, setUnauthorizedHandler } from './api';
import Dashboard from './pages/Dashboard';
import Usuarios from './pages/Usuarios';
import Zonas from './pages/Zonas';
import Niveles from './pages/Niveles';
import Historial from './pages/Historial';
import Dispositivos from './pages/Dispositivos';
import Simulador from './pages/Simulador';
import Incidentes from './pages/Incidentes';
import OrdenesTecnico from './pages/OrdenesTecnico';

const VISTAS_OPERADOR = [
  { id: 'dashboard', label: 'En vivo', icon: LayoutDashboard },
  { id: 'incidentes', label: 'Incidentes', icon: Wrench },
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
      await api.get('/auth/csrf/');
      const data = await api.post('/auth/login/', { username, password });
      onLogin(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <p className="kicker">SGCA-APL</p>
        <h1>Ingreso al sistema</h1>
        <p className="lede">Acceso para operadores y técnicos de APL Seguridad.</p>
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
  const [edificios, setEdificios] = useState([]);
  const [edificioId, setEdificioId] = useState('');
  const [usuario, setUsuario] = useState(undefined);

  const login = (data) => {
    setUsuario(data);
    setVista('dashboard');
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout/');
    } finally {
      setUsuario(null);
      setEdificios([]);
      setEdificioId('');
    }
  };

  useEffect(() => {
    let activo = true;
    setUnauthorizedHandler(() => {
      if (activo) setUsuario(null);
    });
    api
      .get('/auth/csrf/')
      .then(() => api.get('/auth/me/'))
      .then((data) => {
        if (activo) setUsuario(data);
      })
      .catch((err) => {
        if (activo) {
          if (![401, 403].includes(err.status)) console.error(err);
          setUsuario(null);
        }
      });
    return () => {
      activo = false;
      setUnauthorizedHandler(() => {});
    };
  }, []);

  useEffect(() => {
    if (usuario?.rol !== 'Operador') return;
    api
      .get('/edificios/')
      .then((data) => {
        const items = Array.isArray(data) ? data : [];
        setEdificios(items);
        setEdificioId((prev) => prev || (items[0] ? String(items[0].id) : ''));
      })
      .catch((err) => console.error(err));
  }, [usuario]);

  const edificio = { edificios, edificioId, onEdificio: setEdificioId };

  if (usuario === undefined) {
    return <div className="login-wrap">Cargando sesión…</div>;
  }

  if (!usuario) {
    return <Login onLogin={login} />;
  }

  if (usuario.rol === 'Tecnico') {
    return (
      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand">
            <Shield size={18} strokeWidth={1.75} />
            <div>
              <h2>SGCA</h2>
              <span className="brand-sub">APL</span>
            </div>
          </div>
          <div className="sidebar-foot">
            <strong>{usuario.nombre}</strong>
            <span>Técnico</span>
            <button type="button" onClick={logout}>Salir</button>
          </div>
        </aside>
        <main className="content">
          <OrdenesTecnico />
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Shield size={18} strokeWidth={1.75} />
          <div>
            <h2>SGCA</h2>
            <span className="brand-sub">APL</span>
          </div>
        </div>
        <nav className="nav">
          {VISTAS_OPERADOR.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={vista === id ? 'active' : ''}
              onClick={() => setVista(id)}
            >
              <Icon size={16} strokeWidth={1.75} /> {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <strong>{usuario.nombre}</strong>
          <span>Operador · turno {usuario.turno_asignado}</span>
          <button type="button" onClick={logout}>
            Salir
          </button>
        </div>
      </aside>
      <main className="content">
        {vista === 'dashboard' && <Dashboard {...edificio} />}
        {vista === 'incidentes' && <Incidentes {...edificio} />}
        {vista === 'usuarios' && <Usuarios {...edificio} />}
        {vista === 'zonas' && <Zonas {...edificio} />}
        {vista === 'niveles' && <Niveles {...edificio} />}
        {vista === 'historial' && <Historial {...edificio} />}
        {vista === 'dispositivos' && <Dispositivos />}
        {vista === 'simulador' && <Simulador />}
      </main>
    </div>
  );
}
