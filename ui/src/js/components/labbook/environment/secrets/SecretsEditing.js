// vendor
import React from 'react';
// Assets
import './SecretsEditing.scss';

export default ({
  node,
  addedFiles,
  setFile,
  replaceFile,
  editSecret,
}) => (
  <div className="SecretsEditing flex">
    <label
      htmlFor="update_secret"
      className="SecretsTable__label"
    >
      <div
        className="Btn Btn--allStyling Btn--noMargin Btn--action padding--horizontal"
      >
        Replace File...
      </div>
      <input
        id="update_secret"
        className="hidden"
        type="file"
        onChange={evt => setFile(node.filename, evt.target.files[0])}
      />
    </label>
    <button
      type="button"
      className="Btn Btn--small Btn__check--grey Btn--round"
      disabled={!addedFiles.has(node.filename)}
      onClick={() => replaceFile(node.filename, node.id, node.isPresent)}
    />
    <button
      type="button"
      className="Btn Btn--small Btn__close--grey Btn--round"
      onClick={() => editSecret(node.filename)}
    />
  </div>
);
