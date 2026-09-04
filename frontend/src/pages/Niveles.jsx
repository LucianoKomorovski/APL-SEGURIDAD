import { useEffect, useState } from 'react';
import { api, DIAS } from '../api';

export default function Niveles() {
  const [niveles, setNiveles] = useState([]);
  const [zonas, setZonas] = useState([]);
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [zonasElegidas, setZonasElegidas] = useState([]);
  const [horario, setHorario] = useState({
    nivel: '',
    hora_inicio: '08:00',
    hora_fin: '18:00',
    dias: ['0', '1', '2', '3', '4'],
  });

  const cargar = async () => {
    const [n, z] = await Promise.all([api.get('/niveles/'), api.get('/zonas/')]);
    setNiveles(Array.isArray(n) ? n : []);
    setZonas(Array.isArray(z) ? z : []);
    setHorario((prev) => ({ ...prev, nivel: prev.nivel || n[0]?.id || '' }));
  };

  useEffect(() => {
    cargar().catch((err) => alert(err.message));
  }, []);

  const toggleZona = (id) => {
    setZonasElegidas((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const crearNivel = async (e) => {
    e.preventDefault();
    await api.post('/niveles/', {
      nombre_nivel: nombre,
      descripcion,
      zonas: zonasElegidas,
    });
    setNombre('');
    setDescripcion('');
    setZonasElegidas([]);
    await cargar();
  };

  const crearHorario = async (e) => {
    e.preventDefault();
    await api.post('/horarios/', {
      nivel_acceso: Number(horario.nivel),
      hora_inicio: horario.hora_inicio,
      hora_fin: horario.hora_fin,
      dias_semana: horario.dias.join(','),
    });
    await cargar();
  };

  return (
    <div>
      <h1>Niveles y horarios</h1>
      <div className="panel">
        <h2>Nuevo nivel</h2>
        <form onSubmit={crearNivel}>
          <div className="form-grid">
            <label>
              Nombre
              <input value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            </label>
            <label>
              Descripción
              <input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
            </label>
          </div>
          <p>Zonas que cubre este nivel (un padre cubre a sus hijos):</p>
          {zonas.map((z) => (
            <label key={z.id} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
              <input
                type="checkbox"
                checked={zonasElegidas.includes(z.id)}
                onChange={() => toggleZona(z.id)}
              />
              {z.nombre_zona}
              {z.zona_padre_nombre ? ` (dentro de ${z.zona_padre_nombre})` : ''}
            </label>
          ))}
          <button className="btn btn-ok" type="submit">
            Crear nivel
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Ventana horaria</h2>
        <form className="form-grid" onSubmit={crearHorario}>
          <label>
            Nivel
            <select
              value={horario.nivel}
              onChange={(e) => setHorario({ ...horario, nivel: e.target.value })}
            >
              {niveles.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.nombre_nivel}
                </option>
              ))}
            </select>
          </label>
          <label>
            Desde
            <input
              type="time"
              value={horario.hora_inicio}
              onChange={(e) => setHorario({ ...horario, hora_inicio: e.target.value })}
            />
          </label>
          <label>
            Hasta
            <input
              type="time"
              value={horario.hora_fin}
              onChange={(e) => setHorario({ ...horario, hora_fin: e.target.value })}
            />
          </label>
          <div>
            {DIAS.map((d) => (
              <label key={d.id} style={{ flexDirection: 'row', display: 'inline-flex', marginRight: 8 }}>
                <input
                  type="checkbox"
                  checked={horario.dias.includes(d.id)}
                  onChange={() =>
                    setHorario((prev) => ({
                      ...prev,
                      dias: prev.dias.includes(d.id)
                        ? prev.dias.filter((x) => x !== d.id)
                        : [...prev.dias, d.id],
                    }))
                  }
                />
                {d.label}
              </label>
            ))}
          </div>
          <button className="btn btn-primary" type="submit">
            Agregar horario
          </button>
        </form>
      </div>

      {niveles.map((n) => (
        <div className="panel" key={n.id}>
          <h2>{n.nombre_nivel}</h2>
          <p>{n.descripcion}</p>
          <p>
            Zonas:{' '}
            {(n.zonas_detalle || []).map((z) => z.nombre_zona).join(', ') || 'ninguna'}
          </p>
          <p>
            Horarios:{' '}
            {(n.horarios || []).length === 0
              ? '24/7'
              : n.horarios
                  .map((h) => `${h.hora_inicio}–${h.hora_fin} (${h.dias_semana})`)
                  .join(' | ')}
          </p>
        </div>
      ))}
    </div>
  );
}
