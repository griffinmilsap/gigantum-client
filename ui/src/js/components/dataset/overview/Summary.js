// vendor
import React, { PureComponent } from 'react';
// assets
import './Summary.scss';
// config
import config from 'JS/config';

export default class Summary extends PureComponent {

  render() {
    const { props } = this;
    const onDiskBytes = props.localBytes;
    const onDiskFormatted = config.humanFileSize(onDiskBytes);
    const toDownloadBytes = props.totalBytes - props.localBytes;
    const toDownloadFormatted = config.humanFileSize(toDownloadBytes);

    return (
      <div className="Summary">
        <div className="Overview__container">
          <h2> Summary </h2>
        </div>
        <div className="grid">
          <div className="Summary__card Card column-1-span-12">
            <div className="Summary__file-count">
              <div className="Summary__subheader">Number of Files</div>
              <div className="Summary__content">{props.numFiles}</div>
            </div>
            <div className="Summary__size flex-1">
              <div className="Summary__total-size flex-1">
                <div className="Summary__subheader">Total Size</div>
                <div className="Summary__content">{config.humanFileSize(props.totalBytes)}</div>
              </div>
              <div className="Summary__disk-size flex-1 flex flex--column">
                <progress
                  value={onDiskBytes}
                  max={props.totalBytes}
                />
                <div className="flex justify--space-between">
                  <div className="Summary__onDisk flex flex--column">
                    <div className="Summary__onDisk--primary">{onDiskFormatted}</div>
                    <div className="Summary__onDisk--secondary">on disk</div>
                  </div>
                  <div className="Summary__toDownload flex flex--column">
                    <div className="Summary__toDownload--primary">{toDownloadFormatted}</div>
                    <div className="Summary__toDownload--secondary">to download</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="Summary__file-type">
              <div className="Summary__subheader">Common File Types</div>
              <ul className="Summary__list">
                {
                  props.fileTypeDistribution.length
                    ? props.fileTypeDistribution.slice(0, 6).map((type, index) => {
                      const splitType = type.split('|');
                      const adjustedType = splitType[1].length > 10 ? `${splitType[1].slice(0, 7)}...` : splitType[1];
                      const percentage = Math.round(Number(splitType[0]) * 100);
                      if ((index === 5) && (props.fileTypeDistribution.length !== 6)) {
                        return <li key={type}>{`+ ${props.fileTypeDistribution.length - 6} other types`}</li>;
                      }
                      return (
                        <li key={type}>{`${adjustedType} (${percentage}%)`}</li>
                      );
                    })
                    : <li> No files found.</li>
                }
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
