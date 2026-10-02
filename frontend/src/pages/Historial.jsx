import { useEffect, useState } from 'react';
import { api, formatFecha } from '../api';
import EdificioSelect from '../EdificioSelect';
import PageHead from '../PageHead';

export default function Historial({ edificios, edificioId, onEdificio }) {
  const [registros, setRegistros] = useState([]);
  const [filtro, setFiltro] = useState('');

  useEffect(() => {
    if (!edificioId) return undefined;
    let activo = true;
    const params = new URLSearchParams({ edificio: edificioId });
    if (filtro) params.set('resultado', filtro);
    api.get(`/registros/?${params}`).then((data) => {
      if (activo) setRegistros(Array.isArray(data) ? data : []);
    }).catch((err) => alert(err.message));
    return () => {
      activo = false;
    };
  }, [edificioId, filtro]);

  return (
    <div>
      <PageHead
        kicker="Registro"
        title="Auditoría de entradas y salidas"
        lede="Historial completo de pases de este edificio, concedidos y denegados."
      />
      <EdificioSelect edificios={edificios} edificioId={edificioId} onChange={onEdificio} />
      <div className="panel">
        <div className="form-grid">
          <label>
            Resultado
            <select
              value={filtro}
              onChange={(e) => {
                setFiltro(e.target.value);
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
              <th>Sentido</th>
              <th>Persona</th>
              <th>Llave</th>
              <th>Tótem</th>
              <th>Resultado</th>
              <th>Motivo</th>
            </tr>
          </thead>
          <tbody>
            {registros.length === 0 ? (
              <tr>
                <td className="empty" colSpan="7">
                  Sin registros para este filtro.
                </td>
              </tr>
            ) : (
              registros.map((r) => (
                <tr key={r.id}>
                  <td>{formatFecha(r.fecha_hora)}</td>
                  <td>{r.sentido}</td>
                  <td>{r.persona_nombre || '—'}</td>
                  <td className="mono">{r.codigo_rfid || '—'}</td>
                  <td>{r.zona_nombre || '—'}</td>
                  <td>
                    <span
                      className={
                        r.resultado === 'concedido' ? 'badge badge-ok' : 'badge badge-bad'
                      }
                    >
                      {r.resultado}
                    </span>
                  </td>
                  <td className={r.motivo_rechazo ? '' : 'muted'}>{r.motivo_rechazo || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
