import { useEffect, useState } from 'react';
import { LogIn, LogOut, Ban, Radio } from 'lucide-react';
import { api, formatFecha } from '../api';

export default function Dashboard({ operador }) {
  const [alertas, setAlertas] = useState([]);
  const [registros, setRegistros] = useState([]);
  const [controladores, setControladores] = useState([]);
  const [observaciones, setObservaciones] = useState('');

  const cargar = async () => {
    try {
      const [a, r, c] = await Promise.all([
        api.get('/alertas/'),
        api.get('/registros/'),
        api.get('/controladores/'),
      ]);
      setAlertas(Array.isArray(a) ? a : []);
      setRegistros(Array.isArray(r) ? r.slice(0, 25) : []);
      setControladores(Array.isArray(c) ? c : []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    cargar();
    const id = setInterval(cargar, 2500);
    return () => clearInterval(id);
  }, []);

  const pendientes = alertas.filter((a) => a.estado_atencion !== 'Resuelta').length;
  const entradas = registros.filter(
    (r) => r.sentido === 'Entrada' && r.resultado === 'concedido',
  ).length;
  const salidas = registros.filter(
    (r) => r.sentido === 'Salida' && r.resultado === 'concedido',
  ).length;
  const denegados = registros.filter((r) => r.resultado === 'rechazado').length;
  const enLinea = controladores.filter((c) => c.en_linea).length;

  const resolver = async (id) => {
    try {
      await api.post(`/alertas/${id}/resolver/`, {
        observaciones: observaciones || 'Resuelta desde el panel operativo.',
        operador: operador?.id,
      });
      setObservaciones('');
      cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <h1>Entradas y salidas en vivo</h1>
      <p style={{ color: '#64748b', marginTop: 0 }}>
        Operador APL: pases de todos los edificios. El tótem con cámara y el guardia
        están en la puerta; acá se ve el movimiento.
      </p>
      <div className="cards">
        <div className="card ok">
          <h3>
            <LogIn size={16} color="#22c55e" /> Entradas
          </h3>
          <p>{entradas}</p>
        </div>
        <div className="card info">
          <h3>
            <LogOut size={16} color="#3b82f6" /> Salidas
          </h3>
          <p>{salidas}</p>
        </div>
        <div className="card bad">
          <h3>
            <Ban size={16} color="#ef4444" /> Denegados
          </h3>
          <p>{denegados}</p>
        </div>
        <div className="card warn">
          <h3>
            <Radio size={16} color="#f59e0b" /> Tótems en línea
          </h3>
          <p>
            {enLinea}/{controladores.length}
          </p>
        </div>
      </div>

      <div className="panel">
        <h2>Últimos movimientos</h2>
        <table>
          <thead>
            <tr>
              <th>Hora</th>
              <th>Sentido</th>
              <th>Cliente</th>
              <th>Llave</th>
              <th>Edificio</th>
              <th>Tótem</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {registros.length === 0 ? (
              <tr>
                <td colSpan="7">Todavía no hay pases. Usá el tótem virtual para generarlos.</td>
              </tr>
            ) : (
              registros.map((reg) => (
                <tr key={reg.id}>
                  <td>{formatFecha(reg.fecha_hora)}</td>
                  <td>
                    <span
                      className={
                        reg.sentido === 'Salida' ? 'badge badge-muted' : 'badge badge-ok'
                      }
                    >
                      {reg.sentido}
                    </span>
                  </td>
                  <td>{reg.persona_nombre || '—'}</td>
                  <td>{reg.codigo_rfid || '—'}</td>
                  <td>{reg.edificio_nombre || '—'}</td>
                  <td>{reg.zona_nombre || '—'}</td>
                  <td>
                    <span
                      className={
                        reg.resultado === 'concedido' ? 'badge badge-ok' : 'badge badge-bad'
                      }
                    >
                      {reg.resultado === 'concedido' ? 'Abrió' : 'Denegó'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2>Incidentes ({pendientes} abiertos)</h2>
        <label>
          Observación al resolver
          <input
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            placeholder="Ej: el guardia del tótem confirmó identidad"
          />
        </label>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Tipo</th>
              <th>Lugar</th>
              <th>Gravedad</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {alertas.length === 0 ? (
              <tr>
                <td colSpan="6">Sin incidentes.</td>
              </tr>
            ) : (
              alertas.map((alerta) => (
                <tr key={alerta.id}>
                  <td>#{alerta.id}</td>
                  <td>{alerta.tipo_alerta}</td>
                  <td>{alerta.zona_nombre || alerta.dispositivo_ip}</td>
                  <td>{alerta.nivel_gravedad}</td>
                  <td>
                    <span
                      className={
                        alerta.estado_atencion === 'Resuelta'
                          ? 'badge badge-ok'
                          : 'badge badge-bad'
                      }
                    >
                      {alerta.estado_atencion}
                    </span>
                  </td>
                  <td>
                    {alerta.estado_atencion !== 'Resuelta' ? (
                      <button className="btn btn-primary" onClick={() => resolver(alerta.id)}>
                        Resolver
                      </button>
                    ) : (
                      <span className="badge badge-muted">Cerrada</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
