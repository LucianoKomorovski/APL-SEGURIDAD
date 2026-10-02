import { useEffect, useState } from 'react';
import { api, DIAS } from '../api';
import EdificioSelect from '../EdificioSelect';
import PageHead from '../PageHead';

export default function Niveles({ edificios, edificioId, onEdificio }) {
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
    if (!edificioId) return;
    const q = `?edificio=${edificioId}`;
    const [n, z] = await Promise.all([api.get(`/niveles/${q}`), api.get(`/zonas/${q}`)]);
    const listaNiveles = Array.isArray(n) ? n : [];
    setNiveles(listaNiveles);
    setZonas(Array.isArray(z) ? z : []);
    setHorario((prev) => ({
      ...prev,
      nivel: listaNiveles.some((nivel) => String(nivel.id) === String(prev.nivel))
        ? prev.nivel
        : listaNiveles[0]?.id || '',
    }));
  };

  useEffect(() => {
    if (!edificioId) return undefined;
    let activo = true;
    const q = `?edificio=${edificioId}`;
    Promise.all([api.get(`/niveles/${q}`), api.get(`/zonas/${q}`)]).then(([n, z]) => {
      if (!activo) return;
      const listaNiveles = Array.isArray(n) ? n : [];
      setNiveles(listaNiveles);
      setZonas(Array.isArray(z) ? z : []);
      setHorario((prev) => ({
        ...prev,
        nivel: listaNiveles.some((nivel) => String(nivel.id) === String(prev.nivel))
          ? prev.nivel
          : listaNiveles[0]?.id || '',
      }));
    }).catch((err) => alert(err.message));
    return () => {
      activo = false;
    };
  }, [edificioId]);

  const cambiarEdificio = (valor) => {
    setZonasElegidas([]);
    onEdificio(valor);
  };

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
      <PageHead
        kicker="Permisos"
        title="Niveles y horarios"
        lede="Qué zonas de este edificio cubre cada nivel y en qué ventana horaria se puede pasar."
      />
      <EdificioSelect edificios={edificios} edificioId={edificioId} onChange={cambiarEdificio} />
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
          <p className="field-note">Zonas que cubre este nivel (un padre cubre a sus hijos)</p>
          <div className="choice-grid">
            {zonas.map((z) => (
              <label key={z.id} className="choice">
                <input
                  type="checkbox"
                  checked={zonasElegidas.includes(z.id)}
                  onChange={() => toggleZona(z.id)}
                />
                <span>
                  {z.nombre_zona}
                  {z.zona_padre_nombre ? ` · ${z.zona_padre_nombre}` : ''}
                </span>
              </label>
            ))}
          </div>
          <button className="btn btn-primary" type="submit">
            Crear nivel
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Ventana horaria</h2>
        <form onSubmit={crearHorario}>
          <div className="form-grid">
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
          </div>
          <div className="choice-row">
            {DIAS.map((d) => (
              <label key={d.id} className="choice">
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

      <div className="panel">
        <h2>Niveles definidos</h2>
        {niveles.length === 0 ? (
          <p className="empty">Todavía no hay niveles.</p>
        ) : (
          niveles.map((n) => (
            <article className="nivel" key={n.id}>
              <h3>{n.nombre_nivel}</h3>
              {n.descripcion ? <p>{n.descripcion}</p> : null}
              <p>
                <span className="nivel-k">Zonas</span>
                {(n.zonas_detalle || []).map((z) => z.nombre_zona).join(', ') || 'ninguna'}
              </p>
              <p>
                <span className="nivel-k">Horario</span>
                {(n.horarios || []).length === 0
                  ? '24/7'
                  : n.horarios
                      .map((h) => `${h.hora_inicio}–${h.hora_fin} (${h.dias_semana})`)
                      .join(' · ')}
              </p>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
