export default function PageHead({ kicker, title, lede }) {
  return (
    <header className="page-head">
      <p className="kicker">{kicker}</p>
      <h1>{title}</h1>
      {lede ? <p className="lede">{lede}</p> : null}
    </header>
  );
}
