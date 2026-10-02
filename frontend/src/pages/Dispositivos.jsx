import { useEffect, useState } from 'react';
import { api, formatFecha } from '../api';
import PageHead from '../PageHead';

export default function Dispositivos() {
  const [controladores, setControladores] = useState([]);
  const [puntos, setPuntos] = useState([]);
  const [edificios, setEdificios] = useState([]);
  const [form, setForm] = useState({
    direccion_ip: '',
    numero_serie: '',
    punto_acceso: '',
    edificio: '',
  });

  const cargar = async () => {
    const [c, p, e] = await Promise.all([
      api.get('/controladores/'),
      api.get('/puntos-acceso/'),
      api.get('/edificios/'),
    ]);
    setControladores(Array.isArray(c) ? c : []);
    setPuntos(Array.isArray(p) ? p : []);
    setEdificios(Array.isArray(e) ? e : []);
    setForm((prev) => ({
      ...prev,
      punto_acceso: prev.punto_acceso || p[0]?.id || '',
      edificio: prev.edificio || e[0]?.id || '',
    }));
  };

  useEffect(() => {
    let activo = true;
    const actualizar = () => Promise.all([
      api.get('/controladores/'),
      api.get('/puntos-acceso/'),
      api.get('/edificios/'),
    ]).then(([c, p, e]) => {
      if (!activo) return;
      setControladores(Array.isArray(c) ? c : []);
      setPuntos(Array.isArray(p) ? p : []);
      setEdificios(Array.isArray(e) ? e : []);
      setForm((prev) => ({
        ...prev,
        punto_acceso: prev.punto_acceso || p[0]?.id || '',
        edificio: prev.edificio || e[0]?.id || '',
      }));
    });
    actualizar().catch((err) => alert(err.message));
    const id = setInterval(() => actualizar().catch(() => {}), 5000);
    return () => {
      activo = false;
      clearInterval(id);
    };
  }, []);

  const crear = async (e) => {
    e.preventDefault();
    await api.post('/controladores/', {
      direccion_ip: form.direccion_ip,
      numero_serie: form.numero_serie,
      punto_acceso: Number(form.punto_acceso),
      edificio: form.edificio ? Number(form.edificio) : null,
      estado_conexion: 'Desconectado',
    });
    setForm((prev) => ({ ...prev, direccion_ip: '', numero_serie: '' }));
    await cargar();
  };

  return (
    <div>
      <PageHead
        kicker="Red"
        title="Controladoras"
        lede="Alta de dispositivos y estado de conexión de cada tótem."
      />
      <div className="panel">
        <h2>Alta de dispositivo</h2>
        <form className="form-grid" onSubmit={crear}>
          <label>
            IP
            <input
              className="mono"
              value={form.direccion_ip}
              onChange={(e) => setForm({ ...form, direccion_ip: e.target.value })}
              placeholder="10.0.0.40"
              required
            />
          </label>
          <label>
            N° de serie
            <input
              value={form.numero_serie}
              onChange={(e) => setForm({ ...form, numero_serie: e.target.value })}
              required
            />
          </label>
          <label>
            Punto de acceso
            <select
              value={form.punto_acceso}
              onChange={(e) => setForm({ ...form, punto_acceso: e.target.value })}
            >
              {puntos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.descripcion}
                </option>
              ))}
            </select>
          </label>
          <label>
            Edificio
            <select
              value={form.edificio}
              onChange={(e) => setForm({ ...form, edificio: e.target.value })}
            >
              {edificios.map((ed) => (
                <option key={ed.id} value={ed.id}>
                  {ed.nombre}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn-primary" type="submit">
            Registrar
          </button>
        </form>
      </div>
      <div className="panel">
        <h2>Estado de red</h2>
        <table>
          <thead>
            <tr>
              <th>Serie</th>
              <th>IP</th>
              <th>Zona</th>
              <th>Ping</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {controladores.length === 0 ? (
              <tr>
                <td className="empty" colSpan="5">
                  Sin controladoras.
                </td>
              </tr>
            ) : (
              controladores.map((c) => (
                <tr key={c.id}>
                  <td className="mono">{c.numero_serie}</td>
                  <td className="mono">{c.direccion_ip}</td>
                  <td>{c.zona_nombre}</td>
                  <td>{formatFecha(c.fecha_ultimo_ping)}</td>
                  <td>
                    <span className={c.en_linea ? 'badge badge-ok' : 'badge badge-bad'}>
                      {c.en_linea ? 'En línea' : c.estado_conexion}
                    </span>
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
