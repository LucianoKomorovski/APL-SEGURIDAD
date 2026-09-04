import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, Radio } from 'lucide-react';
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
      setRegistros(Array.isArray(r) ? r.slice(0, 8) : []);
      setControladores(Array.isArray(c) ? c : []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    cargar();
    const id = setInterval(cargar, 3000);
    return () => clearInterval(id);
  }, []);

  const pendientes = alertas.filter((a) => a.estado_atencion !== 'Resuelta').length;
  const resueltas = alertas.filter((a) => a.estado_atencion === 'Resuelta').length;
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
      <h1>Sala de monitoreo</h1>
      <div className="cards">
        <div className="card bad">
          <h3>
            <AlertTriangle size={16} color="#ef4444" /> Alertas abiertas
          </h3>
          <p>{pendientes}</p>
        </div>
        <div className="card ok">
          <h3>
            <CheckCircle size={16} color="#22c55e" /> Resueltas
          </h3>
          <p>{resueltas}</p>
        </div>
        <div className="card info">
          <h3>
            <Radio size={16} color="#3b82f6" /> Controladores en línea
          </h3>
          <p>
            {enLinea}/{controladores.length}
          </p>
        </div>
      </div>

      <div className="panel">
        <h2>Alertas de seguridad</h2>
        <label>
          Observación al resolver
          <input
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            placeholder="Ej: se verificó la puerta, sin novedad"
          />
        </label>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Tipo</th>
              <th>Zona</th>
              <th>Gravedad</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {alertas.length === 0 ? (
              <tr>
                <td colSpan="6">No hay alertas.</td>
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

      <div className="panel">
        <h2>Últimos pases</h2>
        <table>
          <thead>
            <tr>
              <th>Hora</th>
              <th>Persona</th>
              <th>Tag</th>
              <th>Zona</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {registros.map((reg) => (
              <tr key={reg.id}>
                <td>{formatFecha(reg.fecha_hora)}</td>
                <td>{reg.persona_nombre || '—'}</td>
                <td>{reg.codigo_rfid || '—'}</td>
                <td>{reg.zona_nombre || '—'}</td>
                <td>
                  <span
                    className={
                      reg.resultado === 'concedido' ? 'badge badge-ok' : 'badge badge-bad'
                    }
                  >
                    {reg.resultado}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
