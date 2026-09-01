import { useState, useEffect } from 'react';
import {
  Shield,
  LayoutDashboard,
  Users,
  Map,
  AlertTriangle,
  CheckCircle,
  UserPlus,
} from 'lucide-react';

function App() {
  // ESTADO DE NAVEGACION (controla en que pantalla estamos):
  const [vistaActiva, setVistaActiva] = useState('dashboard');

  //ESTADO DE DATOS:
  const [alertas, setAlertas] = useState([]);
  const [sujetos, setSujetos] = useState([]);
  const [edificios, setEdificios] = useState([]);

  //ESTADOS DEL FORMULARIO DE USUARIOS:
  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [documento, setDocumento] = useState('');
  const [email, setEmail] = useState('');
  const [codigo_referencia, setCodigoRfid] = useState('');
  const [edificioId, setEdificioId] = useState('');

  //useffect hace que esta peticion se cargue apenas se carga la pantalla
  useEffect(() => {
    const buscarAlertas = async () => {
      try {
        const respuesta = await fetch(`http://127.0.0.1:8000/api/alertas/`, {
          cache: 'no-store',
        });

        if (!respuesta.ok) {
          throw new Error(`HTTP ${respuesta.status}`);
        }

        const datos = await respuesta.json();
        console.log('Datos recibidos del backend: ', datos);
        setAlertas(Array.isArray(datos) ? datos : []);
      } catch (error) {
        console.error('error de conexion con django: ', error);
        setAlertas([]);
      }
    };

    buscarAlertas();

    // POLLING: LE DECIMOS A REACT QUE REPITA ESTO CADA 3 SEGUNDOS (3000 MS):
    const intervalo = setInterval(buscarAlertas, 3000);

    // LIMPIEZA: SI EL USUARIO CIERRA LA PAGINA, APAGAMOS EL RELOJ PARA NO GASTAR MEMORIA
    return () => clearInterval(intervalo);
  }, []);

  //EFECTO PARA BUSCAR USUARIOS SOLO CUANDO ESTAMOS EN ESA PANTALLA:
  useEffect(() => {
    if (vistaActiva !== 'usuarios') {
      return;
    }

    const cargarUsuarios = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/sujetos/');

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const datos = await res.json();
        setSujetos(Array.isArray(datos) ? datos : []);

        // CARGAMOS LOS EDIFICIOS PARA EL <select> DEL FORMULARIO:
        const resEdificios = await fetch(
          'http://127.0.0.1:8000/api/edificios/',
        );

        if (!resEdificios.ok) {
          throw new Error(`HTTP ${resEdificios.status}`);
        }

        const datosEdificios = await resEdificios.json();
        const listaEd = Array.isArray(datosEdificios) ? datosEdificios : [];
        setEdificios(listaEd);
        if (listaEd.length > 0 && !edificioId) {
          setEdificioId(listaEd[0].id);
        }
      } catch (err) {
        console.error('Error cargando datos: ', err);
        setSujetos([]);
        setEdificios([]);
      }
    };

    cargarUsuarios();
  }, [vistaActiva, edificioId]); //SE EJECUTA CADA VEZ QUE SE CAMBIA DE VISTA

  const resolverAlerta = (id) => {
    //1. LE PEDIMOS A DJANGO QUE ACTUALICE LA BASE DE DATOS
    fetch(`http://127.0.0.1:8000/api/alertas/${id}/`, {
      method: 'PATCH', //PATCH significa "modificar"
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        estado_atencion: 'Resuelta', //DATO A ACTUALIZAR
      }),
    })
      .then((respuesta) => {
        if (!respuesta.ok) {
          throw new Error(
            `Django rechazo la peticion con código: ${respuesta.status}`,
          );
        }
        return respuesta.json();
      })
      .then((alertaActualizada) => {
        //2. ACTUALIZAMOS NUESTRA MEMORIA VISUAL EN REACT PARA QUE NO HAGA FALTA RECARGAR LA PAGINA
        setAlertas((alertasPrevias) =>
          alertasPrevias.map((alerta) =>
            alerta.id === id ? alertaActualizada : alerta,
          ),
        );
      })
      .catch((error) => console.error('error al actualizar', error));
  };

  const crearUsuario = (e) => {
    e.preventDefault();

    const datosNuevos = {
      nombre: nombre,
      apellido: apellido,
      dni: Number(documento), // El modelo espera 'dni' (numérico), no 'documento'
      email: email, // El modelo exige email (obligatorio y único)
      codigo_referencia: codigo_referencia,
      edificio: edificioId ? Number(edificioId) : null,
    };

    fetch('http://127.0.0.1:8000/api/sujetos/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datosNuevos),
    })
      // Leemos SIEMPRE el cuerpo: si Django rechazó, ahí viene el motivo real
      .then((res) =>
        res.json().then((body) => {
          if (!res.ok) {
            // body suele ser algo como {"email": ["Este campo es requerido."]}
            throw new Error(JSON.stringify(body));
          }
          return body;
        }),
      )
      .then((sujetoCreado) => {
        // AGREGAMOS EL SUJETO NUEVO A LA LISTA SIN RECARGAR LA PAGINA
        setSujetos([...sujetos, sujetoCreado]);
        // LIMPIAMOS LOS CAMPOS:
        setNombre('');
        setApellido('');
        setDocumento('');
        setEmail('');
        setCodigoRfid('');
        alert('¡Usuario creado con exito!');
      })
      .catch((err) => alert(`Error al crear usuario: ${err.message}`));
  };

  // CONTADORES DE ALERTAS:
  const alertasPendientes = Array.isArray(alertas)
    ? alertas.filter((a) => a.estado_atencion === 'Pendiente').length
    : 0;
  const alertasResueltas = Array.isArray(alertas)
    ? alertas.filter((a) => a.estado_atencion === 'Resuelta').length
    : 0;

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        fontFamily: 'system-ui, sans-serif',
        backgroundColor: '#f4f6f8',
        margin: 0,
      }}
    >
      {/* --- MENÚ LATERAL --- */}
      <div
        style={{
          width: '250px',
          backgroundColor: '#1e293b',
          color: 'white',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            marginBottom: '40px',
            borderBottom: '1px solid #334155',
            paddingBottom: '20px',
          }}
        >
          <Shield size={32} color="#3b82f6" />
          <h2 style={{ margin: 0, fontSize: '1.2rem' }}>SGCA - APL</h2>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <button
            onClick={() => setVistaActiva('dashboard')}
            style={{
              background: 'none',
              border: 'none',
              color: vistaActiva === 'dashboard' ? '#60a5fa' : '#cbd5e1',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontWeight: 'bold',
              cursor: 'pointer',
              padding: 0,
              fontSize: '1rem',
            }}
          >
            <LayoutDashboard size={20} /> Dashboard
          </button>

          <button
            onClick={() => setVistaActiva('usuarios')}
            style={{
              background: 'none',
              border: 'none',
              color: vistaActiva === 'usuarios' ? '#60a5fa' : '#cbd5e1',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontWeight: 'bold',
              cursor: 'pointer',
              padding: 0,
              fontSize: '1rem',
            }}
          >
            <Users size={20} /> Gestión de Usuarios
          </button>

          <button
            style={{
              background: 'none',
              border: 'none',
              color: '#cbd5e1',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontWeight: 'bold',
              cursor: 'not-allowed',
              padding: 0,
              fontSize: '1rem',
              opacity: 0.5,
            }}
          >
            <Map size={20} /> Zonas (Próximamente)
          </button>
        </nav>
      </div>

      {/* --- CONTENIDO PRINCIPAL DINÁMICO --- */}
      <div style={{ flex: 1, padding: '30px', overflowY: 'auto' }}>
        {/* === PANTALLA: DASHBOARD === */}
        {vistaActiva === 'dashboard' && (
          <div>
            <h1 style={{ color: '#0f172a', marginTop: 0 }}>
              Panel de Monitoreo
            </h1>

            <div style={{ display: 'flex', gap: '20px', marginBottom: '30px' }}>
              <div
                style={{
                  backgroundColor: 'white',
                  padding: '20px',
                  borderRadius: '8px',
                  flex: 1,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                  borderLeft: '4px solid #ef4444',
                }}
              >
                <h3
                  style={{
                    margin: 0,
                    color: '#64748b',
                    fontSize: '0.9rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                  }}
                >
                  <AlertTriangle size={16} color="#ef4444" /> Pendientes
                </h3>
                <p
                  style={{
                    margin: '10px 0 0 0',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    color: '#0f172a',
                  }}
                >
                  {alertasPendientes}
                </p>
              </div>
              <div
                style={{
                  backgroundColor: 'white',
                  padding: '20px',
                  borderRadius: '8px',
                  flex: 1,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                  borderLeft: '4px solid #22c55e',
                }}
              >
                <h3
                  style={{
                    margin: 0,
                    color: '#64748b',
                    fontSize: '0.9rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                  }}
                >
                  <CheckCircle size={16} color="#22c55e" /> Resueltas
                </h3>
                <p
                  style={{
                    margin: '10px 0 0 0',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    color: '#0f172a',
                  }}
                >
                  {alertasResueltas}
                </p>
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '8px',
                padding: '20px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              <h2
                style={{
                  marginTop: 0,
                  borderBottom: '1px solid #e2e8f0',
                  paddingBottom: '10px',
                  color: '#1e293b',
                }}
              >
                Alertas de Seguridad
              </h2>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  textAlign: 'left',
                  marginTop: '10px',
                }}
              >
                <thead>
                  <tr
                    style={{
                      backgroundColor: '#f8fafc',
                      color: '#475569',
                      fontSize: '0.9rem',
                    }}
                  >
                    <th
                      style={{
                        padding: '12px',
                        borderBottom: '2px solid #e2e8f0',
                      }}
                    >
                      ID
                    </th>
                    <th
                      style={{
                        padding: '12px',
                        borderBottom: '2px solid #e2e8f0',
                      }}
                    >
                      Tipo
                    </th>
                    <th
                      style={{
                        padding: '12px',
                        borderBottom: '2px solid #e2e8f0',
                      }}
                    >
                      Estado
                    </th>
                    <th
                      style={{
                        padding: '12px',
                        borderBottom: '2px solid #e2e8f0',
                      }}
                    >
                      Acción
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {alertas.length === 0 ? (
                    <tr>
                      <td
                        colSpan="4"
                        style={{ padding: '20px', textAlign: 'center' }}
                      >
                        No hay alertas registradas.
                      </td>
                    </tr>
                  ) : (
                    alertas.map((alerta) => (
                      <tr
                        key={alerta.id}
                        style={{ borderBottom: '1px solid #e2e8f0' }}
                      >
                        <td style={{ padding: '12px', color: '#64748b' }}>
                          #{alerta.id}
                        </td>
                        <td style={{ padding: '12px', fontWeight: '500' }}>
                          {alerta.tipo_alerta}
                        </td>
                        <td style={{ padding: '12px' }}>
                          {alerta.estado_atencion}
                        </td>
                        <td style={{ padding: '12px' }}>
                          {alerta.estado_atencion !== 'Resuelta' ? (
                            <button
                              onClick={() => resolverAlerta(alerta.id)}
                              style={{
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                padding: '6px 12px',
                                borderRadius: '4px',
                                cursor: 'pointer',
                              }}
                            >
                              Resolver
                            </button>
                          ) : (
                            <span
                              style={{
                                color: '#94a3b8',
                                fontSize: '0.85rem',
                                fontWeight: 'bold',
                              }}
                            >
                              ✔️ Cerrada
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* === PANTALLA: USUARIOS === */}
        {vistaActiva === 'usuarios' && (
          <div>
            <h1 style={{ color: '#0f172a', marginTop: 0 }}>
              Gestión de Usuarios
            </h1>

            {/* Formulario de Alta */}
            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '8px',
                padding: '20px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                marginBottom: '30px',
              }}
            >
              <h2
                style={{
                  marginTop: 0,
                  color: '#1e293b',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                }}
              >
                <UserPlus size={20} /> Nuevo Sujeto de Acceso
              </h2>

              <form
                onSubmit={crearUsuario}
                style={{ display: 'flex', gap: '15px', alignItems: 'flex-end' }}
              >
                <div
                  style={{ display: 'flex', flexDirection: 'column', flex: 1 }}
                >
                  <label
                    style={{
                      fontSize: '0.85rem',
                      color: '#64748b',
                      marginBottom: '5px',
                    }}
                  >
                    Nombre
                  </label>
                  <input
                    type="text"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    required
                    style={{
                      padding: '10px',
                      border: '1px solid #cbd5e1',
                      borderRadius: '4px',
                    }}
                  />
                </div>
                <div
                  style={{ display: 'flex', flexDirection: 'column', flex: 1 }}
                >
                  <label
                    style={{
                      fontSize: '0.85rem',
                      color: '#64748b',
                      marginBottom: '5px',
                    }}
                  >
                    Apellido
                  </label>
                  <input
                    type="text"
                    value={apellido}
                    onChange={(e) => setApellido(e.target.value)}
                    required
                    style={{
                      padding: '10px',
                      border: '1px solid #cbd5e1',
                      borderRadius: '4px',
                    }}
                  />
                </div>
                <div
                  style={{ display: 'flex', flexDirection: 'column', flex: 1 }}
                >
                  <label
                    style={{
                      fontSize: '0.85rem',
                      color: '#64748b',
                      marginBottom: '5px',
                    }}
                  >
                    Documento
                  </label>
                  <input
                    type="number"
                    value={documento}
                    onChange={(e) => setDocumento(e.target.value)}
                    required
                    style={{
                      padding: '10px',
                      border: '1px solid #cbd5e1',
                      borderRadius: '4px',
                    }}
                  />
                </div>
                <div
                  style={{ display: 'flex', flexDirection: 'column', flex: 1 }}
                >
                  <label
                    style={{
                      fontSize: '0.85rem',
                      color: '#64748b',
                      marginBottom: '5px',
                    }}
                  >
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    style={{
                      padding: '10px',
                      border: '1px solid #cbd5e1',
                      borderRadius: '4px',
                    }}
                  />
                </div>
                {/* Fila 2: Infraestructura y Hardware (Llavero Azul / Edificio) */}
                <div
                  style={{
                    display: 'flex',
                    gap: '15px',
                    alignItems: 'flex-end',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      flex: 1,
                    }}
                  >
                    <label
                      style={{
                        fontSize: '0.85rem',
                        color: '#475569',
                        fontWeight: 'bold',
                        marginBottom: '5px',
                      }}
                    >
                      🔑 Código de Llavero/Imán RFID
                    </label>
                    <input
                      type="text"
                      placeholder="Ej: A4B7902F"
                      value={codigo_referencia}
                      onChange={(e) => setCodigoRfid(e.target.value)}
                      required
                      style={{
                        padding: '10px',
                        border: '2px solid #3b82f6',
                        borderRadius: '4px',
                        backgroundColor: '#f0f9ff',
                      }}
                    />
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      flex: 1,
                    }}
                  >
                    <label
                      style={{
                        fontSize: '0.85rem',
                        color: '#64748b',
                        marginBottom: '5px',
                      }}
                    >
                      🏢 Asignar a Edificio
                    </label>
                    {/* MENÚ DESPLEGABLE DINÁMICO */}
                    <select
                      value={edificioId}
                      onChange={(e) => setEdificioId(e.target.value)}
                      style={{
                        padding: '10px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '4px',
                        backgroundColor: 'white',
                      }}
                    >
                      {edificios.length === 0 ? (
                        <option value="">Cargando edificios...</option>
                      ) : (
                        edificios.map((edificio) => (
                          <option key={edificio.id} value={edificio.id}>
                            {edificio.nombre}
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                  <button
                    type="submit"
                    style={{
                      backgroundColor: '#22c55e',
                      color: 'white',
                      border: 'none',
                      padding: '11px 20px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                    }}
                  >
                    Guardar
                  </button>
                </div>
              </form>
            </div>

            {/* Tabla de Usuarios Registrados */}
            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '8px',
                padding: '20px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              <h2
                style={{
                  marginTop: 0,
                  borderBottom: '1px solid #e2e8f0',
                  paddingBottom: '10px',
                  color: '#1e293b',
                }}
              >
                Usuarios en el Sistema
              </h2>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  textAlign: 'left',
                  marginTop: '10px',
                }}
              >
                <thead>
                  <tr
                    style={{
                      backgroundColor: '#f8fafc',
                      color: '#475569',
                      fontSize: '0.9rem',
                    }}
                  >
                    <th
                      style={{
                        padding: '12px',
                        borderBottom: '2px solid #e2e8f0',
                      }}
                    >
                      ID
                    </th>
                    <th
                      style={{
                        padding: '12px',
                        borderBottom: '2px solid #e2e8f0',
                      }}
                    >
                      Nombre Completo
                    </th>
                    <th
                      style={{
                        padding: '12px',
                        borderBottom: '2px solid #e2e8f0',
                      }}
                    >
                      Documento
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sujetos.length === 0 ? (
                    <tr>
                      <td
                        colSpan="3"
                        style={{ padding: '20px', textAlign: 'center' }}
                      >
                        No hay usuarios registrados.
                      </td>
                    </tr>
                  ) : (
                    sujetos.map((sujeto) => (
                      <tr
                        key={sujeto.id}
                        style={{ borderBottom: '1px solid #e2e8f0' }}
                      >
                        <td style={{ padding: '12px', color: '#64748b' }}>
                          #{sujeto.id}
                        </td>
                        <td style={{ padding: '12px', fontWeight: '500' }}>
                          {sujeto.nombre} {sujeto.apellido}
                        </td>
                        <td style={{ padding: '12px' }}>{sujeto.dni}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
