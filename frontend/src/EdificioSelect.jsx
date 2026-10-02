export default function EdificioSelect({ edificios, edificioId, onChange }) {
  return (
    <label className="edificio-elegir">
      Edificio
      <select value={edificioId} onChange={(e) => onChange(e.target.value)}>
        {edificios.length === 0 ? <option value="">Sin edificios</option> : null}
        {edificios.map((ed) => (
          <option key={ed.id} value={ed.id}>
            {ed.nombre}
          </option>
        ))}
      </select>
    </label>
  );
}
