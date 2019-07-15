// vendor
import React from 'react';

export default ({
  commitsCSS,
  commitsPending,
  commitsBehind,
  togglePopup,
  commitsPopupCSS,
  modifiyDatasetLink,
  tooltipShown,
  toggleTooltip,
}) => (
  <div className="DatasetsCard__commitsContainer flex justify--left align-items--center">
    <div
      className={commitsCSS}
    >
      {
        !commitsPending
        && <div className="DatasetCard__commits--commits-behind">{commitsBehind}</div>
      }
    </div>
    <div className="relative">
      <button
        className="Btn Btn--flat"
        type="button"
        onClick={(evt) => { togglePopup(evt, true, 'commits'); }}
        disabled={commitsPending}
      >
        Link to Latest Version
      </button>
      <div className={commitsPopupCSS}>
        <div className="Tooltip__pointer" />
        <p className="margin-top--0">Are you sure?</p>
        <div className="flex justify--space-around">
          <button
            className="File__btn--round File__btn--cancel"
            onClick={(evt) => { togglePopup(evt, false, 'commits'); }}
            type="button"
          />
          <button
            className="File__btn--round File__btn--add"
            onClick={evt => modifiyDatasetLink(evt, 'update')}
            type="button"
          />
        </div>
      </div>
    </div>
    <button
      className="DatasetCard__tooltip"
      onClick={() => toggleTooltip()}
      type="button"
    >
      {
        tooltipShown
        && (
        <div className="InfoTooltip">
          {`Dataset link is ${commitsBehind} commits behind. Select "Update Dataset Link" to the latest dataset version. `}
          <a
            target="_blank"
            href="https://docs.gigantum.com/docs/using-datasets-with-projects"
            rel="noopener noreferrer"
          >
            Learn more.
          </a>
        </div>
        )
      }
    </button>
  </div>
);
