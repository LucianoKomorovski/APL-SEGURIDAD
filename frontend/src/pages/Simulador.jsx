import { useEffect, useState } from 'react';
import { api, formatFecha } from '../api';

const TAGS = [
  ['TAG-OP-01', 'Operador'],
  ['TAG-TEC-01', 'Técnico'],
  ['TAG-VIS-01', 'Visitante'],
  ['TAG-ADM-01', 'Admin (Composite)'],
  ['TAG-BLOQ-01', 'Bloqueada'],
  ['TAG-VENC-01', 'Vencida'],
];

export default function Simulador() {
  const [controladores, setControladores] = useState([]);
  const [ip, setIp] = useState('199.1.1.0');
  const [codigo, setCodigo] = useState('TAG-ADM-01');
  const [log, setLog] = useState(
    'Listo. Este tótem habla el mismo contrato HTTP que un ESP32 o una controladora real.\n',
  );

  useEffect(() => {
    api.get('/controladores/').then((data) => {
      const lista = Array.isArray(data) ? data : [];
      setControladores(lista);
      if (lista[0]) setIp(lista[0].direccion_ip);
    });
  }, []);

  const append = (linea) => {
    setLog((prev) => `${formatFecha(new Date().toISOString())}  ${linea}\n${prev}`);
  };

  const leer = async (tag = codigo) => {
    try {
      const data = await api.post('/totem/lectura/', { codigo_rfid: tag, ip_totem: ip });
      append(`VERDE ${tag} @ ${ip} → ${data.accion}`);
    } catch (err) {
      append(`ROJO  ${tag} @ ${ip} → ${err.message}`);
    }
  };

  const evento = async (tipo) => {
    try {
      const data = await api.post('/totem/evento/', { tipo, ip_totem: ip });
      append(`EVENTO ${tipo} → alerta ${data.alerta_id || 'n/a'} (${data.estado_conexion})`);
    } catch (err) {
      append(`ERROR evento: ${err.message}`);
    }
  };

  return (
    <div>
      <h1>Tótem virtual</h1>
      <p>
        Para la defensa no hace falta hardware industrial: el simulador usa el mismo endpoint que
        usaría un lector RFID en el predio.
      </p>
      <div className="totem">
        <div className="panel">
          <h2>Lector</h2>
          <label>
            Controlador
            <select value={ip} onChange={(e) => setIp(e.target.value)}>
              {controladores.map((c) => (
                <option key={c.id} value={c.direccion_ip}>
                  {c.numero_serie} — {c.zona_nombre} ({c.direccion_ip})
                </option>
              ))}
            </select>
          </label>
          <label>
            Código
            <input value={codigo} onChange={(e) => setCodigo(e.target.value)} />
          </label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '12px 0' }}>
            {TAGS.map(([tag, label]) => (
              <button
                key={tag}
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  setCodigo(tag);
                  leer(tag);
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <button className="btn btn-ok" type="button" onClick={() => leer()}>
            Pasar tarjeta
          </button>
          <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
            <button className="btn btn-bad" type="button" onClick={() => evento('PUERTA_FORZADA')}>
              Puerta forzada
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => evento('DESCONEXION')}>
              Desconectar
            </button>
            <button className="btn btn-primary" type="button" onClick={() => evento('RECONEXION')}>
              Reconectar
            </button>
          </div>
        </div>
        <pre className="totem-log">{log}</pre>
      </div>
    </div>
  );
}
