// vendor
import React from 'react';

export default ({
  setTooltipVisible,
  node,
  tooltipVisible,
}) => (
  <button
    type="button"
    className="Btn margin-right--grid Btn--small Btn--round Btn__warning relative"
    onClick={() => setTooltipVisible(node.filename)}
  >
    {
    (tooltipVisible === node.filename)
    && (
    <div className="InfoTooltip">
      Secrets file not found. Edit to replace file.
      {' '}
      <a
        target="_blank"
        href="https://docs.gigantum.com/docs/using-cuda-with-nvidia-gpus"
        rel="noopener noreferrer"
      >
        Learn more.
      </a>
    </div>
    )
  }
  </button>
);
