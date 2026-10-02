import { useEffect, useState } from 'react';
import { api } from '../api';
import EdificioSelect from '../EdificioSelect';
import PageHead from '../PageHead';

const FORM_VACIO = {
  nombre: '',
  apellido: '',
  dni: '',
  email: '',
  codigo_referencia: '',
  edificio: '',
  nivel_acceso: '',
  estado: 'Activo',
};

export default function Usuarios({ edificios, edificioId, onEdificio }) {
  const [sujetos, setSujetos] = useState([]);
  const [niveles, setNiveles] = useState([]);
  const [form, setForm] = useState(FORM_VACIO);
  const [editandoId, setEditandoId] = useState(null);
  const edificioActual = edificios.find((ed) => String(ed.id) === String(edificioId));
  const formLimpio = () => ({ ...FORM_VACIO, edificio: edificioId });

  const cargar = async () => {
    if (!edificioId) return;
    const q = `?edificio=${edificioId}`;
    const [s, n] = await Promise.all([api.get(`/sujetos/${q}`), api.get(`/niveles/${q}`)]);
    setSujetos(Array.isArray(s) ? s : []);
    setNiveles(Array.isArray(n) ? n : []);
  };

  useEffect(() => {
    if (!edificioId) return undefined;
    let activo = true;
    const q = `?edificio=${edificioId}`;
    Promise.all([api.get(`/sujetos/${q}`), api.get(`/niveles/${q}`)]).then(([s, n]) => {
      if (!activo) return;
      setSujetos(Array.isArray(s) ? s : []);
      setNiveles(Array.isArray(n) ? n : []);
    }).catch((err) => alert(err.message));
    return () => {
      activo = false;
    };
  }, [edificioId]);

  const cambiarEdificio = (valor) => {
    if (!editandoId) setForm((prev) => ({ ...prev, edificio: valor }));
    onEdificio(valor);
  };

  const onChange = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  const payload = () => ({
    nombre: form.nombre,
    apellido: form.apellido,
    dni: Number(form.dni),
    email: form.email,
    codigo_referencia: form.codigo_referencia,
    edificio: form.edificio ? Number(form.edificio) : null,
    nivel_acceso: form.nivel_acceso ? Number(form.nivel_acceso) : null,
    estado: form.estado,
  });

  const guardar = async (e) => {
    e.preventDefault();
    try {
      if (editandoId) {
        await api.patch(`/sujetos/${editandoId}/`, payload());
      } else {
        await api.post('/sujetos/', payload());
      }
      setForm(formLimpio());
      setEditandoId(null);
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  const editar = (s) => {
    const llave = (s.credenciales || [])[0];
    setEditandoId(s.id);
    setForm({
      nombre: s.nombre,
      apellido: s.apellido,
      dni: String(s.dni),
      email: s.email,
      codigo_referencia: llave?.codigo_referencia || '',
      edificio: s.edificio ? String(s.edificio) : '',
      nivel_acceso: s.nivel_acceso || '',
      estado: s.estado || 'Activo',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const cambiarEstadoLlave = async (llave, estado) => {
    try {
      await api.patch(`/credenciales/${llave.id}/`, { estado });
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  const borrarLlave = async (llave) => {
    if (!llave) return;
    if (!confirm(`¿Borrar la llave ${llave.codigo_referencia}?`)) return;
    try {
      await api.del(`/credenciales/${llave.id}/`);
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  const borrarCliente = async (s) => {
    if (!confirm(`¿Dar de baja a ${s.nombre} ${s.apellido} y sus llaves?`)) return;
    try {
      await api.del(`/sujetos/${s.id}/`);
      if (editandoId === s.id) {
        setEditandoId(null);
        setForm(formLimpio());
      }
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <PageHead
        kicker="Padrón"
        title="ABM de clientes y llaves"
        lede="Alta de clientes y llaves, bloqueo y actualización de sus datos."
      />
      <EdificioSelect edificios={edificios} edificioId={edificioId} onChange={cambiarEdificio} />
      <div className="panel">
        <h2>{editandoId ? 'Modificar cliente' : 'Alta de cliente'}</h2>
        <form className="form-grid" onSubmit={guardar}>
          <label>
            Nombre
            <input value={form.nombre} onChange={onChange('nombre')} required />
          </label>
          <label>
            Apellido
            <input value={form.apellido} onChange={onChange('apellido')} required />
          </label>
          <label>
            DNI
            <input type="number" value={form.dni} onChange={onChange('dni')} required />
          </label>
          <label>
            Email
            <input type="email" value={form.email} onChange={onChange('email')} required />
          </label>
          <label>
            Código de llave
            <input
              value={form.codigo_referencia}
              onChange={onChange('codigo_referencia')}
              placeholder="Ej: A4B7902F"
              required={!editandoId}
            />
          </label>
          <label>
            Nivel
            <select value={form.nivel_acceso} onChange={onChange('nivel_acceso')}>
              <option value="">Sin nivel</option>
              {niveles.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.nombre_nivel}
                </option>
              ))}
            </select>
          </label>
          <label>
            Edificio
            <select value={form.edificio} onChange={onChange('edificio')}>
              <option value={edificioId}>{edificioActual?.nombre || 'Este edificio'}</option>
              <option value="">Ninguno (técnico, todos los sitios)</option>
            </select>
          </label>
          <label>
            Estado del cliente
            <select value={form.estado} onChange={onChange('estado')}>
              <option>Activo</option>
              <option>Inactivo</option>
            </select>
          </label>
          <button className="btn btn-primary" type="submit">
            {editandoId ? 'Guardar cambios' : 'Dar de alta'}
          </button>
          {editandoId && (
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => {
                setEditandoId(null);
                setForm(formLimpio());
              }}
            >
              Cancelar
            </button>
          )}
        </form>
      </div>

      <div className="panel">
        <h2>Padrón</h2>
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>DNI</th>
              <th>Edificio</th>
              <th>Llave</th>
              <th>Estado llave</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sujetos.length === 0 ? (
              <tr>
                <td className="empty" colSpan="6">
                  Todavía no hay clientes.
                </td>
              </tr>
            ) : null}
            {sujetos.flatMap((s) => {
              const llaves = s.credenciales?.length ? s.credenciales : [null];
              return llaves.map((llave) => (
                <tr key={`${s.id}-${llave?.id || 'sin'}`}>
                  <td>
                    {s.nombre} {s.apellido}
                  </td>
                  <td>{s.dni}</td>
                  <td>{s.edificio_nombre || 'Todos los sitios'}</td>
                  <td className="mono">{llave?.codigo_referencia || '—'}</td>
                  <td>
                    <span className={llave?.estado === 'Activa' ? 'badge badge-ok' : 'badge badge-bad'}>
                      {llave?.estado || 'Sin llave'}
                    </span>
                  </td>
                  <td>
                    <div className="actions">
                      <button className="btn-text" type="button" onClick={() => editar(s)}>
                        Editar
                      </button>
                      {llave && ['Activa', 'Bloqueada', 'Vencida'].includes(llave.estado) && (
                        <>
                          <button className="btn-text" type="button" onClick={() => cambiarEstadoLlave(llave, llave.estado === 'Activa' ? 'Bloqueada' : 'Activa')}>
                            {llave.estado === 'Activa' ? 'Bloquear' : 'Activar'}
                          </button>
                          {llave.estado !== 'Vencida' && (
                            <button className="btn-text" type="button" onClick={() => cambiarEstadoLlave(llave, 'Vencida')}>
                              Marcar vencida
                            </button>
                          )}
                        </>
                      )}
                      {llave && ['Emitida', 'Repuesta'].includes(llave.estado) && (
                        <span className="muted">Histórica · sin habilitación</span>
                      )}
                      {llave && (
                        <button className="btn-text" type="button" onClick={() => borrarLlave(llave)}>
                          Borrar llave
                        </button>
                      )}
                      <button className="btn-text danger" type="button" onClick={() => borrarCliente(s)}>
                        Baja
                      </button>
                    </div>
                  </td>
                </tr>
              ));
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
