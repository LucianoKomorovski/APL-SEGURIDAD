import { useEffect, useState } from 'react';
import { UserPlus } from 'lucide-react';
import { api } from '../api';

export default function Usuarios() {
  const [sujetos, setSujetos] = useState([]);
  const [edificios, setEdificios] = useState([]);
  const [niveles, setNiveles] = useState([]);
  const [form, setForm] = useState({
    nombre: '',
    apellido: '',
    dni: '',
    email: '',
    codigo_referencia: '',
    edificio: '',
    nivel_acceso: '',
  });

  const cargar = async () => {
    const [s, e, n] = await Promise.all([
      api.get('/sujetos/'),
      api.get('/edificios/'),
      api.get('/niveles/'),
    ]);
    setSujetos(Array.isArray(s) ? s : []);
    setEdificios(Array.isArray(e) ? e : []);
    setNiveles(Array.isArray(n) ? n : []);
    setForm((prev) => ({
      ...prev,
      edificio: prev.edificio || e[0]?.id || '',
      nivel_acceso: prev.nivel_acceso || n[0]?.id || '',
    }));
  };

  useEffect(() => {
    cargar().catch((err) => alert(err.message));
  }, []);

  const onChange = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  const crear = async (e) => {
    e.preventDefault();
    try {
      await api.post('/sujetos/', {
        ...form,
        dni: Number(form.dni),
        edificio: form.edificio ? Number(form.edificio) : null,
        nivel_acceso: form.nivel_acceso ? Number(form.nivel_acceso) : null,
      });
      setForm((prev) => ({
        ...prev,
        nombre: '',
        apellido: '',
        dni: '',
        email: '',
        codigo_referencia: '',
      }));
      await cargar();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <h1>Clientes y llaveros</h1>
      <div className="panel">
        <h2>
          <UserPlus size={18} /> Alta con credencial
        </h2>
        <form className="form-grid" onSubmit={crear}>
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
            Código RFID / QR
            <input
              value={form.codigo_referencia}
              onChange={onChange('codigo_referencia')}
              placeholder="TAG-XXXX"
              required
            />
          </label>
          <label>
            Nivel
            <select value={form.nivel_acceso} onChange={onChange('nivel_acceso')}>
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
          <button className="btn btn-ok" type="submit">
            Guardar
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Padrón de clientes</h2>
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>DNI</th>
              <th>Edificio</th>
              <th>Nivel</th>
              <th>Llaveros</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {sujetos.map((s) => (
              <tr key={s.id}>
                <td>
                  {s.nombre} {s.apellido}
                </td>
                <td>{s.dni}</td>
                <td>{s.edificio_nombre || 'Todos'}</td>
                <td>{s.nivel_nombre || '—'}</td>
                <td>
                  {(s.credenciales || []).map((c) => c.codigo_referencia).join(', ') || '—'}
                </td>
                <td>{s.estado}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
