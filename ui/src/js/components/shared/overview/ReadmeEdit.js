import React from 'react';
import classNames from 'classnames';


const ReadmeEdit = ({
  editingReadme,
  closeReadme,
  saveReadme,
}) => {
  const overviewReadmeEditingCSS = classNames({
    'Overview__readme--editing column-1-span-12': editingReadme,
    hidden: !editingReadme,
  });

  return (
    <div className="grid">
      <div className={overviewReadmeEditingCSS}>

        <textarea
          className="Overview__readme-editor"
          id="markDown"
        />

        <div className="Overview__readme--editing-buttons">
          <button
            type="button"
            className="Overview__readme-cancel Btn--flat"
            onClick={() => { closeReadme(); }}
          >
          Cancel
          </button>

          <button
            type="button"
            className="Overview__readme-save Btn--last"
            disabled={false}
            onClick={() => { saveReadme(); }}
          >
          Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReadmeEdit;
