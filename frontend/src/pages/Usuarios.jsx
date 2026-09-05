import { useEffect, useState } from 'react';
import { UserPlus } from 'lucide-react';
import { api } from '../api';

const FORM_VACIO = {
  nombre: '',
  apellido: '',
  dni: '',
  email: '',
  codigo_referencia: '',
  edificio: '',
  nivel_acceso: '',
  estado: 'Activo',
  estado_llave: 'Activa',
};

export default function Usuarios() {
  const [sujetos, setSujetos] = useState([]);
  const [edificios, setEdificios] = useState([]);
  const [niveles, setNiveles] = useState([]);
  const [form, setForm] = useState(FORM_VACIO);
  const [editandoId, setEditandoId] = useState(null);

  const cargar = async () => {
    const [s, e, n] = await Promise.all([
      api.get('/sujetos/'),
      api.get('/edificios/'),
      api.get('/niveles/'),
    ]);
    setSujetos(Array.isArray(s) ? s : []);
    setEdificios(Array.isArray(e) ? e : []);
    setNiveles(Array.isArray(n) ? n : []);
  };

  useEffect(() => {
    cargar().catch((err) => alert(err.message));
  }, []);

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
    estado_llave: form.estado_llave,
  });

  const guardar = async (e) => {
    e.preventDefault();
    try {
      if (editandoId) {
        await api.patch(`/sujetos/${editandoId}/`, payload());
      } else {
        await api.post('/sujetos/', payload());
      }
      setForm(FORM_VACIO);
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
      edificio: s.edificio || '',
      nivel_acceso: s.nivel_acceso || '',
      estado: s.estado || 'Activo',
      estado_llave: llave?.estado || 'Activa',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const bloquearLlave = async (s) => {
    const llave = (s.credenciales || [])[0];
    if (!llave) return;
    const nuevo = llave.estado === 'Bloqueada' ? 'Activa' : 'Bloqueada';
    try {
      await api.patch(`/credenciales/${llave.id}/`, { estado: nuevo });
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  const borrarLlave = async (s) => {
    const llave = (s.credenciales || [])[0];
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
        setForm(FORM_VACIO);
      }
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <h1>ABM de clientes y llaves</h1>
      <p style={{ color: '#64748b', marginTop: 0 }}>
        Alta, modificación y baja de personas y de sus llaves magnéticas (código del llavero).
      </p>
      <div className="panel">
        <h2>
          <UserPlus size={18} /> {editandoId ? 'Modificar cliente' : 'Alta de cliente'}
        </h2>
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
            Estado de la llave
            <select value={form.estado_llave} onChange={onChange('estado_llave')}>
              <option>Activa</option>
              <option>Bloqueada</option>
              <option>Vencida</option>
            </select>
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
              <option value="">Ninguno (técnico, todos los sitios)</option>
              {edificios.map((ed) => (
                <option key={ed.id} value={ed.id}>
                  {ed.nombre}
                </option>
              ))}
            </select>
          </label>
          <label>
            Estado del cliente
            <select value={form.estado} onChange={onChange('estado')}>
              <option>Activo</option>
              <option>Inactivo</option>
            </select>
          </label>
          <button className="btn btn-ok" type="submit">
            {editandoId ? 'Guardar cambios' : 'Dar de alta'}
          </button>
          {editandoId && (
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => {
                setEditandoId(null);
                setForm(FORM_VACIO);
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
            {sujetos.map((s) => {
              const llave = (s.credenciales || [])[0];
              return (
                <tr key={s.id}>
                  <td>
                    {s.nombre} {s.apellido}
                  </td>
                  <td>{s.dni}</td>
                  <td>{s.edificio_nombre || 'Todos'}</td>
                  <td>{llave?.codigo_referencia || '—'}</td>
                  <td>
                    <span
                      className={
                        llave?.estado === 'Activa' ? 'badge badge-ok' : 'badge badge-bad'
                      }
                    >
                      {llave?.estado || 'Sin llave'}
                    </span>
                  </td>
                  <td style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <button className="btn btn-primary" type="button" onClick={() => editar(s)}>
                      Editar
                    </button>
                    <button className="btn btn-ghost" type="button" onClick={() => bloquearLlave(s)}>
                      {llave?.estado === 'Bloqueada' ? 'Activar' : 'Bloquear'}
                    </button>
                    <button className="btn btn-ghost" type="button" onClick={() => borrarLlave(s)}>
                      Borrar llave
                    </button>
                    <button className="btn btn-bad" type="button" onClick={() => borrarCliente(s)}>
                      Baja
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
