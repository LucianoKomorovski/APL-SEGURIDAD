import { useCallback, useEffect, useState } from 'react';
import { api, formatFecha } from '../api';
import EdificioSelect from '../EdificioSelect';
import PageHead from '../PageHead';

function lista(data) {
  return Array.isArray(data) ? data : [];
}

export default function Dashboard({ edificios, edificioId, onEdificio }) {
  const [alertasAbiertas, setAlertasAbiertas] = useState([]);
  const [alertasTodas, setAlertasTodas] = useState([]);
  const [listaAbierta, setListaAbierta] = useState(false);
  const [alertas, setAlertas] = useState([]);
  const [registros, setRegistros] = useState([]);
  const [controladores, setControladores] = useState([]);
  const [observaciones, setObservaciones] = useState('');

  const cargar = useCallback(async () => {
    const abiertas = lista(await api.get('/alertas/?abiertas=1'));
    setAlertasAbiertas(abiertas);
    if (listaAbierta) {
      setAlertasTodas(lista(await api.get('/alertas/')));
    }
    if (!edificioId) return;
    const q = `edificio=${edificioId}`;
    const [r, c, a] = await Promise.all([
      api.get(`/registros/?${q}&hoy=1`),
      api.get(`/controladores/?${q}`),
      api.get(`/alertas/?abiertas=1&${q}`),
    ]);
    setRegistros(lista(r));
    setControladores(lista(c));
    setAlertas(lista(a));
  }, [edificioId, listaAbierta]);

  useEffect(() => {
    let activo = true;
    const tick = () => {
      cargar().catch((err) => {
        if (activo) console.error(err);
      });
    };
    tick();
    const id = setInterval(tick, 2500);
    return () => {
      activo = false;
      clearInterval(id);
    };
  }, [cargar]);

  const conteos = edificios.map((ed) => ({
    id: ed.id,
    nombre: ed.nombre,
    abiertas: alertasAbiertas.filter((a) => String(a.edificio_id) === String(ed.id)).length,
  }));
  const maxAbiertas = Math.max(1, ...conteos.map((c) => c.abiertas));

  const entradas = registros.filter(
    (r) => r.sentido === 'Entrada' && r.resultado === 'concedido',
  ).length;
  const salidas = registros.filter(
    (r) => r.sentido === 'Salida' && r.resultado === 'concedido',
  ).length;
  const denegados = registros.filter((r) => r.resultado === 'rechazado').length;
  const enLinea = controladores.filter((c) => c.en_linea).length;
  const fueraDeLinea = controladores.length - enLinea;

  const resolver = async (id) => {
    try {
      await api.post(`/alertas/${id}/resolver/`, {
        observaciones: observaciones || 'Resuelta desde el panel operativo.',
      });
      setObservaciones('');
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <PageHead
        kicker="Operación"
        title="Entradas y salidas en vivo"
        lede="Elegí un edificio para ver los movimientos del día y las alertas pendientes."
      />

      <button
        type="button"
        className={`alerta-grafico${listaAbierta ? ' abierto' : ''}`}
        aria-expanded={listaAbierta}
        onClick={() => setListaAbierta((abierta) => !abierta)}
      >
        <span className="alerta-grafico-titulo">
          Alertas sin resolver · todos los edificios
          <span className="alerta-grafico-accion">{listaAbierta ? 'Cerrar lista' : 'Ver todas'}</span>
        </span>
        {conteos.length === 0 ? (
          <span className="alerta-vacio">Sin edificios.</span>
        ) : (
          conteos.map((fila) => (
            <span className="alerta-fila" key={fila.id}>
              <span className="alerta-nombre">{fila.nombre}</span>
              <span className="alerta-barra" aria-hidden="true">
                <span style={{ width: `${(fila.abiertas / maxAbiertas) * 100}%` }} />
              </span>
              <span className={fila.abiertas > 0 ? 'alerta-cuenta bad' : 'alerta-cuenta'}>
                {fila.abiertas}
              </span>
            </span>
          ))
        )}
      </button>

      {listaAbierta && (
        <div className="panel alerta-lista">
          <h2>Todas las alertas</h2>
          <label>
            Observación al resolver
            <input
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              placeholder="Ej: el guardia del tótem confirmó identidad"
            />
          </label>
          <TablaAlertas alertas={alertasTodas} onResolver={resolver} mostrarEdificio />
        </div>
      )}

      <EdificioSelect edificios={edificios} edificioId={edificioId} onChange={onEdificio} />

      <div className="metrics">
        <div className="metric">
          <span>Entradas de hoy</span>
          <strong>{entradas}</strong>
        </div>
        <div className="metric">
          <span>Salidas de hoy</span>
          <strong>{salidas}</strong>
        </div>
        <div className="metric">
          <span>Denegados de hoy</span>
          <strong className={denegados > 0 ? 'bad' : ''}>{denegados}</strong>
        </div>
        <div className="metric">
          <span>Tótems en línea</span>
          <strong className={fueraDeLinea > 0 ? 'bad' : ''}>
            {enLinea}/{controladores.length}
          </strong>
        </div>
      </div>

      <div className="panel">
        <h2>Movimientos de hoy</h2>
        <table>
          <thead>
            <tr>
              <th>Hora</th>
              <th>Sentido</th>
              <th>Cliente</th>
              <th>Llave</th>
              <th>Tótem</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {registros.length === 0 ? (
              <tr>
                <td className="empty" colSpan="6">
                  Hoy no hay pases en este edificio.
                </td>
              </tr>
            ) : (
              registros.map((reg) => (
                <tr key={reg.id}>
                  <td>{formatFecha(reg.fecha_hora)}</td>
                  <td>{reg.sentido}</td>
                  <td>{reg.persona_nombre || '—'}</td>
                  <td className="mono">{reg.codigo_rfid || '—'}</td>
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
        <h2>Alertas sin resolver ({alertas.length})</h2>
        <label>
          Observación al resolver
          <input
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            placeholder="Ej: el guardia del tótem confirmó identidad"
          />
        </label>
        <TablaAlertas alertas={alertas} onResolver={resolver} />
      </div>
    </div>
  );
}

function TablaAlertas({ alertas, onResolver, mostrarEdificio = false }) {
  const columnas = mostrarEdificio ? 7 : 6;
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          {mostrarEdificio ? <th>Edificio</th> : null}
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
            <td className="empty" colSpan={columnas}>
              Sin alertas.
            </td>
          </tr>
        ) : (
          alertas.map((alerta) => (
            <tr key={alerta.id}>
              <td>#{alerta.id}</td>
              {mostrarEdificio ? <td>{alerta.edificio_nombre || '—'}</td> : null}
              <td>{alerta.tipo_alerta}</td>
              <td>{alerta.zona_nombre || alerta.dispositivo_ip}</td>
              <td>{alerta.nivel_gravedad}</td>
              <td>
                <span
                  className={
                    alerta.estado_atencion === 'Resuelta' ? 'badge badge-ok' : 'badge badge-bad'
                  }
                >
                  {alerta.estado_atencion}
                </span>
              </td>
              <td>
                {alerta.estado_atencion !== 'Resuelta' ? (
                  <button className="btn btn-primary" type="button" onClick={() => onResolver(alerta.id)}>
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
  );
}
