export const API = '/api';

async function parseJson(res) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = body.error || body.detail || body.motivo || JSON.stringify(body);
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return body;
}

export const api = {
  get: (path) => fetch(`${API}${path}`).then(parseJson),
  post: (path, data) =>
    fetch(`${API}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(parseJson),
  patch: (path, data) =>
    fetch(`${API}${path}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(parseJson),
  del: (path) =>
    fetch(`${API}${path}`, { method: 'DELETE' }).then((res) => {
      if (!res.ok && res.status !== 204) {
        throw new Error(`HTTP ${res.status}`);
      }
    }),
};

export function formatFecha(valor) {
  if (!valor) return '—';
  return new Date(valor).toLocaleString('es-AR', {
    dateStyle: 'short',
    timeStyle: 'medium',
  });
}

export function armarArbolZonas(zonas) {
  const byId = Object.fromEntries(zonas.map((z) => [z.id, { ...z, hijos: [] }]));
  const roots = [];
  zonas.forEach((z) => {
    const nodo = byId[z.id];
    if (z.zona_padre && byId[z.zona_padre]) {
      byId[z.zona_padre].hijos.push(nodo);
    } else {
      roots.push(nodo);
    }
  });
  return roots;
}

export const DIAS = [
  { id: '0', label: 'Lun' },
  { id: '1', label: 'Mar' },
  { id: '2', label: 'Mié' },
  { id: '3', label: 'Jue' },
  { id: '4', label: 'Vie' },
  { id: '5', label: 'Sáb' },
  { id: '6', label: 'Dom' },
];
