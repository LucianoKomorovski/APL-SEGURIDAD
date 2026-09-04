import { useEffect, useState } from 'react';
import { api, formatFecha } from '../api';

export default function Historial() {
  const [registros, setRegistros] = useState([]);
  const [filtro, setFiltro] = useState('');

  const cargar = async (resultado = filtro) => {
    const qs = resultado ? `?resultado=${resultado}` : '';
    const data = await api.get(`/registros/${qs}`);
    setRegistros(Array.isArray(data) ? data : []);
  };

  useEffect(() => {
    cargar('').catch((err) => alert(err.message));
  }, []);

  return (
    <div>
      <h1>Auditoría de pases</h1>
      <div className="panel">
        <div className="form-grid">
          <label>
            Resultado
            <select
              value={filtro}
              onChange={(e) => {
                setFiltro(e.target.value);
                cargar(e.target.value);
              }}
            >
              <option value="">Todos</option>
              <option value="concedido">Concedidos</option>
              <option value="rechazado">Rechazados</option>
            </select>
          </label>
        </div>
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Persona</th>
              <th>Tag</th>
              <th>Zona</th>
              <th>IP</th>
              <th>Resultado</th>
              <th>Motivo</th>
            </tr>
          </thead>
          <tbody>
            {registros.map((r) => (
              <tr key={r.id}>
                <td>{formatFecha(r.fecha_hora)}</td>
                <td>{r.persona_nombre || '—'}</td>
                <td>{r.codigo_rfid || '—'}</td>
                <td>{r.zona_nombre || '—'}</td>
                <td>{r.dispositivo_ip || '—'}</td>
                <td>
                  <span
                    className={
                      r.resultado === 'concedido' ? 'badge badge-ok' : 'badge badge-bad'
                    }
                  >
                    {r.resultado}
                  </span>
                </td>
                <td>{r.motivo_rechazo || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
