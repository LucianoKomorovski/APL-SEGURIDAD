export const API = '/api';

let onUnauthorized = () => {};

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

function cookie(nombre) {
  const prefijo = `${nombre}=`;
  const valor = document.cookie.split('; ').find((item) => item.startsWith(prefijo));
  return valor ? decodeURIComponent(valor.slice(prefijo.length)) : '';
}

async function parseJson(res) {
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = body.error || body.detail || body.motivo || JSON.stringify(body);
    const error = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    error.status = res.status;
    if (res.status === 401) onUnauthorized();
    throw error;
  }
  return body;
}

function request(path, method = 'GET', data) {
  const headers = { Accept: 'application/json' };
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers['X-CSRFToken'] = cookie('csrftoken');
  }
  return fetch(`${API}${path}`, {
    method,
    credentials: 'same-origin',
    headers,
    body: data === undefined ? undefined : JSON.stringify(data),
  }).then(parseJson);
}

export const api = {
  get: (path) => request(path),
  post: (path, data) => request(path, 'POST', data),
  patch: (path, data) => request(path, 'PATCH', data),
  del: (path) => request(path, 'DELETE'),
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
