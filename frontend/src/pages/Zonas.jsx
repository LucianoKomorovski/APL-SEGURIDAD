import { useEffect, useState } from 'react';
import { api, armarArbolZonas } from '../api';
import EdificioSelect from '../EdificioSelect';
import PageHead from '../PageHead';

function agruparPorEdificio(raices) {
  const grupos = new Map();
  raices.forEach((zona) => {
    const nombre = zona.edificio_nombre || 'Sin edificio';
    if (!grupos.has(nombre)) grupos.set(nombre, []);
    grupos.get(nombre).push(zona);
  });
  return [...grupos.entries()];
}

function Fila({ zona, depth }) {
  return (
    <>
      <div className="zona-row" style={{ '--depth': depth }}>
        <span className="zona-nombre">{zona.nombre_zona}</span>
        <span className="zona-nivel">{zona.nivel_seguridad}</span>
      </div>
      {zona.hijos?.map((hijo) => (
        <Fila key={hijo.id} zona={hijo} depth={depth + 1} />
      ))}
    </>
  );
}

export default function Zonas({ edificios, edificioId, onEdificio }) {
  const [zonas, setZonas] = useState([]);
  const [puntos, setPuntos] = useState([]);
  const [zonaForm, setZonaForm] = useState({
    nombre_zona: '',
    nivel_seguridad: 'Media',
    zona_padre: '',
  });
  const [puntoForm, setPuntoForm] = useState({
    descripcion: '',
    ubicacion_fisica: '',
    zona: '',
    sentido: 'Entrada',
    tipo: 'Totem',
  });

  const cargar = async () => {
    if (!edificioId) return;
    const q = `?edificio=${edificioId}`;
    const [z, p] = await Promise.all([api.get(`/zonas/${q}`), api.get(`/puntos-acceso/${q}`)]);
    const listaZonas = Array.isArray(z) ? z : [];
    setZonas(listaZonas);
    setPuntos(Array.isArray(p) ? p : []);
    setPuntoForm((prev) => ({
      ...prev,
      zona: listaZonas.some((zona) => String(zona.id) === String(prev.zona))
        ? prev.zona
        : listaZonas[0]?.id || '',
    }));
  };

  useEffect(() => {
    if (!edificioId) return undefined;
    let activo = true;
    const q = `?edificio=${edificioId}`;
    Promise.all([api.get(`/zonas/${q}`), api.get(`/puntos-acceso/${q}`)]).then(([z, p]) => {
      if (!activo) return;
      const listaZonas = Array.isArray(z) ? z : [];
      setZonas(listaZonas);
      setPuntos(Array.isArray(p) ? p : []);
      setPuntoForm((prev) => ({
        ...prev,
        zona: listaZonas.some((zona) => String(zona.id) === String(prev.zona))
          ? prev.zona
          : listaZonas[0]?.id || '',
      }));
    }).catch((err) => alert(err.message));
    return () => {
      activo = false;
    };
  }, [edificioId]);

  const crearZona = async (e) => {
    e.preventDefault();
    await api.post('/zonas/', {
      nombre_zona: zonaForm.nombre_zona,
      nivel_seguridad: zonaForm.nivel_seguridad,
      zona_padre: zonaForm.zona_padre ? Number(zonaForm.zona_padre) : null,
      edificio: Number(edificioId),
    });
    setZonaForm((prev) => ({ ...prev, nombre_zona: '' }));
    await cargar();
  };

  const crearPunto = async (e) => {
    e.preventDefault();
    await api.post('/puntos-acceso/', {
      ...puntoForm,
      zona: Number(puntoForm.zona),
      tiene_camara: puntoForm.tipo === 'Totem',
    });
    setPuntoForm((prev) => ({ ...prev, descripcion: '', ubicacion_fisica: '' }));
    await cargar();
  };

  const grupos = agruparPorEdificio(armarArbolZonas(zonas));

  return (
    <div>
      <PageHead
        kicker="Planta"
        title="Zonas por edificio"
        lede="Jerarquía de zonas y puntos de acceso de este edificio. Un padre cubre a las zonas que contiene."
      />
      <EdificioSelect edificios={edificios} edificioId={edificioId} onChange={onEdificio} />
      <div className="panel">
        <h2>Mapa de planta</h2>
        {grupos.length === 0 ? (
          <p className="empty">Todavía no hay zonas.</p>
        ) : (
          grupos.map(([edificio, raices]) => (
            <section key={edificio}>
              <p className="planta-edificio">{edificio}</p>
              {raices.map((zona) => (
                <Fila key={zona.id} zona={zona} depth={0} />
              ))}
            </section>
          ))
        )}
      </div>

      <div className="panel">
        <h2>Nueva zona</h2>
        <form className="form-grid" onSubmit={crearZona}>
          <label>
            Nombre
            <input
              value={zonaForm.nombre_zona}
              onChange={(e) => setZonaForm({ ...zonaForm, nombre_zona: e.target.value })}
              required
            />
          </label>
          <label>
            Seguridad
            <select
              value={zonaForm.nivel_seguridad}
              onChange={(e) => setZonaForm({ ...zonaForm, nivel_seguridad: e.target.value })}
            >
              <option>Baja</option>
              <option>Media</option>
              <option>Alta</option>
            </select>
          </label>
          <label>
            Zona padre
            <select
              value={zonaForm.zona_padre}
              onChange={(e) => setZonaForm({ ...zonaForm, zona_padre: e.target.value })}
            >
              <option value="">(raíz)</option>
              {zonas.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.nombre_zona}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn-primary" type="submit">
            Crear zona
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Tótem / puerta</h2>
        <form className="form-grid" onSubmit={crearPunto}>
          <label>
            Descripción
            <input
              value={puntoForm.descripcion}
              onChange={(e) => setPuntoForm({ ...puntoForm, descripcion: e.target.value })}
              required
            />
          </label>
          <label>
            Ubicación
            <input
              value={puntoForm.ubicacion_fisica}
              onChange={(e) => setPuntoForm({ ...puntoForm, ubicacion_fisica: e.target.value })}
              required
            />
          </label>
          <label>
            Zona
            <select
              value={puntoForm.zona}
              onChange={(e) => setPuntoForm({ ...puntoForm, zona: e.target.value })}
            >
              {zonas.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.nombre_zona}
                </option>
              ))}
            </select>
          </label>
          <label>
            Sentido
            <select
              value={puntoForm.sentido}
              onChange={(e) => setPuntoForm({ ...puntoForm, sentido: e.target.value })}
            >
              <option>Entrada</option>
              <option>Salida</option>
            </select>
          </label>
          <label>
            Tipo
            <select
              value={puntoForm.tipo}
              onChange={(e) => setPuntoForm({ ...puntoForm, tipo: e.target.value })}
            >
              <option value="Totem">Tótem con cámara</option>
              <option value="Lector">Lector de puerta</option>
            </select>
          </label>
          <button className="btn btn-primary" type="submit">
            Crear punto
          </button>
        </form>
        <table>
          <thead>
            <tr>
              <th>Punto</th>
              <th>Sentido</th>
              <th>Tipo</th>
              <th>Zona</th>
            </tr>
          </thead>
          <tbody>
            {puntos.length === 0 ? (
              <tr>
                <td className="empty" colSpan="4">
                  Todavía no hay puntos de acceso.
                </td>
              </tr>
            ) : null}
            {puntos.map((p) => (
              <tr key={p.id}>
                <td>{p.descripcion}</td>
                <td>{p.sentido}</td>
                <td>{p.tipo}</td>
                <td>{p.zona_nombre}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
