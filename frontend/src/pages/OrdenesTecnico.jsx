import { useCallback, useEffect, useState } from 'react';
import { api, formatFecha } from '../api';
import PageHead from '../PageHead';

const INFORME_INICIAL = {
  diagnostico: '',
  trabajo_realizado: '',
  resultado: 'solucionado',
};

const lista = (valor) => (Array.isArray(valor) ? valor : valor?.results || []);

export default function OrdenesTecnico() {
  const [ordenes, setOrdenes] = useState([]);
  const [informes, setInformes] = useState({});
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    try {
      setOrdenes(lista(await api.get('/ordenes/')));
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    let activo = true;
    api.get('/ordenes/').then((datos) => {
      if (activo) setOrdenes(lista(datos));
    }).catch((err) => {
      if (activo) setError(err.message);
    });
    return () => {
      activo = false;
    };
  }, []);

  const iniciar = async (id) => {
    setError('');
    try {
      await api.post(`/ordenes/${id}/iniciar/`);
      await cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const informe = (id) => informes[id] || INFORME_INICIAL;
  const cambiarInforme = (id, campo, valor) => {
    setInformes({ ...informes, [id]: { ...informe(id), [campo]: valor } });
  };

  const informar = async (event, orden) => {
    event.preventDefault();
    setError('');
    try {
      await api.post(`/ordenes/${orden.id}/informar/`, informe(orden.id));
      setInformes((actual) => {
        const copia = { ...actual };
        delete copia[orden.id];
        return copia;
      });
      await cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <PageHead
        kicker="Servicio técnico"
        title="Mis órdenes"
        lede="Iniciá la intervención asignada y presentá el diagnóstico, el trabajo y el resultado."
      />
      {error && <p className="error">{error}</p>}
      {!ordenes.length && <div className="panel"><p className="empty">No tenés órdenes asignadas.</p></div>}
      <div className="incident-list">
        {ordenes.map((orden) => (
          <article className="incident-card" key={orden.id}>
            <header>
              <div>
                <strong>Orden {orden.incidente}.{orden.numero} · {orden.edificio_nombre}</strong>
                <p>{orden.incidente_descripcion}</p>
              </div>
              <span className="badge">{orden.estado}</span>
            </header>
            <p className="field-note">Asignada {formatFecha(orden.fecha_asignacion)}</p>
            {orden.estado === 'Asignada' && (
              <button className="btn btn-primary" onClick={() => iniciar(orden.id)}>
                Iniciar trabajo
              </button>
            )}
            {orden.estado === 'En curso' && (
              <form className="technical-report" onSubmit={(event) => informar(event, orden)}>
                <label>
                  Diagnóstico
                  <textarea
                    required
                    value={informe(orden.id).diagnostico}
                    onChange={(e) => cambiarInforme(orden.id, 'diagnostico', e.target.value)}
                  />
                </label>
                <label>
                  Trabajo realizado
                  <textarea
                    required
                    value={informe(orden.id).trabajo_realizado}
                    onChange={(e) => cambiarInforme(orden.id, 'trabajo_realizado', e.target.value)}
                  />
                </label>
                <label>
                  Resultado
                  <select
                    value={informe(orden.id).resultado}
                    onChange={(e) => cambiarInforme(orden.id, 'resultado', e.target.value)}
                  >
                    <option value="solucionado">Solucionado</option>
                    <option value="parcialmente solucionado">Parcialmente solucionado</option>
                    <option value="no solucionado">No solucionado</option>
                  </select>
                </label>
                <button className="btn btn-primary" type="submit">Presentar informe</button>
              </form>
            )}
            {orden.diagnostico && (
              <div className="order-report">
                <p><strong>Diagnóstico:</strong> {orden.diagnostico}</p>
                <p><strong>Trabajo:</strong> {orden.trabajo_realizado}</p>
                <p><strong>Resultado:</strong> {orden.resultado}</p>
                {orden.observaciones_verificacion && (
                  <p><strong>Verificación:</strong> {orden.observaciones_verificacion}</p>
                )}
              </div>
            )}
          </article>
        ))}
      </div>
    </>
  );
}
