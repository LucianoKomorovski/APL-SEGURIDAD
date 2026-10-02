import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, formatFecha } from '../api';
import EdificioSelect from '../EdificioSelect';
import PageHead from '../PageHead';

const FORM_INICIAL = {
  descripcion: '',
  categoria: 'Hardware',
  prioridad: 'Media',
  dispositivo: '',
  alerta_origen: '',
  incidente_anterior: '',
};

const lista = (valor) => (Array.isArray(valor) ? valor : valor?.results || []);

function estadoClase(estado) {
  if (['Cerrado', 'Verificada'].includes(estado)) return 'badge badge-ok';
  if (['Descartado', 'Cancelada'].includes(estado)) return 'badge badge-muted';
  if (['Pendiente verificacion', 'Informada'].includes(estado)) return 'badge badge-warn';
  return 'badge';
}

export default function Incidentes({ edificios, edificioId, onEdificio }) {
  const [incidentes, setIncidentes] = useState([]);
  const [dispositivos, setDispositivos] = useState([]);
  const [alertas, setAlertas] = useState([]);
  const [tecnicos, setTecnicos] = useState([]);
  const [asignaciones, setAsignaciones] = useState({});
  const [form, setForm] = useState(FORM_INICIAL);
  const [filtro, setFiltro] = useState('');
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    if (!edificioId) return;
    try {
      const [inc, disp, alert, tec] = await Promise.all([
        api.get(`/incidentes/?edificio=${edificioId}`),
        api.get(`/controladores/?edificio=${edificioId}`),
        api.get(`/alertas/?edificio=${edificioId}&abiertas=1`),
        api.get('/tecnicos/'),
      ]);
      setIncidentes(lista(inc));
      setDispositivos(lista(disp));
      setAlertas(lista(alert).filter((item) => !item.incidente_tecnico_id));
      setTecnicos(lista(tec));
    } catch (err) {
      setError(err.message);
    }
  }, [edificioId]);

  useEffect(() => {
    if (!edificioId) return undefined;
    let activo = true;
    Promise.all([
      api.get(`/incidentes/?edificio=${edificioId}`),
      api.get(`/controladores/?edificio=${edificioId}`),
      api.get(`/alertas/?edificio=${edificioId}&abiertas=1`),
      api.get('/tecnicos/'),
    ]).then(([inc, disp, alert, tec]) => {
      if (!activo) return;
      setIncidentes(lista(inc));
      setDispositivos(lista(disp));
      setAlertas(lista(alert).filter((item) => !item.incidente_tecnico_id));
      setTecnicos(lista(tec));
    }).catch((err) => {
      if (activo) setError(err.message);
    });
    return () => {
      activo = false;
    };
  }, [edificioId]);

  const visibles = useMemo(
    () => (filtro ? incidentes.filter((item) => item.estado === filtro) : incidentes),
    [filtro, incidentes],
  );

  const ejecutar = async (ruta, datos = {}) => {
    setError('');
    try {
      await api.post(ruta, datos);
      await cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const registrar = async (event) => {
    event.preventDefault();
    setError('');
    const datos = { ...form, edificio: Number(edificioId) };
    ['dispositivo', 'alerta_origen', 'incidente_anterior'].forEach((campo) => {
      if (datos[campo]) datos[campo] = Number(datos[campo]);
      else delete datos[campo];
    });
    try {
      await api.post('/incidentes/', datos);
      setForm(FORM_INICIAL);
      await cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const elegirAlerta = (valor) => {
    const alerta = alertas.find((item) => String(item.id) === valor);
    setForm((actual) => ({
      ...actual,
      alerta_origen: valor,
      dispositivo: alerta ? String(alerta.dispositivo) : actual.dispositivo,
    }));
  };

  const pedir = (mensaje) => window.prompt(mensaje)?.trim() || '';

  return (
    <>
      <PageHead
        kicker="Servicio técnico"
        title="Incidentes e intervenciones"
        lede="Registro, asignación y verificación del trabajo técnico. Las alertas mantienen su atención independiente."
      />
      <EdificioSelect edificios={edificios} edificioId={edificioId} onChange={onEdificio} />

      <section className="panel">
        <h2>Registrar incidente</h2>
        <form onSubmit={registrar}>
          <div className="form-grid incident-form">
            <label className="field-wide">
              Descripción
              <textarea
                required
                value={form.descripcion}
                onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              />
            </label>
            <label>
              Categoría
              <select
                value={form.categoria}
                onChange={(e) => setForm({ ...form, categoria: e.target.value })}
              >
                {['Hardware', 'Conectividad', 'Energia', 'Otro'].map((valor) => (
                  <option key={valor} value={valor}>{valor === 'Energia' ? 'Energía' : valor}</option>
                ))}
              </select>
            </label>
            <label>
              Prioridad
              <select
                value={form.prioridad}
                onChange={(e) => setForm({ ...form, prioridad: e.target.value })}
              >
                {['Baja', 'Media', 'Alta', 'Critica'].map((valor) => (
                  <option key={valor} value={valor}>{valor === 'Critica' ? 'Crítica' : valor}</option>
                ))}
              </select>
            </label>
            <label>
              Dispositivo (opcional)
              <select
                value={form.dispositivo}
                onChange={(e) => setForm({ ...form, dispositivo: e.target.value })}
              >
                <option value="">Sin dispositivo</option>
                {dispositivos.map((item) => (
                  <option key={item.id} value={item.id}>{item.numero_serie}</option>
                ))}
              </select>
            </label>
            <label>
              Alerta de origen (opcional)
              <select value={form.alerta_origen} onChange={(e) => elegirAlerta(e.target.value)}>
                <option value="">Registro manual</option>
                {alertas.map((item) => (
                  <option key={item.id} value={item.id}>#{item.id} · {item.tipo_alerta}</option>
                ))}
              </select>
            </label>
            <label>
              Incidente anterior (opcional)
              <select
                value={form.incidente_anterior}
                onChange={(e) => setForm({ ...form, incidente_anterior: e.target.value })}
              >
                <option value="">Sin antecedente</option>
                {incidentes.filter((item) => item.estado === 'Cerrado').map((item) => (
                  <option key={item.id} value={item.id}>#{item.id} · {item.descripcion}</option>
                ))}
              </select>
            </label>
          </div>
          <button className="btn btn-primary" type="submit" disabled={!edificioId}>
            Registrar
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Incidentes</h2>
          <label>
            Estado
            <select value={filtro} onChange={(e) => setFiltro(e.target.value)}>
              <option value="">Todos</option>
              {['Registrado', 'Evaluado', 'En atencion', 'Pendiente verificacion', 'Cerrado', 'Descartado'].map((estado) => (
                <option key={estado} value={estado}>{estado}</option>
              ))}
            </select>
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        {!visibles.length && <p className="empty">No hay incidentes para mostrar.</p>}
        <div className="incident-list">
          {visibles.map((incidente) => (
            <article className="incident-card" key={incidente.id}>
              <header>
                <div>
                  <strong>#{incidente.id} · {incidente.descripcion}</strong>
                  <p>
                    {incidente.categoria} · {incidente.prioridad} · {formatFecha(incidente.fecha_registro)}
                  </p>
                </div>
                <span className={estadoClase(incidente.estado)}>{incidente.estado}</span>
              </header>
              <p className="field-note">
                {incidente.dispositivo_serie && `Dispositivo ${incidente.dispositivo_serie}. `}
                {incidente.alerta_origen && `Derivado de alerta #${incidente.alerta_origen}: ${incidente.alerta_tipo}. `}
                {incidente.incidente_anterior && `Posterior al incidente #${incidente.incidente_anterior}.`}
              </p>
              <div className="actions">
                {incidente.estado === 'Registrado' && (
                  <button className="btn-text" onClick={() => ejecutar(`/incidentes/${incidente.id}/evaluar/`)}>
                    Evaluar
                  </button>
                )}
                {['Registrado', 'Evaluado'].includes(incidente.estado) && (
                  <button
                    className="btn-text danger"
                    onClick={() => {
                      const motivo = pedir('Motivo del descarte');
                      if (motivo) ejecutar(`/incidentes/${incidente.id}/descartar/`, { motivo });
                    }}
                  >
                    Descartar
                  </button>
                )}
                {incidente.estado === 'Evaluado' && (
                  <>
                    <select
                      aria-label={`Técnico para incidente ${incidente.id}`}
                      value={asignaciones[`i${incidente.id}`] || ''}
                      onChange={(e) => setAsignaciones({ ...asignaciones, [`i${incidente.id}`]: e.target.value })}
                    >
                      <option value="">Seleccionar técnico</option>
                      {tecnicos.map((tecnico) => (
                        <option key={tecnico.id} value={tecnico.id}>{tecnico.nombre}</option>
                      ))}
                    </select>
                    <button
                      className="btn-text"
                      disabled={!asignaciones[`i${incidente.id}`]}
                      onClick={() => ejecutar(`/incidentes/${incidente.id}/asignar/`, {
                        tecnico: Number(asignaciones[`i${incidente.id}`]),
                      })}
                    >
                      Asignar intervención
                    </button>
                  </>
                )}
                {incidente.estado === 'Pendiente verificacion'
                  && incidente.ordenes.some((orden) => orden.estado === 'Verificada' && orden.verificacion_aceptada)
                  && (
                    <button className="btn-text" onClick={() => ejecutar(`/incidentes/${incidente.id}/cerrar/`)}>
                      Cerrar incidente
                    </button>
                  )}
              </div>

              {incidente.ordenes.map((orden) => (
                <div className="order-row" key={orden.id}>
                  <div>
                    <strong>Orden {orden.numero}</strong> · {orden.tecnico_nombre} ·{' '}
                    <span className={estadoClase(orden.estado)}>{orden.estado}</span>
                    {orden.resultado && <p>Resultado: {orden.resultado}</p>}
                    {orden.diagnostico && <p>Diagnóstico: {orden.diagnostico}</p>}
                    {orden.trabajo_realizado && <p>Trabajo: {orden.trabajo_realizado}</p>}
                    {orden.observaciones_verificacion && (
                      <p>Verificación: {orden.observaciones_verificacion}</p>
                    )}
                  </div>
                  <div className="actions">
                    {orden.estado === 'Informada' && (
                      <>
                        {orden.resultado === 'solucionado' && (
                          <button
                            className="btn-text"
                            onClick={() => {
                              const observaciones = pedir('Observaciones de la verificación satisfactoria');
                              if (observaciones) ejecutar(`/ordenes/${orden.id}/verificar/`, { aceptada: true, observaciones });
                            }}
                          >Aceptar</button>
                        )}
                        <button
                          className="btn-text danger"
                          onClick={() => {
                            const observaciones = pedir('Observaciones del rechazo');
                            if (observaciones) ejecutar(`/ordenes/${orden.id}/verificar/`, { aceptada: false, observaciones });
                          }}
                        >Rechazar</button>
                      </>
                    )}
                    {['Asignada', 'En curso'].includes(orden.estado) && (
                      <>
                        <select
                          aria-label={`Nuevo técnico para orden ${orden.id}`}
                          value={asignaciones[`o${orden.id}`] || ''}
                          onChange={(e) => setAsignaciones({ ...asignaciones, [`o${orden.id}`]: e.target.value })}
                        >
                          <option value="">Reasignar a…</option>
                          {tecnicos.filter((tec) => tec.id !== orden.tecnico).map((tec) => (
                            <option key={tec.id} value={tec.id}>{tec.nombre}</option>
                          ))}
                        </select>
                        <button
                          className="btn-text"
                          disabled={!asignaciones[`o${orden.id}`]}
                          onClick={() => {
                            const motivo = pedir('Motivo de la reasignación');
                            if (motivo) ejecutar(`/ordenes/${orden.id}/reasignar/`, {
                              tecnico: Number(asignaciones[`o${orden.id}`]), motivo,
                            });
                          }}
                        >Reasignar</button>
                        <button
                          className="btn-text danger"
                          onClick={() => {
                            const motivo = pedir('Motivo de la cancelación');
                            if (motivo) ejecutar(`/ordenes/${orden.id}/cancelar/`, { motivo });
                          }}
                        >Cancelar</button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
