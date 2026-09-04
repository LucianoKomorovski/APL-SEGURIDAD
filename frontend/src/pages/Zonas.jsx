import { useEffect, useState } from 'react';
import { api, armarArbolZonas } from '../api';

function Nodo({ zona }) {
  return (
    <li>
      <strong>{zona.nombre_zona}</strong>{' '}
      <span className="badge badge-muted">{zona.nivel_seguridad}</span>
      {zona.hijos?.length > 0 && (
        <ul className="tree">
          {zona.hijos.map((h) => (
            <Nodo key={h.id} zona={h} />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function Zonas() {
  const [zonas, setZonas] = useState([]);
  const [edificios, setEdificios] = useState([]);
  const [puntos, setPuntos] = useState([]);
  const [zonaForm, setZonaForm] = useState({
    nombre_zona: '',
    nivel_seguridad: 'Media',
    zona_padre: '',
    edificio: '',
  });
  const [puntoForm, setPuntoForm] = useState({
    descripcion: '',
    ubicacion_fisica: '',
    zona: '',
  });

  const cargar = async () => {
    const [z, e, p] = await Promise.all([
      api.get('/zonas/'),
      api.get('/edificios/'),
      api.get('/puntos-acceso/'),
    ]);
    setZonas(Array.isArray(z) ? z : []);
    setEdificios(Array.isArray(e) ? e : []);
    setPuntos(Array.isArray(p) ? p : []);
    setZonaForm((prev) => ({ ...prev, edificio: prev.edificio || e[0]?.id || '' }));
    setPuntoForm((prev) => ({ ...prev, zona: prev.zona || z[0]?.id || '' }));
  };

  useEffect(() => {
    cargar().catch((err) => alert(err.message));
  }, []);

  const crearZona = async (e) => {
    e.preventDefault();
    await api.post('/zonas/', {
      nombre_zona: zonaForm.nombre_zona,
      nivel_seguridad: zonaForm.nivel_seguridad,
      zona_padre: zonaForm.zona_padre ? Number(zonaForm.zona_padre) : null,
      edificio: zonaForm.edificio ? Number(zonaForm.edificio) : null,
    });
    setZonaForm((prev) => ({ ...prev, nombre_zona: '' }));
    await cargar();
  };

  const crearPunto = async (e) => {
    e.preventDefault();
    await api.post('/puntos-acceso/', {
      ...puntoForm,
      zona: Number(puntoForm.zona),
    });
    setPuntoForm((prev) => ({ ...prev, descripcion: '', ubicacion_fisica: '' }));
    await cargar();
  };

  const arbol = armarArbolZonas(zonas);

  return (
    <div>
      <h1>Zonas del predio</h1>
      <div className="panel">
        <h2>Árbol Composite</h2>
        <ul className="tree">
          {arbol.map((z) => (
            <Nodo key={z.id} zona={z} />
          ))}
        </ul>
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
          <label>
            Edificio
            <select
              value={zonaForm.edificio}
              onChange={(e) => setZonaForm({ ...zonaForm, edificio: e.target.value })}
            >
              {edificios.map((ed) => (
                <option key={ed.id} value={ed.id}>
                  {ed.nombre}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn-ok" type="submit">
            Crear zona
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Punto de acceso (puerta / molinete)</h2>
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
          <button className="btn btn-primary" type="submit">
            Crear punto
          </button>
        </form>
        <table>
          <thead>
            <tr>
              <th>Punto</th>
              <th>Ubicación</th>
              <th>Zona</th>
            </tr>
          </thead>
          <tbody>
            {puntos.map((p) => (
              <tr key={p.id}>
                <td>{p.descripcion}</td>
                <td>{p.ubicacion_fisica}</td>
                <td>{p.zona_nombre}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
