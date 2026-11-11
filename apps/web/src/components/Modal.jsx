import Icon from "./Icon.jsx";
function Modal({ modal, setModal }) {
  return (
    <div className="ov" onClick={(e) => e.target === e.currentTarget && setModal(null)}>
      <div className="dlg" role="dialog" aria-modal="true">
        <div className="dlg-hd">
          <h2>{modal.title}</h2>
          <button className="ic" type="button" aria-label="Close" onClick={() => setModal(null)}><Icon n="x" /></button>
        </div>
        {modal.body}
        <div className={"row" + (modal.center ? " center" : "")}>
          {modal.actions.map((a) => (
            <button
              key={a.label}
              className={"btn" + (a.pri ? " pri" : "")}
              onClick={() => { setModal(null); a.fn && a.fn(); }}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Modal;
